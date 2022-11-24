from requests import utils as rutils
from subprocess import run as srun
from random import choice
from pathlib import PurePath
from telegram.ext import CommandHandler
from re import match as re_match, search as re_search, split as re_split
from time import sleep, time
from base64 import b64encode
from shutil import rmtree
from os import path as ospath, remove as osremove, listdir, walk
from subprocess import Popen
from html import escape
from threading import Thread
from telegram import ParseMode, InlineKeyboardButton

from bot import NAME_FONT, bot, Interval, INDEX_URL, BUTTON_FOUR_NAME, BUTTON_FOUR_URL, BUTTON_FIVE_NAME, BUTTON_FIVE_URL, \
                BUTTON_SIX_NAME, BUTTON_SIX_URL, VIEW_LINK, aria2, dispatcher, DOWNLOAD_DIR, \
                download_dict, download_dict_lock, TG_SPLIT_SIZE, LOGGER, MEGA_KEY, DB_URI, INCOMPLETE_TASK_NOTIFIER, \
                LEECH_LOG, BOT_PM, MIRROR_LOGS, SOURCE_LINK, AUTO_DELETE_UPLOAD_MESSAGE_DURATION, \
                MIRROR_ENABLED, LEECH_ENABLED, WATCH_ENABLED, CLONE_ENABLED, LINK_LOGS, EMOJI_THEME, \
                MIRROR_LOG_URL, LEECH_LOG_URL, TITLE_NAME, LEECH_LOG_INDEXING, PICS, NAME_FONT, FORCE_BOT_PM, DISABLE_DRIVE_LINK, \
                PRE_DICT, REM_DICT, SUF_DICT
from bot.helper.ext_utils.bot_utils import is_url, is_magnet, is_gdtot_link, is_mega_link, is_gdrive_link, get_content_type, get_readable_time
from bot.helper.ext_utils.fs_utils import get_base_name, get_path_size, split_file, clean_download, clean_target
from bot.helper.ext_utils.exceptions import DirectDownloadLinkException, NotSupportedExtractionArchive
from bot.helper.mirror_utils.status_utils.extract_status import ExtractStatus
from bot.helper.mirror_utils.status_utils.zip_status import ZipStatus
from bot.helper.mirror_utils.status_utils.split_status import SplitStatus
from bot.helper.mirror_utils.status_utils.upload_status import UploadStatus
from bot.helper.ext_utils.shortenurl import short_url
from bot.helper.mirror_utils.status_utils.tg_upload_status import TgUploadStatus
from bot.helper.mirror_utils.upload_utils.gdriveTools import GoogleDriveHelper
from bot.helper.mirror_utils.upload_utils.pyrogramEngine import TgUploader
from bot.helper.telegram_helper.message_utils import sendMessage, sendMarkup, delete_all_messages, update_all_messages, auto_delete_upload_message, sendPhoto
from bot.helper.telegram_helper.button_build import ButtonMaker
from bot.helper.ext_utils.db_handler import DbManger
from bot.helper.ext_utils.telegraph_helper import telegraph


