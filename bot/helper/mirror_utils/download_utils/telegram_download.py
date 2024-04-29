#!/usr/bin/env python3
from typing import Any, Callable, Coroutine, Dict, Optional, Set, Union

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
        # Initializing the TelegramDownloadHelper class with a 'listener' object
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
        # A property decorator to calculate the download speed in bytes/second
        return self.__processed_bytes / (time.time() - self.__start_time)

    @property
    def processed_bytes(self) -> int:
        # A property decorator to get the total number of processed bytes
        return self.__processed_bytes

    async def __onDownloadStart(self, name: str, size: int, file_id: str, from_queue: bool):
        # A private method to handle the start of a download
        async with global_lock:
            # Acquiring the global lock to prevent concurrent access to shared resources
            GLOBAL_GID.add(file_id)
        self.name = name
        self.__id = file_id
        async with download_dict_lock:
            # Acquiring the download_dict lock to prevent concurrent access to the download_dict dictionary
            download_dict[self.__listener.uid] = TelegramStatus(
                self, size, self.__listener.message, file_id[:12], 'dl', self.__listener.upload_details)
        async with queue_dict_lock:
            # Acquiring the queue_dict lock to prevent concurrent access to the queue_dict dictionary
            non_queued_dl.add(self.__listener.uid)
        if not from_queue:
            # If the download is not from the queue, calling the 'onDownloadStart' method of the listener object
            await self.__listener.onDownloadStart()
            # Sending a status message to the user
            await sendStatusMessage(self.__listener.message)
            logging.info(f'Download from Telegram: {name}')
        else:
            logging.info(f'Start Queued Download from Telegram: {name}')

    async def __onDownloadProgress(self, current: int, total: int):
        # A private method to handle the progress of a download
        if self.__is_cancelled:
            # If the download is cancelled, stopping the transmission
            if self.__client:
                self.__client.stop_transmission()
        self.__processed_bytes = current

    async def __onDownloadError(self, error: str):
        # A private method to handle the errors during a download
        async with global_lock:
            try:
                GLOBAL_GID.remove(self.__id)
            except Exception:
                pass
        # Calling the 'onDownloadError' method of the listener object with the error message
        if self.__listener:
            await self.__listener.onDownloadError(error)

    async def __onDownloadComplete(self):
        # A private method to handle the completion of a download
        if self.__listener:
            await self.__listener.onDownloadComplete()
        async with global_lock:
            GLOBAL_GID.remove(self.__id)

    async def __download(self, message, path):
        # A private method to download the media from the message
        try:
            if self.__client is None and self.__decrypter is not None:
                # If the client is None and decrypter is not None, creating a new client with the decrypted session string
                try:
                    async with Client(str(self.__listener.user_id), session_string=self.__decrypter.decrypt(self.__listener.user_dict.get('usess')).decode(), 
                                      in_memory=True, no_updates=True) as self.__client:
                        download = await self.__client.download_media(message=message, file_name=path, progress=self.__onDownloadProgress)
                except Exception as e:
                    if not self.__is_cancelled:
                        # If the download is not cancelled, calling the 'onDownloadError' method with the error message
                        await self.__onDownloadError(f'ERROR: {e}')
                        return
            else:
                # If the client is not None, downloading the media using the client
                download = await self.__client.download_media(message=message, file_name=path, progress=self.__onDownloadProgress)
            if self.__is_cancelled:
                # If the download is cancelled, calling the 'onDownloadError' method with the error message
                await self.__onDownloadError('Cancelled by user!')
                return
        except Exception as e:
            logging.error(str(e))
            # If an error occurs during the download, calling the 'onDownloadError' method with the error message
            await self.__onDownloadError(str(e))
            return
        if download is not None:
            # If the download is successful, calling the 'onDownloadComplete' method
            await self.__onDownloadComplete()
        elif not self.__is_cancelled:
            # If the download is not cancelled, calling the 'onDownloadError' method with the error message
            await self.__onDownloadError('Internal Error occurred')


