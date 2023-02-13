from re import search as re_search
from time import time
from asyncio import sleep as asleep
from os import path as ospath, remove as osremove, listdir, walk
from html import escape
from requests.utils import quote as rquote
from pyrogram import Client
from pyrogram.types import Message
from pyrogram.enums import ChatType
from bot.helper.themes import BotTheme
from bot.helper.ext_utils.bot_utils import change_filename, get_bot_pm, is_url, is_magnet, get_readable_time, getGDriveUploadUtils
from bot.helper.ext_utils.db_handler import DbManger
from bot.helper.ext_utils.exceptions import NotSupportedExtractionArchive
from bot.helper.ext_utils.fs_utils import get_base_name, get_path_size, split_file, clean_download, clean_target, runShell
from bot.helper.ext_utils.queued_starter import start_from_queued
from bot.helper.ext_utils.shortenurl import short_url
from bot.helper.ext_utils.telegraph_helper import telegraph
from bot.helper.mirror_utils.status_utils.extract_status import ExtractStatus
from bot.helper.mirror_utils.status_utils.zip_status import ZipStatus
from bot.helper.mirror_utils.status_utils.split_status import SplitStatus
from bot.helper.mirror_utils.status_utils.upload_status import UploadStatus
from bot.helper.mirror_utils.status_utils.tg_upload_status import TgUploadStatus
from bot.helper.mirror_utils.status_utils.queue_status import QueueStatus
from bot.helper.mirror_utils.upload_utils.gdriveTools import GoogleDriveHelper
from bot.helper.mirror_utils.upload_utils.pyrogramEngine import TgUploader
from bot.helper.telegram_helper.button_build import ButtonMaker
from bot.helper.telegram_helper.message_utils import sendMessage, delete_all_messages, update_all_messages, auto_delete_upload_message, sendPhoto, sendLinkLogMessage, sendMirrorLogMessage, sendLeechLogIndexMsg
from bot import aria2, DOWNLOAD_DIR, LOGGER, Interval, config_dict, user_data, DATABASE_URL, download_dict_lock, download_dict, \
    queue_dict_lock, non_queued_dl, non_queued_up, queued_up, queued_dl, tgBotMaxFileSize, status_reply_dict_lock, main_loop


