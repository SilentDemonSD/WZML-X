#!/usr/bin/env python3
from time import time
from typing import Optional

from bot import LOGGER
from bot.helper.ext_utils.bot_utils import EngineStatus
from bot.helper.ext_utils.fs_utils import get_path_size
from bot.helper.ext_utils.human_readable import get_readable_file_size, get_readable_time
from bot.helper.ext_utils.async_utils import async_to_sync

class ZipStatus:
    def __init__(
        self,
        name: str,
        size: int,
        gid: int,
        listener,
        uid: int,
    ):
        """
        Initialize the ZipStatus class.

        :param name: Name of the file/directory being archived.
        :param size: Size of the file/directory being archived.
        :param gid: Group ID of the file/directory being archived.
        :param listener: Listener object containing information about the
        current archiving process.
        :param uid: User ID of the file/directory being archived.
        """
        self.__name = name
        self.__size = size
        self.__gid = gid
        self.__listener = listener
        self.__uid = uid
        self.__start_time = time()
        self.message = listener.message

    @property
    def gid(self) -> int:
        """
        Get the group ID of the file/directory being archived.

        :return: Group ID of the file/directory being archived.
        """
        return self.__gid

    def speed_raw(self) -> float:
        """
        Calculate the speed of the archiving process in bytes per second.

        :return: Speed of the archiving process in bytes per second.
        """
        try:
            return self.processed_raw() / (time() - self.__start_time)
        except ZeroDivisionError:
            return 0

    def progress_raw(self) -> float:
        """
        Calculate the progress of the archiving process as a percentage.

        :return: Progress of the archiving process as a percentage.
        """
        try:
            return self.processed_raw() / self.__size * 100
        except ZeroDivisionError:
            return 0

    @property
    def progress(self) -> str:
        """
        Get the progress of the archiving process as a formatted string.

        :return: Progress of the archiving process as a formatted string.
        """
        return f'{round(self.progress_raw(), 2)}%'

    @property
    def speed(self) -> str:
        """
        Get the speed of the archiving process as a formatted string.

        :return: Speed of the archiving process as a formatted string.
        """
        return f'{get_readable_file_size(self.speed_raw())}/s'

    @property
    def name(self) -> str:
        """
        Get the name of the file/directory being archived.

        :return: Name of the file/directory being archived.
        """
        return self.__name

    @property
    def size(self) -> str:
        """
        Get the size of the file/directory being archived as a formatted string.

        :return: Size of the file/directory being archived as a formatted string.
        """
        return get_readable_file_size(self.__size)

    def eta(self) -> str:
        """
        Calculate the estimated time of arrival of the archiving process.

        :return: Estimated time of arrival of the archiving process as a
        formatted string.
        """
        try:
            seconds = (self.__size - self.processed_raw()) / self.speed_raw()
            return get_readable_time(seconds)
        except ZeroDivisionError:
            return '-'

    @property
    def status(self) -> str:
        """
        Get the status of the archiving process.

        :return: Status of the archiving process.
        """
        return MirrorStatus.STATUS_ARCHIVING

    def processed_raw(self) -> int:
        """
        Calculate the size of the processed data in the archiving process.

        :return: Size of the processed data in the archiving process.
        """
        if self.__listener.new_dir:
            return async_to_sync(get_path_size, self.__listener.new_dir)
        else:
            return async_to_sync(get_path_size, self.__listener.dir) - self.__size

    @property
    def processed_bytes(self) -> str:
        """
        Get the size of the processed data in the archiving process as a
        formatted string.

        :return: Size of the processed data in the archiving process as a
        formatted string.
        """
        return get_readable_file_size(self.processed_raw())

    def download(self) -> 'ZipStatus':
        """
        Return the ZipStatus object itself.

        :return: ZipStatus object.
        """
        return self

    async def cancel_download(self):
        """
        Cancel the archiving process.
        """
        LOGGER.info(f'Cancelling Archive: {self.__name}')
        if self.__listener.suproc is not None:
            self.__listener.suproc.kill()
        else:
            self.__listener.suproc = 'cancelled'
        await self.__listener.on_upload_error('archiving stopped by user!')

    @property
    def eng(self) -> EngineStatus:
        """
        Get the engine status of the archiving process.

        :return: Engine status of the archiving process.
        """
        return EngineStatus().STATUS_ZIP
