#!/usr/bin/env python3
from logging import getLogger, ERROR
from time import time
from asyncio import Lock
from pyrogram import Client

from bot import LOGGER, download_dict, download_dict_lock, non_queued_dl, queue_dict_lock, bot, user, IS_PREMIUM_USER
from bot.helper.mirror_utils.status_utils.telegram_status import TelegramStatus
from bot.helper.mirror_utils.status_utils.queue_status import QueueStatus
from bot.helper.telegram_helper.message_utils import sendStatusMessage, sendMessage, delete_links
from bot.helper.ext_utils.task_manager import is_queued, limit_checker, stop_duplicate_check

global_lock = Lock()
GLOBAL_GID = set()
getLogger("pyrogram").setLevel(ERROR)


class TelegramDownloadHelper:

    def __init__(self, listener):
        self.name = ""
        self.__processed_bytes = 0
        self.__start_time = time()
        self.__listener = listener
        self.__client = bot
        self.__decrypter = None
        self.__id = ""
        self.__is_cancelled = False

    @property
    def speed(self):
        return self.__processed_bytes / (time() - self.__start_time)

    @property
    def processed_bytes(self):
        return self.__processed_bytes

    async def __onDownloadStart(self, name, size, file_id, from_queue):
        async with global_lock:
            GLOBAL_GID.add(file_id)
        self.name = name
        self.__id = file_id
        async with download_dict_lock:
            download_dict[self.__listener.uid] = TelegramStatus(
                self, size, self.__listener.message, file_id[:12], 'dl', self.__listener.upload_details)
        async with queue_dict_lock:
            non_queued_dl.add(self.__listener.uid)
        if not from_queue:
            await self.__listener.onDownloadStart()
            await sendStatusMessage(self.__listener.message)
            LOGGER.info(f'Download from Telegram: {name}')
        else:
            LOGGER.info(f'Start Queued Download from Telegram: {name}')

    async def __onDownloadProgress(self, current, total):
        if self.__is_cancelled:
            self.__client.stop_transmission()
        self.__processed_bytes = current

    async def __onDownloadError(self, error):
        async with global_lock:
            try:
                GLOBAL_GID.remove(self.__id)
            except Exception:
                pass
        await self.__listener.onDownloadError(error)

    async def __onDownloadComplete(self):
        await self.__listener.onDownloadComplete()
        async with global_lock:
            GLOBAL_GID.remove(self.__id)

    async def __download(self, message, path):
        try:
            if self.__client is None and self.__decrypter is not None:
                try:
                    async with Client(str(self.__listener.user_id), session_string=self.__decrypter.decrypt(self.__listener.user_dict.get('usess')).decode(), 
                                    in_memory=True, no_updates=True) as self.__client:
                        download = await self.__client.download_media(message=message, file_name=path, progress=self.__onDownloadProgress)
                except Exception as e:
                    if not self.__is_cancelled:
                        await self.__onDownloadError(f'ERROR: {e}')
                        return
            else:
                download = await self.__client.download_media(message=message, file_name=path, progress=self.__onDownloadProgress)
            if self.__is_cancelled:
                await self.__onDownloadError('Cancelled by user!')
                return
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
            self.__client = user
            if not self.__listener.isSuperGroup:
                await sendMessage(message, 'Use SuperGroup to download this Link with User!')
                return
        elif session == 'user_sess':
            self.__client = None
            self.__decrypter = decrypter

        media = getattr(message, message.media.value) if message.media else None
        
        if media is not None:
            async with global_lock:
                download = media.file_unique_id not in GLOBAL_GID

            if download:
                if filename == "":
                    name = media.file_name if hasattr(media, 'file_name') else 'None'
                else:
                    name = filename
                    path = path + name
                size = media.file_size
                gid = media.file_unique_id

                msg, button = await stop_duplicate_check(name, self.__listener)
                if msg:
                    await sendMessage(self.__listener.message, msg, button)
                    await delete_links(self.__listener.message)
                    return
                if limit_exceeded := await limit_checker(size, self.__listener):
                    await sendMessage(self.__listener.message, limit_exceeded)
                    await delete_links(self.__listener.message)
                    return
                added_to_queue, event = await is_queued(self.__listener.uid)
                if added_to_queue:
                    LOGGER.info(f"Added to Queue/Download: {name}")
                    async with download_dict_lock:
                        download_dict[self.__listener.uid] = QueueStatus(name, size, gid, self.__listener, 'dl')
                    await self.__listener.onDownloadStart()
                    await sendStatusMessage(self.__listener.message)
                    await event.wait()
                    async with download_dict_lock:
                        if self.__listener.uid not in download_dict:
                            return
                    from_queue = True
                else:
                    from_queue = False
                await self.__onDownloadStart(name, size, gid, from_queue)
                await self.__download(message, path)
            else:
                await self.__onDownloadError('File already being downloaded!')
        else:
            await self.__onDownloadError('No valid media type in the replied message')

    async def cancel_download(self):
        self.__is_cancelled = True
        LOGGER.info(f'Cancelling download via User: [ Name: {self.name} ID: {self.__id} ]')