class MirrorLeechListener:
    def __init__(self, bot: Client, message: Message, isZip=False, extract=False, isQbit=False, isLeech=False, pswd=None, tag=None, select=False, seed=False, c_index=0, u_index=None):
        self.bot = bot
        self.message = message
        self.uid = message.id
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
        self.isPrivate = message.chat.type in [
            ChatType.PRIVATE, ChatType.GROUP]
        self.__user_settings()
        self.suproc = None
        self.user_id = self.message.from_user.id
        self.reply_to = self.message.reply_to_message
        self.c_index = c_index
        self.u_index = u_index
        self.queuedUp = False

    async def clean(self):
        try:
            async with status_reply_dict_lock:
                Interval[0].cancel()
                Interval.clear()
            aria2.purge()
            await delete_all_messages()
        except:
            pass

    async def onDownloadStart(self):
        if not self.isPrivate and config_dict['INCOMPLETE_TASK_NOTIFIER'] and DATABASE_URL:
            DbManger().add_incomplete_task(self.message.chat.id, self.message.link, self.tag)

    async def onDownloadComplete(self):
        user_dict = user_data.get(self.message.from_user.id, False)
        async with download_dict_lock:
            download = download_dict[self.uid]
            name = str(download.name()).replace('/', '')
            gid = download.gid()
        LOGGER.info(f"Download completed: {name}")
        if name == "None" or self.isQbit or not ospath.exists(f"{self.dir}/{name}"):
            name = listdir(self.dir)[-1]
        m_path = f'{self.dir}/{name}'
        size = get_path_size(m_path)
        async with queue_dict_lock:
            if self.uid in non_queued_dl:
                non_queued_dl.remove(self.uid)
        await start_from_queued()
        user_dict = user_data.get(self.message.from_user.id, False)
        if self.isZip:
            if self.seed and self.isLeech:
                self.newDir = f"{self.dir}10000"
                path = f"{self.newDir}/{name}.zip"
            else:
                path = f"{m_path}.zip"
            async with download_dict_lock:
                download_dict[self.uid] = ZipStatus(name, size, gid, self)
            TG_SPLIT_SIZE = int((user_dict and user_dict.get(
                'split_size')) or config_dict['TG_SPLIT_SIZE'])
            if self.pswd is not None:
                if self.isLeech and int(size) > TG_SPLIT_SIZE:
                    LOGGER.info(
                        f'Zip: orig_path: {m_path}, zip_path: {path}.0*')
                    self.suproc = await runShell(f'7z -v{TG_SPLIT_SIZE}b a -mx=0 -p"{self.pswd}" "{path}" "{m_path}"')
                else:
                    LOGGER.info(f'Zip: orig_path: {m_path}, zip_path: {path}')
                    self.suproc = await runShell(f'7z a -mx=0 -p"{self.pswd}" "{path}" "{m_path}"')
            elif self.isLeech and int(size) > TG_SPLIT_SIZE:
                LOGGER.info(f'Zip: orig_path: {m_path}, zip_path: {path}.0*')
                self.suproc = await runShell(f'7z -v{TG_SPLIT_SIZE}b a -mx=0 "{path}" "{m_path}"')
            else:
                LOGGER.info(f'Zip: orig_path: {m_path}, zip_path: {path}')
                self.suproc = await runShell(f'7z a -mx=0 "{path}" "{m_path}"')
            if self.suproc.returncode == -9:
                return
            elif not self.seed:
                clean_target(m_path)
        elif self.extract:
            try:
                if ospath.isfile(m_path):
                    path = get_base_name(m_path)
                LOGGER.info(f"Extracting: {name}")
                async with download_dict_lock:
                    download_dict[self.uid] = ExtractStatus(
                        name, size, gid, self)
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
                                t_path = dirpath.replace(
                                    self.dir, self.newDir) if self.seed else dirpath
                                if self.pswd is not None:
                                    self.suproc = await runShell(f'7z x -p"{self.pswd}" "{f_path}" -o"{t_path}" -aot')
                                else:
                                    self.suproc = await runShell(f'7z x "{f_path}" -o"{t_path}" -aot')
                                if self.suproc.returncode == -9:
                                    return
                                elif self.suproc.returncode != 0:
                                    LOGGER.error(
                                        'Unable to extract archive splits!')
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
                        self.suproc = await runShell(f'7z x -p{self.pswd} "{m_path}" -o"{path}" -aot')
                    else:
                        self.suproc = await runShell(f'7z x "{m_path}" -o"{path}" -aot')
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
                        LOGGER.error(
                            'Unable to extract archive! Uploading anyway')
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
                TG_SPLIT_SIZE = int((user_dict and user_dict.get(
                    'split_size')) or config_dict['TG_SPLIT_SIZE'])
                for dirpath, subdir, files in walk(up_dir, topdown=False):
                    for file_ in files:
                        f_path = ospath.join(dirpath, file_)
                        f_size = ospath.getsize(f_path)
                        if f_size > TG_SPLIT_SIZE:
                            if not checked:
                                checked = True
                                async with download_dict_lock:
                                    download_dict[self.uid] = SplitStatus(
                                        up_name, size, gid, self)
                                LOGGER.info(f"Splitting: {up_name}")
                            res = await split_file(
                                f_path, f_size, file_, dirpath, TG_SPLIT_SIZE, self)
                            if not res:
                                return
                            if res == "errored":
                                if f_size <= tgBotMaxFileSize:
                                    continue
                                try:
                                    osremove(f_path)
                                except:
                                    return
                            elif not self.seed or self.newDir:
                                try:
                                    osremove(f_path)
                                except:
                                    return
                            else:
                                m_size.append(f_size)
                                o_files.append(file_)
        up_limit = config_dict['QUEUE_UPLOAD']
        all_limit = config_dict['QUEUE_ALL']
        added_to_queue = False
        async with queue_dict_lock:
            dl = len(non_queued_dl)
            up = len(non_queued_up)
            if (all_limit and dl + up >= all_limit and (not up_limit or up >= up_limit)) or (up_limit and up >= up_limit):
                added_to_queue = True
                LOGGER.info(f"Added to Queue/Upload: {name}")
                queued_up[self.uid] = [self]
        if added_to_queue:
            async with download_dict_lock:
                download_dict[self.uid] = QueueStatus(
                    name, size, gid, self, 'Up')
                self.queuedUp = True
            while self.queuedUp:
                await asleep(1)
                continue
            async with download_dict_lock:
                if self.uid not in download_dict.keys():
                    return
            LOGGER.info(f'Start from Queued/Upload: {name}')
        async with queue_dict_lock:
            non_queued_up.add(self.uid)

        if self.isLeech:
            size = get_path_size(up_dir)
            for s in m_size:
                size = size - s
            LOGGER.info(f"Leech Name: {up_name}")
            tg = TgUploader(up_name, up_dir, size, self)
            tg_upload_status = TgUploadStatus(tg, size, gid, self)
            async with download_dict_lock:
                download_dict[self.uid] = tg_upload_status
            await update_all_messages()
            await tg.upload(o_files)
        else:
            up_path = f'{up_dir}/{up_name}'
            size = get_path_size(up_path)
            LOGGER.info(f"Upload Name: {up_name}")
            drive = GoogleDriveHelper(
                up_name, up_dir, size, self, self.user_id)
            upload_status = UploadStatus(drive, size, gid, self)
            async with download_dict_lock:
                download_dict[self.uid] = upload_status
            await update_all_messages()
            await main_loop.create_task(drive.upload(up_name, self.u_index, self.c_index))

    async def onUploadComplete(self, link: str, size, files, folders, typ, name):
        buttons = ButtonMaker()
        mesg = self.message.text.split('\n')
        message_args = mesg[0].split(maxsplit=1)
        reply_to = self.message.reply_to_message
        user_id_ = self.message.from_user.id
        up_path, name, _ = change_filename(
            name, user_id_, all_edit=False, mirror_type=(False if self.isLeech else True))
        # b_uname = self.message.from_user.username
        bot_d = await self.bot.get_me()
        b_uname = bot_d.username
        botstart = f"http://t.me/{b_uname}"
        BOT_PM_X = get_bot_pm(user_id_)
        if BOT_PM_X and self.message.chat.type == self.message.chat.type.SUPERGROUP:
            PM = await sendMessage("Added your Requested link to Download\n", self.bot, self.message, chat_id=user_id_)
            if PM:
                await PM.delete()
                PM = True
            else:
                return
        else:
            PM = None
