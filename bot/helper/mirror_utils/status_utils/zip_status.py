#!/usr/bin/env python3
from time import time
from typing import Union

from bot import LOGGER
from bot.helper.ext_utils.bot_utils import EngineStatus, get_readable_file_size, MirrorStatus, get_readable_time, async_to_sync
from bot.helper.ext_utils.fs_utils import get_path_size

class ZipStatus:
    """
    Class to represent the status of a zip file.
    """
    def __init__(self, name: str, size: int, gid: int, listener):
        """
        Initialize the ZipStatus object.

        :param name: Name of the zip file.
        :param size: Size of the zip file.
        :param gid: Group id of the zip file.
        :param listener: Listener object to listen for events.
        """
        self.__name = name
        self.__size = size
        self.__gid = gid
        self.__listener = listener
        self.upload_details = listener.upload_details
        self.__uid = listener.uid
        self.__start_time = time()
        self.message = listener.message

    def gid(self) -> int:
        """
        Get the group id of the zip file.

        :return: Group id of the zip file.
        """
        return self.__gid

    def speed_raw(self) -> float:
        """
        Get the speed of the zip file in bytes per second.

        :return: Speed of the zip file in bytes per second.
        """
        return self.processed_raw() / (time() - self.__start_time)

    def progress_raw(self) -> float:
        """
        Get the progress of the zip file in percentage.

        :return: Progress of the zip file in percentage.
        """
        try:
            return self.processed_raw() / self.__size * 100
        except:
            return 0

    def progress(self) -> str:
        """
        Get the progress of the zip file in string format.

        :return: Progress of the zip file in string format.
        """
        return f'{round(self.progress_raw(), 2)}%'

    def speed(self) -> str:
        """
        Get the speed of the zip file in a human-readable format.

        :return: Speed of the zip file in a human-readable format.
        """
        return f'{get_readable_file_size(self.speed_raw())}/s'

    def name(self) -> str:
        """
        Get the name of the zip file.

        :return: Name of the zip file.
        """
        return self.__name

    def size(self) -> str:
        """
        Get the size of the zip file in a human-readable format.

        :return: Size of the zip file in a human-readable format.
        """
        return get_readable_file_size(self.__size)

    def eta(self) -> str:
        """
        Get the estimated time of arrival of the zip file.

        :return: Estimated time of arrival of the zip file.
        """
        try:
            seconds = (self.__size - self.processed_raw()) / self.speed_raw()
            return get_readable_time(seconds)
        except:
            return '-'

    def status(self) -> str:
        """
        Get the status of the zip file.

        :return: Status of the zip file.
        """
        return MirrorStatus.STATUS_ARCHIVING

    def processed_raw(self) -> Union[int, float]:
        """
        Get the processed size of the zip file.

        :return: Processed size of the zip file.
        """
        if self.__listener.newDir is not None:
            return async_to_sync(get_path_size, self.__listener.newDir)
        else:
            return async_to_sync(get_path_size, self.__listener.dir) - self.__size

    def processed_bytes(self) -> str:
        """
        Get the processed size of the zip file in a human-readable format.

        :return: Processed size of the zip file in a human-readable format.
        """
        return get_readable_file_size(self.processed_raw())

    def download(self) -> 'ZipStatus':
        """
        Get the ZipStatus object itself.

        :return: ZipStatus object.
        """
        return self

    async def cancel_download(self):
        """
        Cancel the download of the zip file.
        """
        if hasattr(self.__listener, 'suproc'):
            if self.__listener.suproc is not None:
                self.__listener.suproc.kill()
            else:
                self.__listener.suproc = 'cancelled'
            await self.__listener.onUploadError('archiving stopped by user!')
        else:
            LOGGER.info(f'Cancelling Archive: {self.__name}')

    def eng(self) -> str:
        """
        Get the engine status.

        :return: Engine status.
        """
        return EngineStatus().STATUS_ZIP
