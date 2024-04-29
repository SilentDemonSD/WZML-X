#!/usr/bin/env python3
from logging import getLogger, ERROR
from time import time
from asyncio import Lock
from pyrogram import Client

# Importing helper modules and classes
from bot import LOGGER, download_dict, download_dict_lock, non_queued_dl, queue_dict_lock, bot, user, IS_PREMIUM_USER
from bot.helper.mirror_utils.status_utils.telegram_status import TelegramStatus
from bot.helper.mirror_utils.status_utils.queue_status import QueueStatus
from bot.helper.telegram_helper.message_utils import sendStatusMessage, sendMessage, delete_links
from bot.helper.ext_utils.task_manager import is_queued, limit_checker, stop_duplicate_check

# Creating a global lock to prevent concurrent access to shared resources
global_lock = Lock()
# Creating a global set to store the unique IDs of the files being downloaded
GLOBAL_GID = set()
# Setting the log level for the 'pyrogram' logger to ERROR
getLogger("pyrogram").setLevel(ERROR)


class TelegramDownloadHelper:

    def __init__(self, listener):
        # Initializing the TelegramDownloadHelper class with a 'listener' object
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
        # A property decorator to calculate the download speed in bytes/second
        return self.__processed_bytes / (time() - self.__start_time)

    @property
    def processed_bytes(self):
        # A property decorator to get the total number of processed bytes
        return self.__processed_bytes

    async def __onDownloadStart(self, name, size, file_id, from_queue):
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
            LOGGER.info(f'Download from Telegram: {name}')
        else:
            LOGGER.info(f'Start Queued Download from Telegram: {name}')

    async def __onDownloadProgress(self, current, total):
        # A private method to handle the progress of a download
        if self.__is_cancelled:
            # If the download is cancelled, stopping the transmission
            self.__client.stop_transmission()
        self.__processed_bytes = current

    async def __onDownloadError(self, error):
        # A private method to handle the errors during a download
        async with global_lock:
            try:
                GLOBAL_GID.remove(self.__id)
            except Exception:
                pass
        # Calling the 'onDownloadError' method of the listener object with the error message
        await self.__listener.onDownloadError(error)

    async def __onDownloadComplete(self):
        # A private method to handle the completion of a download
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
            LOGGER.error(str(e))
            # If an error occurs during the download, calling the 'onDownloadError' method with the error message
            await self.__onDownloadError(str(e))
            return
        if download is not None:
            # If the download is successful, calling the 'onDownloadComplete' method
            await self.__onDownloadComplete()
        elif not self.__is_cancelled:
            # If the download is not cancelled, calling the 'onDownloadError' method with the error message
            await self.__onDownloadError('Internal Error occurred')

    async def add_download(self, message, path, filename, session, decrypter):
        # A public method to add a download to the queue
        if session == 'user':
            # If the session is 'user', setting the client to user and checking if the listener is in a supergroup
            self.__client = user
            if not self.__listener.isSuperGroup:
                # If the listener is not in a supergroup, sending a message to the user and returning
                await sendMessage(message, 'Use SuperGroup to download this Link with User!')
                return
        elif session == 'user_sess':
            # If the session is 'user_sess', setting the client to None and the decrypter to the given decrypter
            self.__client = None
            self.__decrypter = decrypter

        media = getattr(message, message.media.value) if message.media else None
        
        if media is not None:
            # If the message has media, acquiring the global lock to prevent concurrent access to shared resources
            async with global_lock:
                # Checking if the file is already being downloaded
                download = media.file_unique_id not in GLOBAL_GID

            if download:
                # If the file is not already being downloaded, getting the name, size, and unique ID of the media
                if filename == "":
                    name = media.file_name if hasattr(media, 'file_name') else 'None'
                else:
                    name = filename
                    path = path + name
                size = media.file_size
                gid = media.file_unique_id

                # Checking for duplicate messages and limit exceeded
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
                # If the download is already in the queue, sending a status message and waiting for the event
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
                # Calling the 'onDownloadStart' method with the name, size, unique ID, and from_queue parameters
                await self.__onDownloadStart(name, size, gid, from_queue)
                # Calling the 'download' method with the message and path parameters
                await self.__download(message, path)
            else:
                # If the file is already being downloaded, calling the 'onDownloadError' method with the error message
                await self.__onDownloadError('File already being downloaded!')
        else:
            # If the message does not have media, calling the 'onDownloadError' method with the error message
            await self.__onDownloadError('No valid media type in the replied message')

    async def cancel_download(self):
        # A public method to cancel the current download
        self.__is_cancelled = True
        LOGGER.info(f'Cancelling download via User: [ Name: {self.name} ID: {self.__id} ]')
