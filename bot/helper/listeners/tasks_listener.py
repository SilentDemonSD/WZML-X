#!/usr/bin/env python3
from random import choice
from time import time
from requests import utils as rutils
from aiofiles.os import path as aiopath, remove as aioremove, listdir, makedirs
from os import walk, path as ospath
from html import escape
from aioshutil import move
from asyncio import create_subprocess_exec, sleep, Event
from pyrogram.enums import ChatType

from bot import OWNER_ID, Interval, aria2, DOWNLOAD_DIR, download_dict, download_dict_lock, LOGGER, bot_name, DATABASE_URL, \
    MAX_SPLIT_SIZE, config_dict, status_reply_dict_lock, user_data, non_queued_up, non_queued_dl, queued_up, \
    queued_dl, queue_dict_lock, bot, GLOBAL_EXTENSION_FILTER
from bot.helper.ext_utils.bot_utils import extra_btns, sync_to_async, get_readable_file_size, get_readable_time, is_mega_link, is_gdrive_link
from bot.helper.ext_utils.fs_utils import get_base_name, get_path_size, clean_download, clean_target, \
    is_first_archive_split, is_archive, is_archive_split, join_files
from bot.helper.ext_utils.leech_utils import split_file, format_filename
from bot.helper.ext_utils.exceptions import NotSupportedExtractionArchive
from bot.helper.ext_utils.task_manager import start_from_queued
from bot.helper.mirror_utils.status_utils.extract_status import ExtractStatus
from bot.helper.mirror_utils.status_utils.zip_status import ZipStatus
from bot.helper.mirror_utils.status_utils.split_status import SplitStatus
from bot.helper.mirror_utils.status_utils.gdrive_status import GdriveStatus
from bot.helper.mirror_utils.status_utils.telegram_status import TelegramStatus
from bot.helper.mirror_utils.status_utils.ddl_status import DDLStatus
from bot.helper.mirror_utils.status_utils.rclone_status import RcloneStatus
from bot.helper.mirror_utils.status_utils.queue_status import QueueStatus
from bot.helper.mirror_utils.upload_utils.gdriveTools import GoogleDriveHelper
from bot.helper.mirror_utils.upload_utils.pyrogramEngine import TgUploader
from bot.helper.mirror_utils.upload_utils.ddlEngine import DDLUploader
from bot.helper.mirror_utils.rclone_utils.transfer import RcloneTransferHelper
from bot.helper.telegram_helper.message_utils import sendBot, sendMessage, delete_all_messages, delete_links, sendMultiMessage, update_all_messages
from bot.helper.telegram_helper.button_build import ButtonMaker
from bot.helper.ext_utils.db_handler import DbManger
from bot.helper.themes import BotTheme