# --------------------------------------------------LINK LOG CODE---------------------------------------------------------------
        await sendLinkLogMessage(self.bot, message_args, name, size, self.tag, user_id_, reply_to)
# -------------------------------------------------------------------------------------------------------------------------------------

# ---------------------------------------------------------Warn Messages-----------------------------------------------------------------
        if config_dict["AUTO_DELETE_UPLOAD_MESSAGE_DURATION"] != -1 and self.message.chat.type != ChatType.PRIVATE:
            auto_delete_message = int(
                config_dict["AUTO_DELETE_UPLOAD_MESSAGE_DURATION"] / 60)
            warnmsg = f'\n<b>❗ This message will be deleted in <i>{auto_delete_message} minutes</i> from this group.</b>\n'
        else:
            warnmsg = ''
        if BOT_PM_X and self.message.chat.type != ChatType.PRIVATE:
            pmwarn = f"\n\n<b>😉Hey {self.tag}!, I have sent your Links/Files in PM.</b>\n"
        else:
            pmwarn = ''
        if 'mirror_logs' in user_data and self.message.chat.type != ChatType.PRIVATE:
            logwarn = f"\n<b>⚠️ I have sent Links in Mirror Log Channel. Join <a href=\"{config_dict['MIRROR_LOG_URL']}\">Mirror Log channel</a> </b>\n"
        else:
            logwarn = ''
        if 'is_leech_log' in user_data and self.message.chat.type != ChatType.PRIVATE:
            logleechwarn = f"\n<b>⚠️ I have sent files in Leech Log Channel. Join <a href=\"{config_dict['LEECH_LOG_URL']}\">Leech Log channel</a> </b>\n"
        else:
            logleechwarn = ''

