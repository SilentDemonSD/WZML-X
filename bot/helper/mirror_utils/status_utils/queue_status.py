#!/usr/bin/env python3

import bot.helper.ext_utils.bot_utils as bot_utils  # Importing the bot_utils module
from bot import LOGGER  # Importing the logger from bot module


class QueueStatus:
    def __init__(self, name, size, gid, listener, status):
        # Initialize the QueueStatus class with the following parameters:
        # name: The name of the queue
        # size: The size of the queue
        # gid: The group id of the queue
        # listener: The listener object associated with the queue
        # status: The status of the queue ('dl' for download, 'up' for upload)

        self.__name = name
        self.__size = size
        self.__gid = gid
        self.__listener = listener
        self.upload_details = listener.upload_details
        self.__status = status
        self.message = listener.message

    def gid(self):
        # Return the group id of the queue
        return self.__gid

    def name(self):
        # Return the name of the queue
        return self.__name

    def size(self):
        # Return the size of the queue in a readable format
        return get_readable_file_size(self.__size)

    def status(self):
        # Return the status of the queue
        if self.__status == 'dl':
            return MirrorStatus.STATUS_QUEUEDL  # If the status is 'dl', return the corresponding MirrorStatus constant
        return MirrorStatus.STATUS_QUEUEUP  # Otherwise, return the corresponding MirrorStatus constant

    def processed_bytes(self):
        # Always return 0 for processed bytes
        return 0

    def progress(self):
        # Always return '0%' for progress
        return '0%'

    def speed(self):
        # Always return '0B/s' for speed
        return '0B/s'

    def eta(self):
        # Always return '-' for ETA
        return '-'

    def download(self):
        # Return the download object associated with the queue
        return self

    async def cancel_download(self):
        # Cancel the download or upload associated with the queue
        LOGGER.info(f'Cancelling Queue{self.__status}: {self.__name}')
        if self.__status == 'dl':
            await self.__listener.onDownloadError('task have been removed from queue/download')
        else:
            await self.__listener.onUploadError('task have been removed from queue/upload')

    def eng(self):
        # Return the EngineStatus constant for queue
        return EngineStatus().STATUS_QUEUE