class MirrorLeechListener:
    def __init__(self, message, compress=False, extract=False, isQbit=False, isLeech=False, tag=None, select=False, seed=False, sameDir=None, rcFlags=None, upPath=None, isClone=False, join=False, isYtdlp=False, source_url=None):
        if sameDir is None:
            sameDir = {}
        self.message = message
        self.uid = message.id
        self.extract = extract
        self.compress = compress
        self.isQbit = isQbit
        self.isLeech = isLeech
        self.isClone = isClone
        self.isMega = is_mega_link(source_url) if source_url else False
        self.isGdrive = is_gdrive_link(source_url) if source_url else False
        self.isYtdlp = isYtdlp
        self.tag = tag
        self.seed = seed
        self.newDir = ""
        self.dir = f"{DOWNLOAD_DIR}{self.uid}"
        self.select = select
        self.isSuperGroup = message.chat.type in [ChatType.SUPERGROUP, ChatType.CHANNEL]
        self.isPrivate = message.chat.type == ChatType.BOT
        self.suproc = None
        self.sameDir = sameDir
        self.rcFlags = rcFlags
        self.upPath = upPath
        self.random_pic = 'IMAGES'
        self.join = join
        self.leechlogmsg = None
        self.upload_details = {}
        self.source_url = source_url if source_url and source_url.startswith('http') else ("https://t.me/share/url?url=" + source_url) if source_url else message.link
        self.__setModeEng()

    async def clean(self):
        try:
            async with status_reply_dict_lock:
                if Interval:
                    Interval[0].cancel()
                    Interval.clear()
            await sync_to_async(aria2.purge)
            await delete_all_messages()
        except:
            pass

    def __setModeEng(self):
        mode = 'Leech' if self.isLeech else 'Clone' if self.isClone else 'RClone' if self.upPath not in ['gd', 'ddl'] else 'DDL' if self.upPath != 'gd' else 'GDrive'
        mode += ' as Zip' if self.compress else ' as Unzip' if self.extract else ''
        mode += f" | #{'qbit' if self.isQbit else 'ytdlp' if self.isYtdlp else 'gdrive' if (self.isClone or self.isGdrive) else 'mega' if self.isMega else 'aria2' if self.source_url else 'tg'}"
        self.upload_details['mode'] = mode
        
    async def onDownloadStart(self):
        if self.isSuperGroup and config_dict['INCOMPLETE_TASK_NOTIFIER'] and DATABASE_URL:
            await DbManger().add_incomplete_task(self.message.chat.id, self.message.link, self.tag)

    async def onDownloadComplete(self):
        multi_links = False
        while True:
            if self.sameDir:
                if self.sameDir['total'] in [1, 0] or self.sameDir['total'] > 1 and len(self.sameDir['tasks']) > 1:
                    break
            else:
                break
            await sleep(0.2)
        async with download_dict_lock:
            if self.sameDir and self.sameDir['total'] > 1:
                self.sameDir['tasks'].remove(self.uid)
                self.sameDir['total'] -= 1
                folder_name = self.sameDir['name']
                spath = f"{self.dir}/{folder_name}"
                des_path = f"{DOWNLOAD_DIR}{list(self.sameDir['tasks'])[0]}/{folder_name}"
                await makedirs(des_path, exist_ok=True)
                for item in await listdir(spath):
                    if item.endswith(('.aria2', '.!qB')):
                        continue
                    item_path = f"{self.dir}/{folder_name}/{item}"
                    if item in await listdir(des_path):
                        await move(item_path, f'{des_path}/{self.uid}-{item}')
                    else:
                        await move(item_path, f'{des_path}/{item}')
                multi_links = True
            download = download_dict[self.uid]
            name = str(download.name()).replace('/', '')
            gid = download.gid()
        LOGGER.info(f"Download Completed: {name}")
        if multi_links:
            await self.onUploadError('Downloaded! Starting other part of the Task...')
            return
        if name == "None" or self.isQbit or not await aiopath.exists(f"{self.dir}/{name}"):
            try:
                files = await listdir(self.dir)
            except Exception as e:
                await self.onUploadError(str(e))
                return
            name = files[-1]
            if name == "yt-dlp-thumb":
                name = files[0]

        dl_path = f"{self.dir}/{name}"
        up_path = ''
        size = await get_path_size(dl_path)
        async with queue_dict_lock:
            if self.uid in non_queued_dl:
                non_queued_dl.remove(self.uid)
        await start_from_queued()
        user_dict = user_data.get(self.message.from_user.id, {})
        
        if self.join:
            if await aiopath.isdir(dl_path):
                await join_files(dl_path)

        if self.extract:
            pswd = self.extract if isinstance(self.extract, str) else ''
            try:
                if await aiopath.isfile(dl_path):
                    up_path = get_base_name(dl_path)
                LOGGER.info(f"Extracting: {name}")
                async with download_dict_lock:
                    download_dict[self.uid] = ExtractStatus(
                        name, size, gid, self)
                if await aiopath.isdir(dl_path):
                    if self.seed:
                        self.newDir = f"{self.dir}10000"
                        up_path = f"{self.newDir}/{name}"
                    else:
                        up_path = dl_path
                    for dirpath, _, files in await sync_to_async(walk, dl_path, topdown=False):
                        for file_ in files:
                            if is_first_archive_split(file_) or is_archive(file_) and not file_.endswith('.rar'):
                                f_path = ospath.join(dirpath, file_)
                                t_path = dirpath.replace(
                                    self.dir, self.newDir) if self.seed else dirpath
                                cmd = [
                                    "7z", "x", f"-p{pswd}", f_path, f"-o{t_path}", "-aot", "-xr!@PaxHeader"]
                                if not pswd:
                                    del cmd[2]
                                if self.suproc == 'cancelled' or self.suproc is not None and self.suproc.returncode == -9:
                                    return
                                self.suproc = await create_subprocess_exec(*cmd)
                                code = await self.suproc.wait()
                                if code == -9:
                                    return
                                elif code != 0:
                                    LOGGER.error(
                                        'Unable to extract archive splits!')
                        if not self.seed and self.suproc is not None and self.suproc.returncode == 0:
                            for file_ in files:
                                if is_archive_split(file_) or is_archive(file_):
                                    del_path = ospath.join(dirpath, file_)
                                    try:
                                        await aioremove(del_path)
                                    except:
                                        return
                else:
                    if self.seed:
                        self.newDir = f"{self.dir}10000"
                        up_path = up_path.replace(self.dir, self.newDir)
                    cmd = ["7z", "x", f"-p{pswd}", dl_path,
                           f"-o{up_path}", "-aot", "-xr!@PaxHeader"]
                    if not pswd:
                        del cmd[2]
                    if self.suproc == 'cancelled':
                        return
                    self.suproc = await create_subprocess_exec(*cmd)
                    code = await self.suproc.wait()
                    if code == -9:
                        return
                    elif code == 0:
                        LOGGER.info(f"Extracted Path: {up_path}")
                        if not self.seed:
                            try:
                                await aioremove(dl_path)
                            except:
                                return
                    else:
                        LOGGER.error(
                            'Unable to extract archive! Uploading anyway')
                        self.newDir = ""
                        up_path = dl_path
            except NotSupportedExtractionArchive:
                LOGGER.info("Not any valid archive, uploading file as it is.")
                self.newDir = ""
                up_path = dl_path

        if self.compress:
            pswd = self.compress if isinstance(self.compress, str) else ''
            if up_path:
                dl_path = up_path
                up_path = f"{up_path}.zip"
            elif self.seed and self.isLeech:
                self.newDir = f"{self.dir}10000"
                up_path = f"{self.newDir}/{name}.zip"
            else:
                up_path = f"{dl_path}.zip"
            async with download_dict_lock:
                download_dict[self.uid] = ZipStatus(name, size, gid, self)
            LEECH_SPLIT_SIZE = user_dict.get('split_size', False) or config_dict['LEECH_SPLIT_SIZE']
            cmd = ["7z", f"-v{LEECH_SPLIT_SIZE}b", "a",
                   "-mx=0", f"-p{pswd}", up_path, dl_path]
            for ext in GLOBAL_EXTENSION_FILTER:
                ex_ext = f'-xr!*.{ext}'
                cmd.append(ex_ext)
            if self.isLeech and int(size) > LEECH_SPLIT_SIZE:
                if not pswd:
                    del cmd[4]
                LOGGER.info(f'Zip: orig_path: {dl_path}, zip_path: {up_path}.0*')
            else:
                del cmd[1]
                if not pswd:
                    del cmd[3]
                LOGGER.info(f'Zip: orig_path: {dl_path}, zip_path: {up_path}')
            if self.suproc == 'cancelled':
                return
            self.suproc = await create_subprocess_exec(*cmd)
            code = await self.suproc.wait()
            if code == -9:
                return
            elif not self.seed:
                await clean_target(dl_path)

        if not self.compress and not self.extract:
            up_path = dl_path

        up_dir, up_name = up_path.rsplit('/', 1)
        size = await get_path_size(up_dir)
        if self.isLeech:
            m_size = []
            o_files = []
            if not self.compress:
                checked = False
                LEECH_SPLIT_SIZE = user_dict.get(
                    'split_size', False) or config_dict['LEECH_SPLIT_SIZE']
                for dirpath, _, files in await sync_to_async(walk, up_dir, topdown=False):
                    for file_ in files:
                        f_path = ospath.join(dirpath, file_)
                        f_size = await aiopath.getsize(f_path)
                        if f_size > LEECH_SPLIT_SIZE:
                            if not checked:
                                checked = True
                                async with download_dict_lock:
                                    download_dict[self.uid] = SplitStatus(
                                        up_name, size, gid, self)
                                LOGGER.info(f"Splitting: {up_name}")
                            res = await split_file(f_path, f_size, file_, dirpath, LEECH_SPLIT_SIZE, self)
                            if not res:
                                return
                            if res == "errored":
                                if f_size <= MAX_SPLIT_SIZE:
                                    continue
                                try:
                                    await aioremove(f_path)
                                except:
                                    return
                            elif not self.seed or self.newDir:
                                try:
                                    await aioremove(f_path)
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
                event = Event()
                queued_up[self.uid] = event
        if added_to_queue:
            async with download_dict_lock:
                download_dict[self.uid] = QueueStatus(
                    name, size, gid, self, 'Up')
            await event.wait()
            async with download_dict_lock:
                if self.uid not in download_dict:
                    return
            LOGGER.info(f'Start from Queued/Upload: {name}')
        async with queue_dict_lock:
            non_queued_up.add(self.uid)
        if self.isLeech:
            size = await get_path_size(up_dir)
            for s in m_size:
                size = size - s
            LOGGER.info(f"Leech Name: {up_name}")
            tg = TgUploader(up_name, up_dir, self)
            tg_upload_status = TelegramStatus(
                tg, size, self.message, gid, 'up', self.upload_details)
            async with download_dict_lock:
                download_dict[self.uid] = tg_upload_status
            await update_all_messages()
            await tg.upload(o_files, m_size, size)
        elif self.upPath == 'gd':
            size = await get_path_size(up_path)
            LOGGER.info(f"Upload Name: {up_name}")
            drive = GoogleDriveHelper(up_name, up_dir, self)
            upload_status = GdriveStatus(drive, size, self.message, gid, 'up', self.upload_details)
            async with download_dict_lock:
                download_dict[self.uid] = upload_status
            await update_all_messages()
            await sync_to_async(drive.upload, up_name, size)
        elif self.upPath == 'ddl':
            size = await get_path_size(up_path)
            LOGGER.info(f"Upload Name: {up_name} via DDL")
            ddl = DDLUploader(up_name, up_dir, self)
            ddl_upload_status = DDLStatus(ddl, size, self.message, gid, self.upload_details)
            async with download_dict_lock:
                download_dict[self.uid] = ddl_upload_status
            await update_all_messages()
            await ddl.upload(up_name, size)
        else:
            size = await get_path_size(up_path)
            LOGGER.info(f"Upload Name: {up_name} via RClone")
            RCTransfer = RcloneTransferHelper(self, up_name)
            async with download_dict_lock:
                download_dict[self.uid] = RcloneStatus(
                    RCTransfer, self.message, gid, 'up', self.upload_details)
            await update_all_messages()
            await RCTransfer.upload(up_path, size)

    async def onUploadComplete(self, link, size, files, folders, mime_type, name, rclonePath=''):
        if self.isSuperGroup and config_dict['INCOMPLETE_TASK_NOTIFIER'] and DATABASE_URL:
            await DbManger().rm_complete_task(self.message.link)
        user_id = self.message.from_user.id
        name, _ = await format_filename(name, user_id, isMirror=not self.isLeech)
        user_dict = user_data.get(user_id, {})
        msg = BotTheme('NAME', Name="Task has been Completed!"if config_dict['SAFE_MODE'] else escape(name))
        msg += BotTheme('SIZE', Size=get_readable_file_size(size))
        msg += BotTheme('ELAPSE', Time=get_readable_time(time() - self.message.date.timestamp()))
        msg += BotTheme('MODE', Mode=self.upload_details['mode'])
        LOGGER.info(f'Task Done: {name}')
        buttons = ButtonMaker()
        if self.isLeech:
            msg += BotTheme('L_TOTAL_FILES', Files=folders)
            if mime_type != 0:
                msg += BotTheme('L_CORRUPTED_FILES', Corrupt=mime_type)
            msg += BotTheme('L_CC', Tag=self.tag)
            if not files:
                if self.isPrivate:
                    msg += BotTheme('PM_BOT_MSG')
                await sendMessage(self.message, msg, photo=self.random_pic)
            else:
                toPM = False
                if config_dict['BOT_PM'] or user_dict.get('bot_pm'):
                    await sendBot(self.message, msg + BotTheme('PM_BOT_MSG'), photo=self.random_pic)
                    if self.isSuperGroup:
                        btn = ButtonMaker()
                        if self.source_url and config_dict['SOURCE_LINK']:
                            btn.ubutton(BotTheme('SOURCE_URL'), self.source_url)
                        btn.ubutton(BotTheme('CHECK_PM'), f"https://t.me/{bot_name}", 'header')
                        btn = extra_btns(btn)
                        toPM = True
                        await sendMessage(self.message, msg + BotTheme('L_BOT_MSG'), btn.build_menu(2), self.random_pic)
                msg += BotTheme('L_LL_MSG')
                if self.leechlogmsg:
                    self.leechlogmsg._client = bot
                fmsg = '\n\n'
                for index, (link, name) in enumerate(files.items(), start=1):
                    fmsg += f"{index}. <a href='{link}'>{name}</a>\n"
                    limit = 4000 if not config_dict['IMAGES'] else 1000
                    if len(fmsg.encode() + msg.encode()) > limit:
                        if config_dict['SAVE_MSG']:
                            buttons.ibutton(BotTheme('SAVE_MSG'), 'save', 'footer')
                        if self.source_url and config_dict['SOURCE_LINK']:
                            buttons.ubutton(BotTheme('SOURCE_URL'), self.source_url)
                        if self.leechlogmsg or not toPM:
                            log_msg = await sendMessage(self.leechlogmsg if self.leechlogmsg else self.message, msg + fmsg, buttons.build_menu(1), self.random_pic)
                        await sleep(1)
                        fmsg = '\n\n'
                if fmsg != '\n\n':
                    if config_dict['SAVE_MSG']:
                        buttons.ibutton(BotTheme('SAVE_MSG'), 'save', 'footer')
                    if self.source_url and config_dict['SOURCE_LINK']:
                        buttons.ubutton(BotTheme('SOURCE_URL'), self.source_url)
                    if self.leechlogmsg or not toPM:
                        log_msg = await sendMessage(self.leechlogmsg if self.leechlogmsg else self.message, msg + fmsg, buttons.build_menu(1), self.random_pic)
                if self.leechlogmsg and not (config_dict['BOT_PM'] or user_dict.get('bot_pm')):
                    buttons = ButtonMaker()
                    buttons.ubutton(BotTheme('CHECK_LL'), log_msg.link)
                    await sendMessage(self.message, msg, buttons.build_menu(1), self.random_pic)
            if self.seed:
                if self.newDir:
                    await clean_target(self.newDir)
                async with queue_dict_lock:
                    if self.uid in non_queued_up:
                        non_queued_up.remove(self.uid)
                await start_from_queued()
                return
        else:
            is_DDL = 'gofile' in link or 'streamsb' in link
            msg += BotTheme('M_TYPE', Mimetype=mime_type)
            if mime_type == "Folder":
                if not is_DDL:
                    msg += BotTheme('M_SUBFOLD', Folder=folders)
                    msg += BotTheme('TOTAL_FILES', Files=files)
            if link or rclonePath and config_dict['RCLONE_SERVE_URL']:

                if is_DDL:
                    buttons.ubutton(BotTheme('DDL_LINK', Serv='GoFile'), link)
                elif link:
                    if user_id == OWNER_ID or not config_dict['DISABLE_DRIVE_LINK']:
                        buttons.ubutton(BotTheme('CLOUD_LINK'), link)
                else:
                    msg += BotTheme('RCPATH', RCpath=rclonePath)
                if rclonePath and (RCLONE_SERVE_URL := config_dict['RCLONE_SERVE_URL']):
                    remote, path = rclonePath.split(':', 1)
                    url_path = rutils.quote(f'{path}')
                    share_url = f'{RCLONE_SERVE_URL}/{remote}/{url_path}'
                    if mime_type == "Folder":
                        share_url += '/'
                    buttons.ubutton(BotTheme('RCLONE_LINK'), share_url)
                elif (INDEX_URL := config_dict['INDEX_URL']) and not rclonePath and not is_DDL:
                    url_path = rutils.quote(f'{name}')
                    share_url = f'{INDEX_URL}/{url_path}'
                    if mime_type == "Folder":
                        share_url += '/'
                        buttons.ubutton(BotTheme('INDEX_LINK'), share_url)
                    else:
                        buttons.ubutton(BotTheme('INDEX_LINK'), share_url)
                        if mime_type.startswith(('image', 'video', 'audio')):
                            share_urls = f'{INDEX_URL}/{url_path}?a=view'
                            buttons.ubutton(BotTheme('VIEW_LINK'), share_urls)

                buttons = extra_btns(buttons)
                button = buttons.build_menu(2)
            else:
                msg += BotTheme('RCPATH', RCpath=rclonePath)
                button = None
            msg += BotTheme('M_CC', Tag=self.tag)


            if config_dict['BOT_PM'] or user_dict.get('bot_pm'):
                await sendBot(self.message, msg, button, self.random_pic)
                nmsg = msg + BotTheme('M_BOT_MSG')
                if button is not None:
                    if config_dict['SAVE_MSG']:
                        buttons.ibutton(BotTheme('SAVE_MSG'), 'save', 'footer')
                    button = buttons.build_menu(2)
                btns = ButtonMaker()
                btns = extra_btns(btns)
                if self.source_url and config_dict['SOURCE_LINK']:
                    btns.ubutton(BotTheme('SOURCE_URL'), self.source_url)
                btns.ubutton(BotTheme('CHECK_PM'), f"https://t.me/{bot_name}", 'header')
                await sendMessage(self.message, nmsg, btns.build_menu(1), self.random_pic)
            else:
                if config_dict['SAVE_MSG']:
                    if button is not None:
                        if self.source_url and config_dict['SOURCE_LINK']:
                            buttons.ubutton(BotTheme('SOURCE_URL'), self.source_url)
                        buttons.ibutton(BotTheme('SAVE_MSG'), 'save', 'footer')
                        button = buttons.build_menu(2)
                await sendMessage(self.message, msg, button, self.random_pic)

            if ids := config_dict['MIRROR_LOG_ID']:
                await sendMultiMessage(self.message, ids, msg, button, self.random_pic)

            if self.seed:
                if self.newDir:
                    await clean_target(self.newDir)
                elif self.compress:
                    await clean_target(f"{self.dir}/{name}")
                async with queue_dict_lock:
                    if self.uid in non_queued_up:
                        non_queued_up.remove(self.uid)
                await start_from_queued()
                return

        await clean_download(self.dir)
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
        await delete_links(self.message)

    async def onDownloadError(self, error, button=None):
        async with download_dict_lock:
            if self.uid in download_dict.keys():
                del download_dict[self.uid]
            count = len(download_dict)
            if self.sameDir and self.uid in self.sameDir['tasks']:
                self.sameDir['tasks'].remove(self.uid)
                self.sameDir['total'] -= 1
        msg = f'''<i><b>Download Stopped!</b></i>
┠ <b>Task for:</b> {self.tag}
┃
┠ <b>Due To:</b> {escape(error)}
┠ <b>Mode:</b> {self.upload_details['mode']}
┖ <b>Elapsed:</b> {get_readable_time(time() - self.message.date.timestamp())}'''
        await sendMessage(self.message, msg, button)
        if count == 0:
            await self.clean()
        else:
            await update_all_messages()

        if self.isSuperGroup and config_dict['INCOMPLETE_TASK_NOTIFIER'] and DATABASE_URL:
            await DbManger().rm_complete_task(self.message.link)

        async with queue_dict_lock:
            if self.uid in queued_dl:
                queued_dl[self.uid].set()
                del queued_dl[self.uid]
            if self.uid in queued_up:
                queued_up[self.uid].set()
                del queued_up[self.uid]
            if self.uid in non_queued_dl:
                non_queued_dl.remove(self.uid)
            if self.uid in non_queued_up:
                non_queued_up.remove(self.uid)

        await start_from_queued()
        await sleep(3)
        await clean_download(self.dir)
        if self.newDir:
            await clean_download(self.newDir)

    async def onUploadError(self, error):
        async with download_dict_lock:
            if self.uid in download_dict.keys():
                del download_dict[self.uid]
            count = len(download_dict)
        msg = f'''<i><b>Upload Stopped!</b></i>
┠ <b>Task for:</b> {self.tag}
┃
┠ <b>Due To:</b> {escape(error)}
┠ <b>Mode:</b> {self.upload_details['mode']}
┖ <b>Elapsed:</b> {get_readable_time(time() - self.message.date.timestamp())}'''
        await sendMessage(self.message, msg)
        if count == 0:
            await self.clean()
        else:
            await update_all_messages()

        if self.isSuperGroup and config_dict['INCOMPLETE_TASK_NOTIFIER'] and DATABASE_URL:
            await DbManger().rm_complete_task(self.message.link)

        async with queue_dict_lock:
            if self.uid in queued_dl:
                queued_dl[self.uid].set()
                del queued_dl[self.uid]
            if self.uid in queued_up:
                queued_up[self.uid].set()
                del queued_up[self.uid]
            if self.uid in non_queued_dl:
                non_queued_dl.remove(self.uid)
            if self.uid in non_queued_up:
                non_queued_up.remove(self.uid)

        await start_from_queued()
        await sleep(3)
        await clean_download(self.dir)
        if self.newDir:
            await clean_download(self.newDir)
