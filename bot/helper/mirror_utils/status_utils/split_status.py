#!/usr/bin/env python3
from bot import LOGGER
from bot.helper.ext_utils.bot_utils import EngineStatus, get_readable_file_size, MirrorStatus

class SplitStatus:
    """
    Class representing the status of a file split operation.
    """

    def __init__(
        self,
        name: str,
        size: int,
        gid: int,
        listener,
    ):
        """
        Initialize a new SplitStatus object.

        :param name: The name of the file being split.
        :param size: The size of the file in bytes.
        :param gid: The group ID associated with the file.
        :param listener: The listener object associated with the file.
        """
        self.__name = name
        self.__gid = gid
        self.__size = size
        self.__listener = listener
        self.upload_details = listener.upload_details
        self.message = listener.message

    @property
    def gid(self) -> int:
        """
        Get the group ID associated with the file.

        :return: The group ID.
        """
        return self.__gid

    def progress(self) -> str:
        """
        Get the progress of the file split operation.

        :return: The progress as a string.
        """
        return '0'

    def speed(self) -> str:
        """
        Get the speed of the file split operation.

        :return: The speed as a string.
        """
        return '0'

    def name(self) -> str:
        """
        Get the name of the file being split.

        :return: The name of the file.
        """
        return self.__name

    def size(self) -> str:
        """
        Get the size of the file being split.

        :return: The size of the file as a human-readable string.
        """
        return get_readable_file_size(self.__size)

    def eta(self) -> str:
        """
        Get the estimated time of arrival of the file split operation.

        :return: The ETA as a string.
        """
        return '0s'

    def status(self) -> MirrorStatus:
        """
        Get the status of the file split operation.

        :return: The status as a MirrorStatus object.
        """
        return MirrorStatus.STATUS_SPLITTING

    def processed_bytes(self) -> int:
        """
        Get the number of bytes processed by the file split operation.

        :return: The number of processed bytes.
        """
        return 0

    def download(self) -> 'SplitStatus':
        """
        Get the file split operation object.

        :return: The file split operation object.
        """
        return self

    async def cancel_download(self):
        """
        Cancel the file split operation.
        """
        LOGGER.info(f'Cancelling Split: {self.__name}')
        if self.__listener.suproc is not None:
            self.__listener.suproc.kill()
        else:
            self.__listener.suproc = 'cancelled'
        await self.__listener.onUploadError('splitting stopped by user!')

    def eng(self) -> EngineStatus:
        """
        Get the engine status of the file split operation.

        :return: The engine status as an EngineStatus object.
        """
        return EngineStatus().STATUS_SPLIT_MERGE

    def __str__(self):
        """
        Get a human-readable representation of the object.

        :return: A string representation of the object.
        """
        return (
            f'SplitStatus('
            f'name={self.__name}, '
            f'size={self.__size}, '
            f'gid={self.__gid}, '
            f'listener={self.__listener})'
        )
