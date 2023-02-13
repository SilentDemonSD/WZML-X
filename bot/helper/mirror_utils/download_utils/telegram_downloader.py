from logging import getLogger, WARNING
from time import time
from threading import RLock
from asyncio import Lock
from bot import LOGGER, download_dict, download_dict_lock, config_dict, app, user_data, non_queued_dl, non_queued_up, queued_dl, queue_dict_lock, bot
from bot.helper.ext_utils.bot_utils import get_readable_file_size, userlistype
from ..status_utils.telegram_download_status import TelegramDownloadStatus
from bot.helper.mirror_utils.status_utils.queue_status import QueueStatus
from bot.helper.telegram_helper.message_utils import sendMessage, sendStatusMessage, sendFile
from bot.helper.mirror_utils.upload_utils.gdriveTools import GoogleDriveHelper
from bot.helper.ext_utils.fs_utils import check_storage_threshold

global_lock = Lock()
GLOBAL_GID = set()
getLogger("pyrogram").setLevel(WARNING)


class TelegramDownloadHelper:

    def __init__(self, listener):
        self.name = ""
        self.size = 0
        self.progress = 0
        self.downloaded_bytes = 0
        self.__start_time = time()
        self.__listener = listener
        self.__id = ""
        self.__is_cancelled = False
        self.__resource_lock = RLock()
        self.app = app if app is not None else bot

    @property
    def download_speed(self):
        with self.__resource_lock:
            return self.downloaded_bytes / (time() - self.__start_time)

    async def __onDownloadStart(self, name, size, file_id, from_queue):
        async with global_lock:
            GLOBAL_GID.add(file_id)
        with self.__resource_lock:
            self.name = name
            self.size = size
            self.__id = file_id
        async with download_dict_lock:
            download_dict[self.__listener.uid] = TelegramDownloadStatus(
                self, self.__listener, self.__id)
        async with queue_dict_lock:
            non_queued_dl.add(self.__listener.uid)
        if not from_queue:
            await self.__listener.onDownloadStart()
            await sendStatusMessage(self.__listener.message, self.__listener.bot)
            LOGGER.info(f'Download from Telegram: {name}')
        else:
            LOGGER.info(f'Start Queued Download from Telegram: {name}')

    async def __onDownloadProgress(self, current, total):
        if self.__is_cancelled:
            self.app.stop_transmission()
            return
        with self.__resource_lock:
            self.downloaded_bytes = current
            try:
                self.progress = current / self.size * 100
            except ZeroDivisionError:
                pass

    async def __onDownloadError(self, error):
        async with global_lock:
            try:
                GLOBAL_GID.remove(self.__id)
            except:
                pass
        await self.__listener.onDownloadError(error)

    async def __onDownloadComplete(self):
        async with global_lock:
            GLOBAL_GID.remove(self.__id)
        await self.__listener.onDownloadComplete()

    async def __download(self, message, path):
        try:
            download = await message.download(file_name=path, progress=self.__onDownloadProgress)
            if self.__is_cancelled:
                await self.__onDownloadError('Cancelled by user!')
                return
        except Exception as e:
            LOGGER.error(str(e))
            return await self.__onDownloadError(str(e))
        if download is not None:
            await self.__onDownloadComplete()
        elif not self.__is_cancelled:
            await self.__onDownloadError('Internal error occurred')

    async def add_download(self, message, path, filename, from_queue=False):
        _dmsg = await self.app.get_messages(message.chat.id, reply_to_message_ids=message.id)
        user_id = message.from_user.id
        user_dict = user_data.get(user_id, False)
        media = _dmsg.document or _dmsg.video or _dmsg.audio or None
        if media is not None:
            async with global_lock:
                # For avoiding locking the thread lock for long time unnecessarily
                download = media.file_unique_id not in GLOBAL_GID
            if filename == "":
                name = media.file_name
            else:
                name = filename
                path = path + name

            if from_queue or download:
                size = media.file_size
                gid = media.file_unique_id
                IS_USRTD = user_dict.get('is_usertd') if user_dict and user_dict.get(
                    'is_usertd') else False
                if config_dict['STOP_DUPLICATE'] and not self.__listener.isLeech and IS_USRTD == False:
                    LOGGER.info('Checking File/Folder if already in Drive...')
                    smsg, button = await GoogleDriveHelper(
                        user_id=user_id).drive_list(name, True, True)
                    if smsg:
                        tegr, html, tgdi = userlistype(user_id)
                        if tegr:
                            return await sendMessage("File/Folder is already available in Drive.\nHere are the search results:", self.__listener.bot, self.__listener.message, button)
                        elif html:
                            return await sendFile(self.__listener.bot, self.__listener.message, button, f"File/Folder is already available in Drive. Here are the search results:\n\n{smsg}")
                        else:
                            return await sendMessage(smsg, self.__listener.bot, self.__listener.message, button)
                if config_dict['STORAGE_THRESHOLD']:
                    STORAGE_THRESHOLD = config_dict['STORAGE_THRESHOLD']
                    arch = any(
                        [self.__listener.isZip, self.__listener.extract])
                    acpt = check_storage_threshold(size, arch)
                    if not acpt:
                        msg = f'You must leave {STORAGE_THRESHOLD}GB free storage.'
                        msg += f'\nYour File/Folder size is {get_readable_file_size(size)}'
                        await sendMessage(msg, self.__listener.bot, self.__listener.message, button)
                        return
                all_limit = config_dict['QUEUE_ALL']
                dl_limit = config_dict['QUEUE_DOWNLOAD']
                if all_limit or dl_limit:
                    added_to_queue = False
                    async with queue_dict_lock:
                        dl = len(non_queued_dl)
                        up = len(non_queued_up)
                        if (all_limit and dl + up >= all_limit and (not dl_limit or dl >= dl_limit)) or (dl_limit and dl >= dl_limit):
                            added_to_queue = True
                            queued_dl[self.__listener.uid] = [
                                'tg', message, path, filename, self.__listener]
                    if added_to_queue:
                        LOGGER.info(f"Added to Queue/Download: {name}")
                        async with download_dict_lock:
                            download_dict[self.__listener.uid] = QueueStatus(
                                name, size, gid, self.__listener, 'Dl')
                        await self.__listener.onDownloadStart()
                        await sendStatusMessage(self.__listener.message, self.__listener.bot)
                        async with global_lock:
                            GLOBAL_GID.add(gid)
                        return
                await self.__onDownloadStart(name, size, gid, from_queue)
                await self.__download(_dmsg, path)
            else:
                await self.__onDownloadError('File already being downloaded!')
        else:
            await self.__onDownloadError('No document in the replied message')

    def cancel_download(self):
        LOGGER.info(f'Cancelling download on user request: {self.__id}')
        self.__is_cancelled = True