# ---------------------------------------------------------------------------------------------------------------------------------------
        if not self.isPrivate and config_dict['INCOMPLETE_TASK_NOTIFIER'] and DATABASE_URL is not None:
            DbManger().rm_complete_task(self.message.link)

# --------------------------------------------------Leeching Msg Code---------------------------------------------------------------
        if self.isLeech:
            if config_dict['SOURCE_LINK']:
                try:
                    mesg = message_args[1]
                    if is_magnet(mesg):
                        link = telegraph.create_page(
                            title=f"{config_dict['TITLE_NAME']} Source Link",
                            content=mesg,
                        )["path"]
                        buttons.buildbutton(
                            f"🔗 Source Link", f"https://te.legra.ph/{link}")
                    elif is_url(mesg):
                        source_link = mesg
                        if source_link.startswith(("|", "pswd: ", "c:")):
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
                                    title=f"{config_dict['TITLE_NAME']} Source Link",
                                    content=source_link,
                                )["path"]
                                buttons.buildbutton(
                                    f"🔗 Source Link", f"https://te.legra.ph/{link}")
                            else:
                                buttons.buildbutton(
                                    f"🔗 Source Link", source_link)
                    except Exception:
                        pass
            else:
                pass

            if not self.isPrivate and config_dict['SAVE_MSG']:
                buttons.sbutton('Save This Message', 'save', 'footer')
            msg = BotTheme(self.message.from_user.id).LISTENER_MSG1.format(lm1=config_dict['NAME_FONT'], lm2=escape(
                name), lm3=size, lm4=folders, lm5=get_readable_time(time() - self.message.date.timestamp()), lm6=self.tag)
            if typ != 0:
                msg += BotTheme(self.message.from_user.id).LISTENER_MSG2.format(lm7=typ)
            hide = BotTheme(self.message.from_user.id).LISTENER_HIDE_MSG1.format(
                lhm1=config_dict['NAME_FONT'], lhm2=escape(name))
            # if config_dict['EMOJI_THEME']:
            #     msg = f"<b>╭🗂️ Name: </b><{config_dict['NAME_FONT']}>{escape(name)}</{config_dict['NAME_FONT']}>\n<b>├📐 Size: </b>{size}"
            #     msg += f'\n<b>├📚 Total Files: </b>{folders}'
            #     if typ != 0:
            #         msg += f'\n<b>├💀 Corrupted Files: </b>{typ}'
            #     msg += f'\n<b>├⌛ It Tooks:</b> {get_readable_time(time() - self.message.date.timestamp())}'
            #     msg += f'\n<b>╰👤 #Leech_by: </b>{self.tag}\n\n'
            #     hide = f"<b>🗂️ Name: </b><{config_dict['NAME_FONT']}>{escape(name)}</{config_dict['NAME_FONT']}>\n"
            #     hide += f"\n<b>Hey {self.tag}!, I have sent your Leech Files in PM.</b>\n"
            # else:
            #     msg = f"<b>╭ Name: </b><{config_dict['NAME_FONT']}>{escape(name)}</{config_dict['NAME_FONT']}>\n<b>├ Size: </b>{size}"
            #     msg += f'\n<b>├ Total Files: </b>{folders}'
            #     if typ != 0:
            #         msg += f'\n<b>├ Corrupted Files: </b>{typ}'
            #     msg += f'\n<b>├ It Tooks:</b> {get_readable_time(time() - self.message.date.timestamp())}'
            #     msg += f'\n<b>╰ #Leech_by: </b>{self.tag}\n\n'
            #     hide = f"<b>Name: </b><{config_dict['NAME_FONT']}>{escape(name)}</{config_dict['NAME_FONT']}>\n"
            #     hide += f"\n<b>Hey {self.tag}!, I have sent your Leech Files in PM.</b>\n"

            fmsg = ''
            button = ButtonMaker()
            button.buildbutton("View File in PM", f"{botstart}")
            if not files:
                uploadmsg = await sendPhoto(msg, self.bot, self.message, reply_markup=buttons.build_menu(2))
            else:
                if PM:
                    uploadmsg = await sendPhoto(hide + warnmsg + pmwarn + logleechwarn, self.bot, self.message, reply_markup=button.build_menu(1))