class MirrorLeechListener:
    def __init__(self, bot, message, isZip=False, extract=False, isQbit=False, isLeech=False, pswd=None, tag=None, select=False, seed=False):
        self.bot = bot
        self.message = message
        self.uid = message.message_id
        self.extract = extract
        self.isZip = isZip
        self.isQbit = isQbit
        self.isLeech = isLeech
        self.pswd = pswd
        self.tag = tag
        self.seed = seed
        self.newDir = ""
        self.dir = f"{DOWNLOAD_DIR}{self.uid}"
        self.select = select
        self.isPrivate = message.chat.type in ['private', 'group']
        self.suproc = None
        self.user_id = self.message.from_user.id	
        reply_to = self.message.reply_to_message

    def clean(self):
        try:
            Interval[0].cancel()
            Interval.clear()
            aria2.purge()
            delete_all_messages()
        except:
            pass

    def onDownloadStart(self):
        if not self.isPrivate and INCOMPLETE_TASK_NOTIFIER and DB_URI is not None:
            DbManger().add_incomplete_task(self.message.chat.id, self.message.link, self.tag)

    def onDownloadComplete(self):
        with download_dict_lock:
            download = download_dict[self.uid]
            name = str(download.name()).replace('/', '')
            gid = download.gid()
        LOGGER.info(f"Download completed: {name}")
        if name == "None" or self.isQbit or not ospath.exists(f"{self.dir}/{name}"):
            name = listdir(f"{self.dir}")[-1]
        m_path = f'{self.dir}/{name}'
        size = get_path_size(m_path)
        if self.isZip:
            if self.seed and self.isLeech:
                self.newDir = f"{self.dir}10000"
                path = f"{self.newDir}/{name}.zip"
            else:
                path = f"{m_path}.zip"
            with download_dict_lock:
                download_dict[self.uid] = ZipStatus(name, size, gid, self)
            if self.pswd is not None:
                if self.isLeech and int(size) > TG_SPLIT_SIZE:
                    LOGGER.info(f'Zip: orig_path: {m_path}, zip_path: {path}.0*')
                    self.suproc = Popen(["7z", f"-v{TG_SPLIT_SIZE}b", "a", "-mx=0", f"-p{self.pswd}", path, m_path])
                else:
                    LOGGER.info(f'Zip: orig_path: {m_path}, zip_path: {path}')
                    self.suproc = Popen(["7z", "a", "-mx=0", f"-p{self.pswd}", path, m_path])
            elif self.isLeech and int(size) > TG_SPLIT_SIZE:
                LOGGER.info(f'Zip: orig_path: {m_path}, zip_path: {path}.0*')
                self.suproc = Popen(["7z", f"-v{TG_SPLIT_SIZE}b", "a", "-mx=0", path, m_path])
            else:
                LOGGER.info(f'Zip: orig_path: {m_path}, zip_path: {path}')
                self.suproc = Popen(["7z", "a", "-mx=0", path, m_path])
            self.suproc.wait()
            if self.suproc.returncode == -9:
                return
            elif not self.seed:
                clean_target(m_path)
        elif self.extract:
            try:
                if ospath.isfile(m_path):
                    path = get_base_name(m_path)
                LOGGER.info(f"Extracting: {name}")
                with download_dict_lock:
                    download_dict[self.uid] = ExtractStatus(name, size, gid, self)
                if ospath.isdir(m_path):
                    if self.seed:
                        self.newDir = f"{self.dir}10000"
                        path = f"{self.newDir}/{name}"
                    else:
                        path = m_path
                    for dirpath, subdir, files in walk(m_path, topdown=False):
                        for file_ in files:
                            if re_search(r'\.part0*1\.rar$|\.7z\.0*1$|\.zip\.0*1$|\.zip$|\.7z$|^.(?!.*\.part\d+\.rar)(?=.*\.rar$)', file_):
                                f_path = ospath.join(dirpath, file_)
                                if self.seed:
                                    t_path = dirpath.replace(self.dir, self.newDir)
                                else:
                                    t_path = dirpath
                                if self.pswd is not None:
                                    self.suproc = Popen(["7z", "x", f"-p{self.pswd}", f_path, f"-o{t_path}", "-aot"])
                                else:
                                    self.suproc = Popen(["7z", "x", f_path, f"-o{t_path}", "-aot"])
                                self.suproc.wait()
                                if self.suproc.returncode == -9:
                                    return
                                elif self.suproc.returncode != 0:
                                    LOGGER.error('Unable to extract archive splits!')
                        if not self.seed and self.suproc is not None and self.suproc.returncode == 0:
                            for file_ in files:
                                if re_search(r'\.r\d+$|\.7z\.\d+$|\.z\d+$|\.zip\.\d+$|\.zip$|\.rar$|\.7z$', file_):
                                    del_path = ospath.join(dirpath, file_)
                                    try:
                                        osremove(del_path)
                                    except:
                                        return
                else:
                    if self.seed and self.isLeech:
                        self.newDir = f"{self.dir}10000"
                        path = path.replace(self.dir, self.newDir)
                    if self.pswd is not None:
                        self.suproc = Popen(["7z", "x", f"-p{self.pswd}", m_path, f"-o{path}", "-aot"])
                    else:
                        self.suproc = Popen(["7z", "x", m_path, f"-o{path}", "-aot"])
                    self.suproc.wait()
                    if self.suproc.returncode == -9:
                        return
                    elif self.suproc.returncode == 0:
                        LOGGER.info(f"Extracted Path: {path}")
                        if not self.seed:
                            try:
                                osremove(m_path)
                            except:
                                return
                    else:
                        LOGGER.error('Unable to extract archive! Uploading anyway')
                        self.newDir = ""
                        path = m_path
            except NotSupportedExtractionArchive:
                LOGGER.info("Not any valid archive, uploading file as it is.")
                self.newDir = ""
                path = m_path
        else:
            path = m_path
        up_dir, up_name = path.rsplit('/', 1)
        size = get_path_size(up_dir)
        if self.isLeech:
            m_size = []
            o_files = []
            if not self.isZip:
                checked = False
                for dirpath, subdir, files in walk(up_dir, topdown=False):
                    for file_ in files:
                        f_path = ospath.join(dirpath, file_)
                        f_size = ospath.getsize(f_path)
                        if f_size > TG_SPLIT_SIZE:
                            if not checked:
                                checked = True
                                with download_dict_lock:
                                    download_dict[self.uid] = SplitStatus(up_name, size, gid, self)
                                LOGGER.info(f"Splitting: {up_name}")
                            res = split_file(f_path, f_size, file_, dirpath, TG_SPLIT_SIZE, self)
                            if not res:
                                return
                            if res == "errored":
                                if f_size <= TG_SPLIT_SIZE:
                                    continue
                                else:
                                    try:
                                        osremove(f_path)
                                    except:
                                        return
                            elif not self.seed or self.newDir:
                                try:
                                    osremove(f_path)
                                except:
                                    return
                            elif self.seed and res != "errored":
                                m_size.append(f_size)
                                o_files.append(file_)

            size = get_path_size(up_dir)
            for s in m_size:
                size = size - s
            LOGGER.info(f"Leech Name: {up_name}")
            tg = TgUploader(up_name, up_dir, size, self)
            tg_upload_status = TgUploadStatus(tg, size, gid, self)
            with download_dict_lock:
                download_dict[self.uid] = tg_upload_status
            update_all_messages()
            tg.upload(o_files)
        else:
            up_path = f'{up_dir}/{up_name}'
            size = get_path_size(up_path)
            LOGGER.info(f"Upload Name: {up_name}")
            drive = GoogleDriveHelper(up_name, up_dir, size, self)
            upload_status = UploadStatus(drive, size, gid, self)
            with download_dict_lock:
                download_dict[self.uid] = upload_status
            update_all_messages()
            drive.upload(up_name)

    def onUploadComplete(self, link: str, size, files, folders, typ, name):
        buttons = ButtonMaker()
        mesg = self.message.text.split('\n')
        message_args = mesg[0].split(' ', maxsplit=1)
        reply_to = self.message.reply_to_message
        PREFIX = PRE_DICT.get(self.message.from_user.id, "")
        REMNAME = REM_DICT.get(self.message.from_user.id, "")
        SUFFIX = SUF_DICT.get(self.message.from_user.id, "")
        file_ = escape(name)

        #MysteryStyle ~ Tele-LeechX
        if file_.startswith('www'):
            file_ = ' '.join(file_.split()[1:])
        if REMNAME:
            if not REMNAME.startswith('|'):
                REMNAME = f"|{REMNAME}"
            slit = REMNAME.split("|")
            __newFileName = file_
            for rep in range(1, len(slit)):
                args = slit[rep].split(":")
                if len(args) == 3:
                    __newFileName = __newFileName.replace(args[0], args[1], int(args[2]))
                elif len(args) == 2:
                    __newFileName = __newFileName.replace(args[0], args[1])
                elif len(args) == 1:
                    __newFileName = __newFileName.replace(args[0], '')
            file_ = __newFileName
            LOGGER.info("Remname : "+file_)
        if PREFIX:
            if not file_.startswith(PREFIX):
                file_ = f"{PREFIX}{file_}"
        if SUFFIX:
            sufLen = len(SUFFIX)
            fileDict = file_.split('.')
            _extIn = 1 + len(fileDict[-1])
            _extOutName = '.'.join(fileDict[:-1]).replace('.', ' ').replace('-', ' ')
            _newExtFileName = f"{_extOutName}{SUFFIX}.{fileDict[-1]}"
            if len(_extOutName) > (64 - (sufLen + _extIn)):
                _newExtFileName = (
                    _extOutName[: 64 - (sufLen + _extIn)]
                    + f"{SUFFIX}.{fileDict[-1]}"
                            )
            file_ = _newExtFileName

        if EMOJI_THEME is True:
            slmsg = f"🗂️ Name: <{NAME_FONT}>{file_}</{NAME_FONT}>\n\n"
            slmsg += f"📐 Size: {size}\n"
            slmsg += f"👥 Added by: {self.tag} | <code>{self.user_id}</code>\n\n"
        else:
            slmsg = f"Name: <{NAME_FONT}>{file_}</{NAME_FONT}>\n\n"
            slmsg += f"Size: {size}\n"
            slmsg += f"Added by: {self.tag} | <code>{self.user_id}</code>\n\n"
        if LINK_LOGS:
            try:
                upper = f"‒‒‒‒‒‒‒‒‒‒‒‒‒‒‒‒‒‒‒‒‒‒‒‒‒‒‒‒‒‒‒‒\n"
                source_link = f"<code>{message_args[1]}</code>\n"
                lower = f"‒‒‒‒‒‒‒‒‒‒‒‒‒‒‒‒‒‒‒‒‒‒‒‒‒‒‒‒‒‒‒‒\n"
                for link_log in LINK_LOGS:
                    bot.sendMessage(link_log, text=slmsg + upper + source_link + lower, parse_mode=ParseMode.HTML )
            except IndexError:
                pass
            if reply_to is not None:
                try:
                    reply_text = reply_to.text
                    if is_url(reply_text):
                        upper = f"‒‒‒‒‒‒‒‒‒‒‒‒‒‒‒‒‒‒‒‒‒‒‒‒‒‒‒‒‒‒‒‒\n"
                        source_link = f"<code>{reply_text.strip()}</code>\n"
                        lower = f"‒‒‒‒‒‒‒‒‒‒‒‒‒‒‒‒‒‒‒‒‒‒‒‒‒‒‒‒‒‒‒‒\n"
                        for link_log in LINK_LOGS:
                            bot.sendMessage(chat_id=link_log, text=slmsg + upper + source_link + lower, parse_mode=ParseMode.HTML )
                except TypeError:
                    pass
        if AUTO_DELETE_UPLOAD_MESSAGE_DURATION != -1:
            reply_to = self.message.reply_to_message
            if reply_to is not None:
                reply_to.delete()
            auto_delete_message = int(AUTO_DELETE_UPLOAD_MESSAGE_DURATION / 60)
            if self.message.chat.type == 'private':
                warnmsg = ''
            else:
                if EMOJI_THEME is True:
                    warnmsg = f'<b>❗ This message will be deleted in <i>{auto_delete_message} minutes</i> from this group.</b>\n'
                else:
                    warnmsg = f'<b>This message will be deleted in <i>{auto_delete_message} minutes</i> from this group.</b>\n'
        else:
            warnmsg = ''
        if BOT_PM and self.message.chat.type != 'private':
            if EMOJI_THEME is True:
                pmwarn = f"<b>😉 I have sent files in PM.</b>\n"
            else:
                pmwarn = f"<b>I have sent files in PM.</b>\n"
        elif self.message.chat.type == 'private':
            pmwarn = ''
        else:
            pmwarn = ''
        if MIRROR_LOGS and self.message.chat.type != 'private':
            if EMOJI_THEME is True:
                logwarn = f"<b>⚠️ I have sent files in Mirror Log Channel. Join <a href=\"{MIRROR_LOG_URL}\">Mirror Log channel</a> </b>\n"
            else:
                logwarn = f"<b>I have sent files in Mirror Log Channel. Join <a href=\"{MIRROR_LOG_URL}\">Mirror Log channel</a> </b>\n"
        elif self.message.chat.type == 'private':
            logwarn = ''
        else:
            logwarn = ''
        if LEECH_LOG and self.message.chat.type != 'private':
            if EMOJI_THEME is True:
                logleechwarn = f"<b>⚠️ I have sent files in Leech Log Channel. Join <a href=\"{LEECH_LOG_URL}\">Leech Log channel</a> </b>\n"
            else:
                logleechwarn = f"<b>I have sent files in Leech Log Channel. Join <a href=\"{LEECH_LOG_URL}\">Leech Log channel</a> </b>\n"
        elif self.message.chat.type == 'private':
            logleechwarn = ''
        else:
            logleechwarn = ''
        if not self.isPrivate and INCOMPLETE_TASK_NOTIFIER and DB_URI is not None:
            DbManger().rm_complete_task(self.message.link)


        if BOT_PM and FORCE_BOT_PM and not self.isPrivate:
            if EMOJI_THEME is True:
                msg = f"<b>🗂️ Name: </b><{NAME_FONT}>{file_}</{NAME_FONT}>\n"
            else:
                msg = f"<b>Name: </b><{NAME_FONT}>{file_}</{NAME_FONT}>\n"
            botpm = f"<b>\nHey {self.tag}!, I have sent your stuff in PM.</b>\n"
            buttons = ButtonMaker()
            b_uname = bot.get_me().username
            botstart = f"http://t.me/{b_uname}"
            buttons.buildbutton("View links in PM", f"{botstart}")

            if PICS:
                sendPhoto(msg + botpm, self.bot, self.message, choice(PICS), buttons.build_menu(2))
            else:
                sendMarkup(msg + botpm, self.bot, self.message, buttons.build_menu(2))
            try:
                self.message.delete()
            except Exception as e:
                    LOGGER.warning(e)
            pass
            reply_to = self.message.reply_to_message
            if reply_to is not None and AUTO_DELETE_UPLOAD_MESSAGE_DURATION == -1:
                reply_to.delete()

        if EMOJI_THEME is True:
            msg = f"<b>╭🗂️ Name: </b><{NAME_FONT}>{file_}</{NAME_FONT}>\n<b>├📐 Size: </b>{size}"
        else:
            msg = f"<b>╭ Name: </b><{NAME_FONT}>{file_}</{NAME_FONT}>\n<b>├ Size: </b>{size}"


        if self.isLeech:
            if SOURCE_LINK is True:
                try:
                    mesg = message_args[1]
                    if is_magnet(mesg):
                        link = telegraph.create_page(
                            title=f"{TITLE_NAME} Source Link",
                            content=mesg,
                        )["path"]
                        buttons.buildbutton(f"🔗 Source Link", f"https://graph.org/{link}")
                    elif is_url(mesg):
                        source_link = mesg
                        if source_link.startswith(("|", "pswd: ")):
                            pass
                        else:
                            buttons.buildbutton(f"🔗 Source Link", source_link)
                    else:
                        pass
                except Exception:
                    pass
                if reply_to is not None:
                    try:
                        reply_text = reply_to.text
                        if is_url(reply_text):
                            source_link = reply_text.strip()
                            if is_magnet(source_link):
                                link = telegraph.create_page(
                                    title=f"{TITLE_NAME} Source Link",
                                    content=source_link,
                                )["path"]
                                buttons.buildbutton(f"🔗 Source Link", f"https://graph.org/{link}")
                            else:
                                buttons.buildbutton(f"🔗 Source Link", source_link)
                    except Exception:
                        pass
            else:
                pass
            if BOT_PM is True and FORCE_BOT_PM is False and self.message.chat.type != 'private':	
                bot_d = bot.get_me()	
                b_uname = bot_d.username	
                botstart = f"http://t.me/{b_uname}"	
                buttons.buildbutton("View file in PM", f"{botstart}")
            elif self.message.chat.type == 'private':
                botstart = ''
            else:
                botstart = ''

            if EMOJI_THEME is True:
                msg += f'\n<b>├📚 Total Files: </b>{folders}'
            else:
                msg += f'\n<b>├ Total Files: </b>{folders}'
            if typ != 0:
                if EMOJI_THEME is True:
                    msg += f'\n<b>├💀 Corrupted Files: </b>{typ}'
                else:
                    msg += f'\n<b>├ Corrupted Files: </b>{typ}'
            if EMOJI_THEME is True:
                msg += f'\n<b>├⌛ It Tooks:</b> {get_readable_time(time() - self.message.date.timestamp())}'
                msg += f'\n<b>╰👤 #Leech_by: </b>{self.tag}\n\n'
            else: 
                msg += f'\n<b>├ It Tooks:</b> {get_readable_time(time() - self.message.date.timestamp())}'
                msg += f'\n<b>╰ #Leech_by: </b>{self.tag}\n\n'



            if not files:
                if PICS:
                    uploadmsg = sendPhoto(msg, self.bot, self.message, choice(PICS), buttons.build_menu(2))
                else:
                    uploadmsg = sendMarkup(msg, self.bot, self.message, buttons.build_menu(2))
            else:
                fmsg = ''
                for index, (link, name) in enumerate(files.items(), start=1):
                    fmsg += f"{index}. <a href='{link}'>{name}</a>\n"
                    if len(fmsg.encode() + msg.encode()) > 2000:
                        sleep(1.5)
                        if FORCE_BOT_PM is False:
                            if PICS:
                                uploadmsg = sendPhoto(msg + fmsg + pmwarn + logleechwarn + warnmsg, self.bot, self.message, choice(PICS), buttons.build_menu(2))
                            else:
                                uploadmsg = sendMarkup(msg + fmsg + pmwarn + logleechwarn + warnmsg, self.bot, self.message, buttons.build_menu(2))
                            Thread(target=auto_delete_upload_message, args=(bot, self.message, uploadmsg)).start()
                        fmsg = ''
                if fmsg != '':
                    sleep(1.5)
                    if FORCE_BOT_PM is False:
                        if PICS:
                            uploadmsg = sendPhoto(msg + fmsg + pmwarn + logleechwarn + warnmsg, self.bot, self.message, choice(PICS), buttons.build_menu(2))
                        else:
                            uploadmsg = sendMarkup(msg + fmsg + pmwarn + logleechwarn + warnmsg, self.bot, self.message, buttons.build_menu(2))
                        Thread(target=auto_delete_upload_message, args=(bot, self.message, uploadmsg)).start()
                if LEECH_LOG_INDEXING is True:
                    for i in LEECH_LOG:
                        indexmsg = ''
                        for index, (link, name) in enumerate(files.items(), start=1):
                            indexmsg += f"{index}. <a href='{link}'>{name}</a>\n"
                            if len(indexmsg.encode() + msg.encode()) > 4000:
                                bot.sendMessage(chat_id=i, text=msg + indexmsg,
                                                reply_markup=buttons.build_menu(2),
                                                parse_mode=ParseMode.HTML)
                                indexmsg = ''
                        if indexmsg != '':
                                bot.sendMessage(chat_id=i, text=msg + indexmsg,
                                                reply_markup=buttons.build_menu(2),
                                                parse_mode=ParseMode.HTML)
                else:
                    pass
            if self.seed:
                if self.newDir:
                    clean_target(self.newDir)
                return			   			  
        else:
            if EMOJI_THEME is True:
                msg += f'\n<b>├📦 Type: </b>{typ}'
            else:
                msg += f'\n<b>├ Type: </b>{typ}'
            if typ == "Folder":
                if EMOJI_THEME is True:
                    msg += f'\n<b>├🗃️ SubFolders: </b>{folders}'
                    msg += f'\n<b>├🗂️ Files: </b>{files}'
                else:
                    msg += f'\n<b>├ SubFolders: </b>{folders}'
                    msg += f'\n<b>├ Files: </b>{files}'
            if EMOJI_THEME is True:
                msg += f'\n<b>├⌛ It Tooks:</b> {get_readable_time(time() - self.message.date.timestamp())}'
                msg += f'\n<b>╰👤 #Mirror_By: </b>{self.tag}\n\n'
            else:
                msg += f'\n<b>├ It Tooks:</b> {get_readable_time(time() - self.message.date.timestamp())}'
                msg += f'\n<b>╰ #Mirror_By: </b>{self.tag}\n\n' 
            buttons = ButtonMaker()
            link = short_url(link)
            if DISABLE_DRIVE_LINK is True and self.message.chat.type != 'private':
                pass
            else:
                buttons.buildbutton("☁️ Drive Link", link)
            LOGGER.info(f'Done Uploading {name}')
            if INDEX_URL is not None:
                url_path = rutils.quote(f'{name}')
                share_url = f'{INDEX_URL}/{url_path}'
                if typ == "Folder":
                    share_url += '/'
                    share_url = short_url(share_url)
                    buttons.buildbutton("⚡ Index Link", share_url)
                else:
                    share_url = short_url(share_url)
                    buttons.buildbutton("⚡ Index Link", share_url)
                    if VIEW_LINK:
                        share_urls = f'{INDEX_URL}/{url_path}?a=view'
                        share_urls = short_url(share_urls)
                        buttons.buildbutton("🌐 View Link", share_urls)
                    if SOURCE_LINK is True:
                        try:
                            mesg = message_args[1]
                            if is_magnet(mesg):
                                link = telegraph.create_page(
                                    title=f"{TITLE_NAME} Source Link",
                                    content=mesg,
                                )["path"]
                                buttons.buildbutton(f"🔗 Source Link", f"https://graph.org/{link}")
                            elif is_url(mesg):
                                source_link = mesg
                                if source_link.startswith(("|", "pswd: ")):
                                    pass
                                else:
                                    buttons.buildbutton(f"🔗 Source Link", source_link)
                            else:
                                pass
                        except Exception:
                            pass
                        if reply_to is not None:
                            try:
                                reply_text = reply_to.text
                                if is_url(reply_text):
                                    source_link = reply_text.strip()
                                    if is_magnet(source_link):
                                        link = telegraph.create_page(
                                            title=f"{TITLE_NAME} Source Link",
                                            content=source_link,
                                        )["path"]
                                        buttons.buildbutton(f"🔗 Source Link", f"https://graph.org/{link}")
                                    else:
                                        buttons.buildbutton(f"🔗 Source Link", source_link)
                            except Exception:
                                pass
                    else:
                        pass
                    

                    if BOT_PM is True and FORCE_BOT_PM is False and self.message.chat.type != 'private':	
                        bot_d = bot.get_me()	
                        b_uname = bot_d.username	
                        botstart = f"http://t.me/{b_uname}"	
                        buttons.buildbutton("View file in PM", f"{botstart}")
                    elif self.message.chat.type == 'private':
                        botstart = ''
                    else:
                        botstart = ''

            if BUTTON_FOUR_NAME is not None and BUTTON_FOUR_URL is not None:
                buttons.buildbutton(f"{BUTTON_FOUR_NAME}", f"{BUTTON_FOUR_URL}")
            if BUTTON_FIVE_NAME is not None and BUTTON_FIVE_URL is not None:
                buttons.buildbutton(f"{BUTTON_FIVE_NAME}", f"{BUTTON_FIVE_URL}")
            if BUTTON_SIX_NAME is not None and BUTTON_SIX_URL is not None:
                buttons.buildbutton(f"{BUTTON_SIX_NAME}", f"{BUTTON_SIX_URL}")

            if FORCE_BOT_PM is False or self.message.chat.type == 'private':
                if PICS:
                    uploadmsg = sendPhoto(msg + pmwarn + logwarn + warnmsg, self.bot, self.message, choice(PICS), buttons.build_menu(2))
                else:
                    uploadmsg = sendMarkup(msg + pmwarn + logwarn + warnmsg, self.bot, self.message, buttons.build_menu(2))
                Thread(target=auto_delete_upload_message, args=(bot, self.message, uploadmsg)).start()
            
            if MIRROR_LOGS:	
                try:	
                    for chatid in MIRROR_LOGS:	
                        bot.sendMessage(chat_id=chatid, text=msg,	
                                        reply_markup=buttons.build_menu(2),	
                                        parse_mode=ParseMode.HTML)	
                except Exception as e:	
                    LOGGER.warning(e)	
            if BOT_PM and self.message.chat.type != 'private':	
                try:	
                    bot.sendMessage(chat_id=self.user_id, text=msg,	
                                    reply_markup=buttons.build_menu(2),	
                                    parse_mode=ParseMode.HTML)	
                except Exception as e:	
                    LOGGER.warning(e)	
                    return
            if self.seed:
                if self.isZip:
                    clean_target(f"{self.dir}/{name}")
                elif self.newDir:
                    clean_target(self.newDir)
                return
        clean_download(self.dir)
        with download_dict_lock:
            try:
                del download_dict[self.uid]
            except Exception as e:
                LOGGER.error(str(e))
            count = len(download_dict)
        if count == 0:
            self.clean()
        else:
            update_all_messages()

    def onDownloadError(self, error):
        error = error.replace('<', ' ').replace('>', ' ')
        try:
            if AUTO_DELETE_UPLOAD_MESSAGE_DURATION != -1 and reply_to is not None:
                reply_to.delete()
            else:
                pass
        except Exception as e:
            LOGGER.warning(e)
            pass
        clean_download(self.dir)
        if self.newDir:
            clean_download(self.newDir)
        with download_dict_lock:
            try:
                del download_dict[self.uid]
            except Exception as e:
                LOGGER.error(str(e))
            count = len(download_dict)
        msg = f"{self.tag} your download has been stopped due to: {error}"
        sendMessage(msg, self.bot, self.message)
        if count == 0:
            self.clean()
        else:
            update_all_messages()

        if not self.isPrivate and INCOMPLETE_TASK_NOTIFIER and DB_URI is not None:
            DbManger().rm_complete_task(self.message.link)

    def onUploadError(self, error):
        e_str = error.replace('<', '').replace('>', '')
        clean_download(self.dir)
        if self.newDir:
            clean_download(self.newDir)
        with download_dict_lock:
            try:
                del download_dict[self.uid]
            except Exception as e:
                LOGGER.error(str(e))
            count = len(download_dict)
        sendMessage(f"{self.tag} {e_str}", self.bot, self.message)
        if count == 0:
            self.clean()
        else:
            update_all_messages()

        if not self.isPrivate and INCOMPLETE_TASK_NOTIFIER and DB_URI is not None:
            DbManger().rm_complete_task(self.message.link)
