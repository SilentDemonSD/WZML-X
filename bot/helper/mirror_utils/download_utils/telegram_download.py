import asyncio
import time
from typing import Any
from logging import getLogger

import pyrogram
from pyrogram import Client as PyrogramClient
from pyrogram.errors import DownloadFailed

from bot import LOGGER, download_dict, download_dict_lock, non_queued_dl, queue_dict_lock, bot, user, IS_PREMIUM_USER
from bot.helper.mirror_utils.status_utils.telegram_status import TelegramStatus
from bot.helper.mirror_utils.status_utils.queue_status import QueueStatus
from bot.helper.telegram_helper.message_utils import send_status_message, send_message, delete_links
from bot.helper.ext_utils.task_manager import is_queued, limit_checker, stop_duplicate_check

global_lock = asyncio.Lock()
GLOBAL_GID: set[str] = set()
getLogger("pyrogram").setLevel(pyrogram.logging.ERROR)


class TelegramDownloadHelper:
    def __init__(self, listener):
        self.name: str = ""
        self.__processed_bytes: int = 0
        self.__start_time: float = time.time()
        self.__listener = listener
        self.__client: PyrogramClient | None = bot
        self.__decrypter: Any | None = None
        self.__id: str = ""
        self.__is_cancelled: bool = False

    @property
    def speed(self) -> float:
        return self.__processed_bytes / (time.time() - self.__start_time)

    @property
    def processed_bytes(self) -> int:
        return self.__processed_bytes

    async def __on_download_start(self, name: str, size: int, file_id: str, from_queue: bool):
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
            await self.__listener.on_download_start()
            await send_status_message(self.__listener.message)
            LOGGER.info(f'Download from Telegram: {name}')
        else:
            LOGGER.info(f'Start Queued Download from Telegram: {name}')

    async def __on_download_progress(self, current: int, total: int):
        if self.__is_cancelled:
            self.__client.stop_transmission()
        self.__processed_bytes = current

    async def __on_download_error(self, error: Exception):
        async with global_lock:
            try:
                GLOBAL_GID.remove(self.__id)
            except KeyError:
                pass
        await self.__listener.on_download_error(error)

    async def __on_download_complete(self):
        await self.__listener.on_download_complete()
        async with global_lock:
            GLOBAL_GID.remove(self.__id)

    async def __download(self, message, path):
        try:
            if self.__client is None and self.__decrypter is not None:
                try:
                    async with PyrogramClient(
                            str(self.__listener.user_id),
                            session_string=self.__decrypter.decrypt(self.__listener.user_dict.get('usess')).decode(),
                            in_memory=True, no_updates=True) as self.__client:
                        download = await self.__client.download_media(
                            message=message,
                            file_name=path,
                            progress=self.__on_download_progress)
                except Exception as e:
                    if not self.__is_cancelled:
                        await self.__on_download_error(e)
                        return
            else:
                download = await self.__client.download_media(
                    message=message,
                    file_name=path,
                    progress=self.__on_download_progress)
            if self.__is_cancelled:
                await self.__on_download_error('Cancelled by user!')
                return
        except Exception as e:
            LOGGER.error(str(e))
            await self.__on_download_error(e)
            return
        if download is not None:
            await self.__on_download_complete()
        elif not self.__is_cancelled:
            await self.__on_download_error('Internal Error occurred')

    async def add_download(self,
                           message,
                           path: str,
                           filename: str,
                           session: str,
                           decrypter: Any = None):
        if session == 'user':
            self.__client = user
            if not self.__listener.is_supergroup:
                await send_message(message, 'Use SuperGroup to download this Link with User!')
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
                    await send_message(self.__listener.message, msg, button)
                    await delete_links(self.__listener.message)
                    return
                if limit_exceeded := await limit_checker(size, self.__listener):
                    await send_message(self.__listener.message, limit_exceeded)
                    await delete_links(self.__listener.message)
                    return
                added_to_queue, event = await is_queued(self.__listener.uid)
                if added_to_queue:
                    LOGGER.info(f"Added to Queue/Download: {name}")
                    async with download_dict_lock:
                        download_dict[self.__listener.uid] = QueueStatus(name, size, gid, self.__listener, 'dl')
                    await self.__listener.on_download_start()
                    await send_status_message(self.__listener.message)
                    await event.wait()
                    async with download_dict_lock:
                        if self.__listener.uid not in download_dict:
                            return
                    from_queue = True
                else:
                    from_queue = False
                await self.__on_download_start(name, size, gid, from_queue)
                try:
                    await self.__download(message, path)
                except DownloadFailed as e:
                    await self.__on_download_error(e)
            else:
                await self.__on_download_error('File already being downloaded!')
        else:
            await self.__on_download_error('No valid media type in the replied message')

    async def cancel_download(self):
        self.__is_cancelled = True
        LOGGER.info(f'Cancelling download via User: [ Name: {self.name} ID: {self.__id} ]')