# --------------------------------------------------Leech Index Msg Code---------------------------------------------------------------
                for index, (link, name) in enumerate(files.items(), start=1):
                    fmsg += f"{index}. <a href='{link}'>{name}</a>\n"
                    if len(fmsg.encode() + msg.encode()) > 2000:
                        if self.message.chat.type != ChatType.PRIVATE and not PM:
                            uploadmsg = await sendPhoto(msg + fmsg + warnmsg + logleechwarn, self.bot, self.message, reply_markup=button.build_menu(2))
                        await sendLeechLogIndexMsg(msg + fmsg, self.bot, self.message)
                        await asleep(1.5)
                        fmsg = ''
                if fmsg != '':
                    if self.message.chat.type != ChatType.PRIVATE and not PM:
                        uploadmsg = await sendPhoto(msg + fmsg + warnmsg + logleechwarn, self.bot, self.message, reply_markup=buttons.build_menu(2))
                    await sendLeechLogIndexMsg(msg + fmsg, self.bot, self.message, reply_markup=buttons.build_menu(2))
                main_loop.create_task(auto_delete_upload_message(self.bot, self.message, uploadmsg))
# --------------------------------------------------------------------------------------------------------------------------------------
            if self.seed:
                if self.newDir:
                    clean_target(self.newDir)
                async with queue_dict_lock:
                    if self.uid in non_queued_up:
                        non_queued_up.remove(self.uid)
                return
