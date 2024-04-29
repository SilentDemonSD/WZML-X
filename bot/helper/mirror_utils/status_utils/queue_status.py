#!/usr/bin/env python3

import bot.helper.ext_utils.bot_utils as bot_utils  # Importing the bot_utils module
from bot import LOGGER  # Importing the logger from bot module

class QueueStatus:
    """
    Represents the status of a queue.

    Attributes:
        name (str): The name of the queue.
        gid (int): The group id of the queue.
        listener (object): The listener object associated with the queue.
        status (str): The status of the queue ('dl' for download, 'up' for upload).
        upload_details (dict): The upload details associated with the queue.
        message (object): The message object associated with the queue.
    """

    def __init__(self, name: str, gid: int, listener, status: str):
        self.__name = name
        self.__gid = gid
        self.__listener = listener
        self.upload_details = listener.upload_details
        self.__status = status
        self.message = listener.message
        self.total_size = sum(item.size for item in listener.queue)

    @property
    def name(self) -> str:
        """Return the name of the queue."""
        return self.__name

    @property
    def size(self) -> int:
        """Return the size of the queue."""
        return self.total_size

    @property
    def gid(self) -> int:
        """Return the group id of the queue."""
        return self.__gid

    @property
    def status(self) -> str:
        """Return the status of the queue."""
        return self.__status

    @property
    def processed_bytes(self) -> int:
        """Always return 0 for processed bytes."""
        return 0

    @property
    def progress(self) -> str:
        """Always return '0%' for progress."""
        return '0%'

    @property
    def speed(self) -> str:
        """Always return '0B/s' for speed."""
        return '0B/s'

    @property
    def eta(self) -> str:
        """Always return '-' for ETA."""
        return '-'

    def download(self) -> 'QueueStatus':
        """Return the download object associated with the queue."""
        return None

    async def cancel_download(self):
        """Cancel the download or upload associated with the queue."""
        LOGGER.info(f'Cancelling Queue {self.status}: {self.name}')
        if self.status == 'dl':
            raise CancellationError('The task has been removed from the queue/download')
        else:
            raise CancellationError('The task has been removed from the queue/upload')

    def eng(self) -> str:
        """Return the EngineStatus constant for queue."""
        return 'QUEUE'

    def __str__(self):
        """Return a human-readable representation of the QueueStatus object."""
        return (
            f'QueueName: {self.name}\n'
            f'QueueSize: {self.size}\n'
            f'QueueGroupId: {self.gid}\n'
            f'QueueStatus: {self.status}\n'
        )

    def __repr__(self):
        """Return a more informative representation of the QueueStatus object."""
        return (
            f'QueueStatus(name={self.name}, gid={self.gid}, status={self.status}, '
            f'total_size={self.total_size})'
        )

    @classmethod
    def get_readable_file_size(cls, size: int) -> str:
        """Return the size in a human-readable format."""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size < 1024:
                break
            size /= 1024.0
        return f'{size:.2f} {unit}'

class CancellationError(Exception):
    """Custom error for cancellation."""

    def __init__(self, message: str):
        super().__init__(message)
