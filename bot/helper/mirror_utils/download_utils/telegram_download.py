#!/usr/bin/env python3
from typing import Any, Callable, Coroutine, Dict, Lock, Optional, Set, Union

import asyncio
import logging
import time
from pyrogram import Client

# Importing helper modules and classes
# ...

# Creating a global lock to prevent concurrent access to shared resources
global_lock: Lock = Lock()
# Creating a global set to store the unique IDs of the files being downloaded
GLOBAL_GID: Set[str] = set()
# Setting the log level for the 'pyrogram' logger to ERROR
logging.getLogger("pyrogram").setLevel(logging.ERROR)


class TelegramDownloadHelper:
    """
    A helper class to handle downloads from Telegram.
    """

    __slots__ = (
        'name',
        '__processed_bytes',
        '__start_time',
        '__listener',
        '__client',
        '__decrypter',
        '__id',
        '__is_cancelled'
    )

    def __init__(self, listener: 'Listener'):
        """
        Initializes the TelegramDownloadHelper class with a 'listener' object.

        :param listener: The listener object that will receive download events.
        """
        self.name: str = ''
        self.__processed_bytes: int = 0
        self.__start_time: float = time.time()
        self.__listener: 'Listener' = listener
        self.__client: Optional[Client] = None
        self.__decrypter: Optional[Any] = None
        self.__id: str = ''
        self.__is_cancelled: bool = False

    @property
    def speed(self) -> float:
        """
        A property decorator to calculate the download speed in bytes/second.

        :return: The download speed in bytes/second.
        """
        return self.__processed_bytes / (time.time() - self.__start_time)

    @property
    def processed_bytes(self) -> int:
        """
        A property decorator to get the total number of processed bytes.

        :return: The total number of processed bytes.
        """
        return self.__processed_bytes

    async def __onDownloadStart(self, name: str, size: int, file_id: str, from_queue: bool):
        """
        A private method to handle the start of a download.

        :param name: The name of the file being downloaded.
        :param size: The size of the file being downloaded.
        :param file_id: The unique ID of the file being downloaded.
        :param from_queue: Whether the download is from the queue or not.
        """
        async with global_lock:
            try:
                if file_id in GLOBAL_GID:
                    return
                GLOBAL_GID.add(file_id)
            except Exception:
                pass

        self.name = name
        self.__id = file_id

        async with download_dict_lock:
            try:
                if self.__listener.uid in download_dict:
                    return
                download_dict[self.__listener.uid] = TelegramStatus(
                    self, size, self.__listener.message, file_id[:12], 'dl', self.__listener.upload_details)
            except Exception:
                pass

        async with queue_dict_lock:
            try:
                if self.__listener.uid in non_queued_dl:
                    return
                non_queued_dl.add(self.__listener.uid)
            except Exception:
                pass

        if not from_queue:
            try:
                await self.__listener.onDownloadStart()
                await sendStatusMessage(self.__listener.message)
                logging.info(f'Download from Telegram: {name}')
            except Exception:
                pass
        else:
            logging.info(f'Start Queued Download from Telegram: {name}')

    async def __onDownloadProgress(self, current: int, total: int):
        """
        A private method to handle the progress of a download.

        :param current: The current number of processed bytes.
        :param total: The total number of bytes to be processed.
        """
        if self.__is_cancelled:
            if self.__client:
                try:
                    self.__client.stop_transmission()
                except Exception:
                    pass
            return

        self.__processed_bytes = current

    async def __onDownloadError(self, error: str):
        """
        A private method to handle the errors during a download.

        :param error: The error message.
        """
        async with global_lock:
            try:
                GLOBAL_GID.remove(self.__id)
            except Exception:
                pass

        try:
            await self.__listener.onDownloadError(error)
        except Exception:
            pass

    async def __onDownloadComplete(self):
        """
        A private method to handle the completion of a download.
        """
        try:
            await self.__listener.onDownloadComplete()
        except Exception:
            pass

        async with global_lock:
            try:
                GLOBAL_GID.remove(self.__id)
            except Exception:
                pass

    async def __download(self, message, path):
        """
        A private method to download the media from the message.

        :param message: The message object containing the media to be downloaded.
        :param path: The path to download the media to.
        """
        try:
            if self.__client is None and self.__decrypter is not None:
                try:
                    async with Client(str(self.__listener.user_id), session_string=self.__decrypter.decrypt(self.__listener.user_dict.get('usess')).decode(), 
                                      in_memory=True, no_updates=True) as self.__client:
                        if self.__client is None:
                            return

                        download = await self.__client.download_media(message=message, file_name=path, progress=self.__onDownloadProgress)
                except Exception as e:
                    if not self.__is_cancelled:
                        await self.__onDownloadError(f'ERROR: {e}')
                        return
            else:
                if self.__client is None:
                    return

                download = await self.__client.download_media(message=message, file_name=path, progress=self.__onDownloadProgress)

            if self.__is_cancelled:
                try:
                    self.__client.stop_transmission()
                except Exception:
                    pass
                await self.__onDownloadError('Cancelled by user!')
                return
        except Exception as e:
            logging.error(str(e))
            await self.__onDownloadError(str(e))
            return

        if download is not None:
            await self.__onDownloadComplete()
        elif not self.__is_cancelled:
            await self.__onDownloadError('Internal Error occurred')