# --------------------------------------------------Mirror Msg Code--------------------------------------------------------------------
        else:
            msg = BotTheme(self.message.from_user.id).LISTENER_MSG3.format(lm8=config_dict['NAME_FONT'], lm9=escape(
                name), lm10=size, lm11=typ, lm12=get_readable_time(time() - self.message.date.timestamp()), lm13=self.tag)
            if typ == "Folder":
                msg += BotTheme(self.message.from_user.id).LISTENER_MSG4.format(
                    lm14=folders, lm15=files)
            hide = BotTheme(self.message.from_user.id).LISTENER_HIDE_MSG2.format(
                lhm3=config_dict['NAME_FONT'], lhm4=escape(name))
            # if config_dict['EMOJI_THEME']:
            #     msg = f"<b>╭🗂️ Name: </b><{config_dict['NAME_FONT']}>{escape(name)}</{config_dict['NAME_FONT']}>\n<b>├📐 Size: </b>{size}"
            #     msg += f'\n<b>├📦 Type: </b>{typ}'
            #     if typ == "Folder":
            #         msg += f'\n<b>├🗃️ SubFolders: </b>{folders}'
            #         msg += f'\n<b>├🗂️ Files: </b>{files}'
            #     msg += f'\n<b>├⌛ It Tooks:</b> {get_readable_time(time() - self.message.date.timestamp())}'
            #     msg += f'\n<b>╰👤 #Mirror_By: </b>{self.tag}\n\n'
            #     hide = f"<b>🗂️ Name: </b><{config_dict['NAME_FONT']}>{escape(name)}</{config_dict['NAME_FONT']}>\n"
            #     hide += f"\n<b>Hey {self.tag}!, I have sent your Mirror links in PM.</b>\n"
            # else:
            #     msg = f"<b>╭ Name: </b><{config_dict['NAME_FONT']}>{escape(name)}</{config_dict['NAME_FONT']}>\n<b>├ Size: </b>{size}"
            #     msg += f'\n<b>├ Type: </b>{typ}'
            #     if typ == "Folder":
            #         msg += f'\n<b>├ SubFolders: </b>{folders}'
            #         msg += f'\n<b>├ Files: </b>{files}'
            #     msg += f'\n<b>├ It Tooks:</b> {get_readable_time(time() - self.message.date.timestamp())}'
            #     msg += f'\n<b>╰ #Mirror_By: </b>{self.tag}\n\n'
            #     hide = f"<b>Name: </b><{config_dict['NAME_FONT']}>{escape(name)}</{config_dict['NAME_FONT']}>\n"
            #     hide += f"\n<b>Hey {self.tag}!, I have sent your Mirror links in PM.</b>\n"
            link = short_url(link, user_id_)
            if not config_dict['DISABLE_DRIVE_LINK']:
                # buttons.buildbutton(
                #     BotTheme(self.message.from_user.id).LISTENER_BUTTON1.format(lb1=link))
                buttons.buildbutton("☁️ Drive Link", link)
            LOGGER.info(f'Done Uploading {name}')
            _, INDEXURL = getGDriveUploadUtils(
                user_id_, self.u_index, self.c_index)
            if INDEX_URL := INDEXURL:
                url_path = rquote(f'{name}', safe='')
                share_url = f'{INDEX_URL}/{url_path}'
                if typ == "Folder":
                    share_url += '/'
                    share_url = short_url(share_url, user_id_)
                    # buttons.buildbutton(
                    #     BotTheme(self.message.from_user.id).LISTENER_BUTTON2.format(lb2=share_url))
                    buttons.buildbutton("⚡ Index Link", share_url)
                else:
                    share_url = short_url(share_url, user_id_)
                    # buttons.buildbutton(
                    # BotTheme(self.message.from_user.id).LISTENER_BUTTON2.format(lb2=share_url))
                    buttons.buildbutton("⚡ Index Link", share_url)
                    if config_dict['VIEW_LINK']:
                        share_urls = f'{INDEX_URL}/{url_path}?a=view'
                        share_urls = short_url(share_urls, user_id_)
                        # buttons.buildbutton(
                        # BotTheme(self.message.from_user.id).LISTENER_BUTTON3.format(lb3=share_urls))
                        buttons.buildbutton("🌐 View Link", share_urls)
# --------------------------------------------------Source Link Button Code---------------------------------------------------------------
                    if config_dict['SOURCE_LINK']:
                        try:
                            mesg = message_args[1]
                            if is_magnet(mesg):
                                link = telegraph.create_page(
                                    title=f"{config_dict['TITLE_NAME']} Source Link", content=mesg,)["path"]
                                buttons.buildbutton(
                                    f"🔗 Source Link", f"https://te.legra.ph/{link}")
                            elif is_url(mesg):
                                source_link = mesg
                                if source_link.startswith(("|", "pswd: ", "c:")):
                                    pass
                                else:
                                    buttons.buildbutton(
                                        f"🔗 Source Link", source_link)
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
                                            title=f"{config_dict['TITLE_NAME']} Source Link", content=source_link,)["path"]
                                        buttons.buildbutton(
                                            f"🔗 Source Link", f"https://te.legra.ph/{link}")
                                    else:
                                        buttons.buildbutton(
                                            f"🔗 Source Link", source_link)
                            except Exception:
                                pass
                    else:
                        pass
