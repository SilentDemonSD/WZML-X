#!/usr/bin/env python3
from typing import Any, Callable, Coroutine, Dict, Set, Union
from logging import getLogger, ERROR
from time import time
from asyncio import Lock

from bot import LOGGER, download_dict, download_dict_lock, non_queued_dl, queue_dict_lock, bot, user, IS_PREMIUM_USER
from bot.helper.mirror_utils.status_utils.telegram_status import TelegramStatus
from bot.helper.mirror_utils.status_utils.queue_status import QueueStatus
from bot.helper.telegram_helper.message_utils import sendStatusMessage, sendMessage, delete_links
from bot.helper.ext_utils.task_manager import is_queued, limit_checker, stop_duplicate_check

global_lock = Lock()
GLOBAL_GID: Set[str] = set()
getLogger("pyrogram").setLevel(ERROR)


class TelegramDownloadHelper:
    """
    Helper class for downloading files from Telegram.
    """

    def __init__(self, listener: Any):
        """
        Initialize the helper with a listener object.

        :param listener: The listener object.
        """
        self.name = ""
        self.__processed_bytes = 0
        self.__start_time = time()
        self.__listener = listener
        self.__id = ""
        self.__is_cancelled = False

    @property
    def speed(self) -> float:
        """
        Get the download speed in bytes per second.

        :return: The download speed.
        """
        return self.__processed_bytes / (time() - self.__start_time)

    @property
    def processed_bytes(self) -> int:
        """
        Get the number of processed bytes.

        :return: The number of processed bytes.
        """
        return self.__processed_bytes

    async def __onDownloadStart(self, name: str, size: int, file_id: str, from_queue: bool):
        """
        Callback for when the download starts.

        :param name: The name of the file.
        :param size: The size of the file.
        :param file_id: The unique id of the file.
        :param from_queue: Whether the download is from the queue.
        """
        async with global_lock:
            GLOBAL_GID.add(file_id)
        self.name = name
        self.__id = file_id
        async with download_dict_lock:
            if self.__listener.uid in download_dict:
                del download_dict[self.__listener.uid]
            download_dict[self.__listener.uid] = TelegramStatus(
                self, size, self.__listener.message, file_id[:12], 'dl', self.__listener.upload_details)
        async with queue_dict_lock:
            if self.__listener.uid not in non_queued_dl:
                non_queued_dl.add(self.__listener.uid)
        if not from_queue:
            await self.__listener.onDownloadStart()
            await sendStatusMessage(self.__listener.message)
            LOGGER.info(f'Download from Telegram: {name}')
        else:
            LOGGER.info(f'Start Queued Download from Telegram: {name}')

    async def __onDownloadProgress(self, current: int, total: int):
        """
        Callback for when the download progress changes.

        :param current: The current number of processed bytes.
        :param total: The total number of bytes to be processed.
        """
        if self.__is_cancelled:
            if IS_PREMIUM_USER:
                user.stop_transmission()
            else:
                bot.stop_transmission()
        self.__processed_bytes = current

    async def __onDownloadError(self, error: Union[Exception, str]):
        """
        Callback for when the download encounters an error.

        :param error: The error object or message.
        """
        async with global_lock:
            try:
                GLOBAL_GID.remove(self.__id)
            except:
                pass
        await self.__listener.onDownloadError(error)

    async def __onDownloadComplete(self):
        """
        Callback for when the download completes.
        """
        await self.__listener.onDownloadComplete()
        async with global_lock:
            GLOBAL_GID.remove(self.__id)

    async def __download(self, message, path):
        """
        Download the file.

        :param message: The message object containing the file.
        :param path: The path to save the file.
        :return: Whether the download was successful.
        """
        try:
            download = await message.download(file_name=path, progress=self.__onDownloadProgress)
            if self.__is_cancelled:
                await self.__onDownloadError('Cancelled by user!')
                return False
        except Exception as e:
            LOGGER.error(str(e))
            await self.__onDownloadError(str(e))
            return False
        if download is not None:
            await self.__onDownloadComplete()
            return True
        elif not self.__is_cancelled:
            await self.__onDownloadError('Internal Error occurred')
        return False

    async def add_download(self, message, path, filename, session):
        """
        Add a download to the queue.

        :param message: The message object containing the file.
        :param path: The path to save the file.
        :param filename: The name of the file.
        :param session: The session type.
        :return: Whether the download was added to the queue.
        """
        if session == 'user':
            if not self.__listener.isSuperGroup:
                await sendMessage(message, 'Use SuperGroup to download this Link with User!')
                return False
            message = await user.get_messages(chat_id=message.chat.id, message_ids=message.id)

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
                    return False
                if limit_exceeded := await limit_checker(size, self.__listener):
                    await sendMessage(self.__listener.message, limit_exceeded)
                    await delete_links(self.__listener.message)
                    return False
                added_to_queue, event = await is_queued(self.__listener.uid)
                if added_to_queue:
                    LOGGER.info(f"Added to Queue/Download: {name}")
                    async with download_dict_lock:
                        download_dict[self.__listener.uid] = QueueStatus(
                            name, size, gid, self.__listener, 'dl')
                    await self.__listener.onDownloadStart()
                    await sendStatusMessage(self.__listener.message)
                    await event.wait()
                    async with download_dict_lock:
                        if self.__listener.uid not in download_dict:
                            return False
                    from_queue = True
                else:
                    from_queue = False
                await self.__onDownloadStart(name, size, gid, from_queue)
                return await self.__download(message, path)
            else:
                await self.__onDownloadError('File already being downloaded!')
        else:
            await self.__onDownloadError('No valid media type in the replied message')
        return False

    async def cancel_download(self):
        """
        Cancel the current download.
        """
        self.__is_cancelled = True
        LOGGER.info(f'Cancelling download via User: [ Name: {self.name} ID: {self.__id} ]')
