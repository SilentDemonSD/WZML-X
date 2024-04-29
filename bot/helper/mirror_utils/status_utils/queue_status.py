#!/usr/bin/env python3

import bot.helper.ext_utils.bot_utils as bot_utils  # Importing the bot_utils module
from bot import LOGGER  # Importing the logger from bot module

class QueueStatus:
    """
    Represents the status of a queue.

    Attributes:
        name (str): The name of the queue.
        size (int): The size of the queue.
        gid (int): The group id of the queue.
        listener (object): The listener object associated with the queue.
        status (str): The status of the queue ('dl' for download, 'up' for upload).
    """

    def __init__(self, name: str, size: int, gid: int, listener, status: str):
        self.__name = name
        self.__size = size
        self.__gid = gid
        self.__listener = listener
        self.upload_details = listener.upload_details
        self.__status = status
        self.message = listener.message

    def gid(self) -> int:
        """Return the group id of the queue."""
        return self.__gid

    def name(self) -> str:
        """Return the name of the queue."""
        return self.__name

    def size(self) -> str:
        """Return the size of the queue in a readable format."""
        return get_readable_file_size(self.__size)

    def status(self) -> str:
        """Return the status of the queue."""
        return self.__status

    def processed_bytes(self) -> int:
        """Always return 0 for processed bytes."""
        return 0

    def progress(self) -> str:
        """Always return '0%' for progress."""
        return '0%'

    def speed(self) -> str:
        """Always return '0B/s' for speed."""
        return '0B/s'

    def eta(self) -> str:
        """Always return '-' for ETA."""
        return '-'

    def download(self) -> 'QueueStatus':
        """Return the download object associated with the queue."""
        return self

    async def cancel_download(self):
        """Cancel the download or upload associated with the queue."""
        LOGGER.info(f'Cancelling Queue{self.__status}: {self.__name}')
        if self.__status == 'dl':
            await self.__listener.onDownloadError('task have been removed from queue/download')
        else:
            await self.__listener.onUploadError('task have been removed from queue/upload')

    def eng(self) -> str:
        """Return the EngineStatus constant for queue."""
        return EngineStatus().STATUS_QUEUE

    def __str__(self):
        """Return a human-readable representation of the QueueStatus object."""
        return (
            f'QueueName: {self.__name}\n'
            f'QueueSize: {self.__size}\n'
            f'QueueGroupId: {self.__gid}\n'
            f'QueueStatus: {self.__status}\n'
        )