# ---------------------------------------------------------------------------------------------------------------------------------------
            if config_dict['BUTTON_FOUR_NAME'] != '' and config_dict['BUTTON_FOUR_URL'] != '':
                buttons.buildbutton(
                    f"{config_dict['BUTTON_FOUR_NAME']}", f"{config_dict['BUTTON_FOUR_URL']}")
            if config_dict['BUTTON_FIVE_NAME'] != '' and config_dict['BUTTON_FIVE_URL'] != '':
                buttons.buildbutton(
                    f"{config_dict['BUTTON_FIVE_NAME']}", f"{config_dict['BUTTON_FIVE_URL']}")
            if config_dict['BUTTON_SIX_NAME'] != '' and config_dict['BUTTON_SIX_URL'] != '':
                buttons.buildbutton(
                    f"{config_dict['BUTTON_SIX_NAME']}", f"{config_dict['BUTTON_SIX_URL']}")
            button = ButtonMaker()
            button.buildbutton("View links in PM", f"{botstart}")
            if PM:
                await sendPhoto(msg, self.bot, self.message, reply_markup=buttons.build_menu(2), chat_id=user_id_)
                uploadmsg = await sendPhoto(hide + warnmsg + pmwarn + logwarn, self.bot, self.message, reply_markup=button.build_menu(1))
            else:
                if self.message.chat.type != ChatType.PRIVATE:
                    if config_dict['SAVE_MSG']:
                        buttons.sbutton("Save This Message", 'save', 'footer')
                uploadmsg = await sendPhoto(msg + warnmsg + logwarn, self.bot, self.message, reply_markup=buttons.build_menu(2))

            await sendMirrorLogMessage(msg, self.bot, self.message, PM, buttons)
            main_loop.create_task(auto_delete_upload_message(self.bot, self.message, uploadmsg))
# --------------------------------------------------------------------------------------------------------------------------------------
            if self.seed:
                if self.isZip:
                    clean_target(f"{self.dir}/{name}")
                elif self.newDir:
                    clean_target(self.newDir)
                async with queue_dict_lock:
                    if self.uid in non_queued_up:
                        non_queued_up.remove(self.uid)
                return
        clean_download(self.dir)
        async with download_dict_lock:
            if self.uid in download_dict.keys():
                del download_dict[self.uid]
            count = len(download_dict)
        if count == 0:
            await self.clean()
        else:
            await update_all_messages()

        async with queue_dict_lock:
            if self.uid in non_queued_up:
                non_queued_up.remove(self.uid)

        await start_from_queued()

    async def onDownloadError(self, error):
        try:
            if config_dict['AUTO_DELETE_UPLOAD_MESSAGE_DURATION'] != -1 and self.reply_to is not None:
                await self.reply_to.delete()
            else:
                pass
        except Exception as e:
            LOGGER.warning(e)
            pass
        clean_download(self.dir)
        if self.newDir:
            clean_download(self.newDir)
        async with download_dict_lock:
            if self.uid in download_dict.keys():
                del download_dict[self.uid]
            count = len(download_dict)
        msg = f"{self.tag} your download has been stopped due to: {escape(error)}"
        await sendMessage(msg, self.bot, self.message)
        if count == 0:
            await self.clean()
        else:
            await update_all_messages()

        if not self.isPrivate and config_dict['INCOMPLETE_TASK_NOTIFIER'] and DATABASE_URL:
            DbManger().rm_complete_task(self.message.link)

        async with queue_dict_lock:
            if self.uid in queued_dl:
                del queued_dl[self.uid]
            if self.uid in non_queued_dl:
                non_queued_dl.remove(self.uid)
            if self.uid in queued_up:
                del queued_up[self.uid]
            if self.uid in non_queued_up:
                non_queued_up.remove(self.uid)

        self.queuedUp = False
        await start_from_queued()

    async def onUploadError(self, error):
        clean_download(self.dir)
        if self.newDir:
            clean_download(self.newDir)
        async with download_dict_lock:
            if self.uid in download_dict.keys():
                del download_dict[self.uid]
            count = len(download_dict)
        await sendMessage(f"{self.tag} {escape(error)}", self.bot, self.message)
        if count == 0:
            await self.clean()
        else:
            await update_all_messages()

        if not self.isPrivate and config_dict['INCOMPLETE_TASK_NOTIFIER'] and DATABASE_URL:
            DbManger().rm_complete_task(self.message.link)
        async with queue_dict_lock:
            if self.uid in queued_up:
                del queued_up[self.uid]
            if self.uid in non_queued_up:
                non_queued_up.remove(self.uid)

        self.queuedUp = False
        await start_from_queued()

    def __user_settings(self):
        user_id = self.message.from_user.id
        user_dict = user_data.get(user_id, False)
