#!/usr/bin/env python3
import contextlib
from time import time
from asyncio import Lock, sleep
from pyrogram.errors import FloodWait

from bot import LOGGER, task_dict, task_dict_lock, non_queued_dl, queue_dict_lock, bot, user
from bot.helper.mirror_leech_utils.status_utils.telegram_status import TelegramStatus
from bot.helper.mirror_leech_utils.status_utils.queue_status import QueueStatus
from bot.helper.tele_swi_helper.message_utils import sendStatusMessage, sendMessage, delete_links
from bot.helper.ext_utils.task_manager import is_queued, limit_checker, stop_duplicate_check

global_lock = Lock()
GLOBAL_GID = set()


class TelegramDownloadHelper:

    def __init__(self, listener):
        self._processed_bytes = 0
        self._start_time = time()
        self._listener = listener
        self._client = bot
        self._decrypter = None
        self._id = ""

    @property
    def speed(self):
        return self._processed_bytes / (time() - self._start_time)

    @property
    def processed_bytes(self):
        return self._processed_bytes

    async def __onDownloadStart(self, file_id, from_queue):
        async with global_lock:
            GLOBAL_GID.add(file_id)
        self._id = file_id
        async with task_dict_lock:
            task_dict[self._listener.mid] = TelegramStatus(
                self._listener, self, file_id[:12], 'dl', self._listener.upload_details)

        if not from_queue:
            await self._listener.onDownloadStart()
            if self._listener.multi <= 1:
                await sendStatusMessage(self._listener.message)
            LOGGER.info(f'Download from Telegram: {self._listener.name}')
        else:
            LOGGER.info(f'Start Queued Download from Telegram: {self._listener.name}')

    async def __onDownloadProgress(self, current, total):
        if self._listener.isCancelled:
            self._client.stop_transmission()
        self._processed_bytes = current

    async def __onDownloadError(self, error):
        async with global_lock:
            with contextlib.suppress(Exception):
                GLOBAL_GID.remove(self._id)
        await self._listener.onDownloadError(error)

    async def __onDownloadComplete(self):
        await self._listener.onDownloadComplete()
        async with global_lock:
            GLOBAL_GID.remove(self._id)

    async def __download(self, message, path):
        try:
            if self._client is None and self._decrypter is not None:
                try:
                    async with Client(str(self._listener.userId), session_string=self._decrypter.decrypt(self._listener.user_dict.get('usess')).decode(), 
                                    in_memory=True, no_updates=True) as self._client:
                        download = await self._client.download_media(message=message, file_name=path, progress=self.__onDownloadProgress)
                except Exception as e:
                    if not self._listener.isCancelled:
                        await self.__onDownloadError(f'ERROR: {e}')
                        return
            else:
                download = await self._client.download_media(message=message, file_name=path, progress=self.__onDownloadProgress)
            if self._listener.isCancelled:
                await self.__onDownloadError('Cancelled by user!')
                return
        except FloodWait as f:
            LOGGER.warning(str(f))
            await sleep(f.value)
        except Exception as e:
            LOGGER.error(str(e))
            await self.__onDownloadError(str(e))
            return
        if download is not None:
            await self.__onDownloadComplete()
        elif not self.__is_cancelled:
            await self.__onDownloadError('Internal Error occurred')

    async def add_download(self, message, path, filename, session, decrypter):
        if session == 'user':
            self._client = user
            if not self._listener.isSuperChat:
                await sendMessage(message, 'Use SuperGroup to download this Link with User!')
                return
        elif session == 'user_sess':
            self._client = None
            self._decrypter = decrypter

        media = getattr(message, message.media.value) if message.media else None
        
        if media is not None:
            async with global_lock:
                download = media.file_unique_id not in GLOBAL_GID

            if download:
                if self._listener.name == "":
                    self._listener.name = media.file_name if hasattr(media, 'file_name') else 'None'
                else:
                    path = path + self._listener.name
                size = media.file_size
                gid = media.file_unique_id

                msg, button = await stop_duplicate_check(self._listener)
                if msg:
                    await self._listener.onDownloadError(msg, button)
                    await delete_links(self._listener.message)
                    return
                if limit_exceeded := await limit_checker(size, self._listener):
                    await self._listener.onDownloadError(limit_exceeded)
                    await delete_links(self._listener.message)
                    return

                add_to_queue, event = await check_running_tasks(self._listener)
                if add_to_queue:
                    LOGGER.info(f"Added to Queue/Download: {self._listener.name}")
                    async with task_dict_lock:
                        task_dict[self._listener.mid] = QueueStatus(
                            self._listener, gid, "dl"
                        )
                    await self._listener.onDownloadStart()
                    if self._listener.multi <= 1:
                        await sendStatusMessage(self._listener.message)
                    await event.wait()
                    if self._listener.isCancelled:
                        return
                    async with queue_dict_lock:
                        non_queued_dl.add(self._listener.mid)

                await self._onDownloadStart(gid, add_to_queue)
                await self._download(message, path)
            else:
                await self._onDownloadError('File already being downloaded!')
        else:
            await self._onDownloadError('No valid media type in the replied message')

    async def cancel_task(self):
        self._listener.isCancelled = True
        LOGGER.info(f'Cancelling download via User: [ Name: {self._listener.name} ID: {self._id} ]')
