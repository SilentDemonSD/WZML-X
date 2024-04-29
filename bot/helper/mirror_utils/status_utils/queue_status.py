#!/usr/bin/env python3
import asyncio
from bot import LOGGER
from bot.helper.ext_utils.bot_utils import EngineStatus, get_readable_file_size, MirrorStatus


class QueueStatus:
    def __init__(self, name: str, size: int, gid: int, listener, status: str):
        """
        Initialize QueueStatus object

        :param name: Name of the queue
        :param size: Size of the queue
        :param gid: Group id of the queue
        :param listener: Listener object
        :param status: Status of the queue
        """
        self.__name = name
        self.__size = size
        self.__gid = gid
        self.__listener = listener
        self.upload_details = listener.upload_details
        self.__status = status
        self.message = listener.message

    @property
    def gid(self) -> int:
        """
        Get group id of the queue

        :return: Group id of the queue
        """
        return self.__gid

    @property
    def name(self) -> str:
        """
        Get name of the queue

        :return: Name of the queue
        """
        return self.__name

    @property
    def size(self) -> str:
        """
        Get size of the queue in readable format

        :return: Readable size of the queue
        """
        return get_readable_file_size(self.__size)

    def status(self) -> MirrorStatus:
        """
        Get status of the queue

        :return: Status of the queue
        """
        return MirrorStatus.STATUS_QUEUE if self.__status == 'dl' else MirrorStatus.STATUS_QUEUEUP

    def processed_bytes(self) -> int:
        """
        Get processed bytes of the queue

        :return: Processed bytes of the queue
        """
        return 0

    def progress(self) -> str:
        """
        Get progress of the queue

        :return: Progress of the queue
        """
        return '0%'

    def speed(self) -> str:
        """
        Get speed of the queue

        :return: Speed of the queue
        """
        return '0B/s'

    def eta(self) -> str:
        """
        Get ETA of the queue

        :return: ETA of the queue
        """
        return '-'

    def download(self) -> 'QueueStatus':
        """
        Get download object of the queue

        :return: Download object of the queue
        """
        return self

    @asyncio.coroutine
    async def cancel_download(self):
        """
        Cancel download of the queue
        """
        LOGGER.info(f'Cancelling Queue{self.__status}: {self.__name}')
        if self.__status == 'dl':
            await self.__listener.onDownloadError('task have been removed from queue/download')
        else:
            await self.__listener.onUploadError('task have been removed from queue/upload')

    @property
    def eng(self) -> EngineStatus:
        """
        Get engine status of the queue

        :return: Engine status of the queue
        """
        return EngineStatus().STATUS_QUEUE
