#!/usr/bin/env python3
from time import time

from bot import LOGGER
from bot.helper.ext_utils.bot_utils import EngineStatus, get_readable_file_size, MirrorStatus, get_readable_time, async_to_sync
from bot.helper.ext_utils.fs_utils import get_path_size

class ZipStatus:
    """
    A class to represent the status of a ZIP archive.

    Attributes:
        name (str): The name of the ZIP archive.
        size (int): The size of the ZIP archive in bytes.
        gid (int): The group ID of the ZIP archive.
        listener (object): The listener object that is responsible for updating the status of the ZIP archive.
        upload_details (dict): The upload details of the ZIP archive.
        uid (int): The user ID of the ZIP archive.
        start_time (float): The start time of the ZIP archive creation.
        message (object): The message object associated with the ZIP archive.
    """

    def __init__(self, name: str, size: int, gid: int, listener):
        self.__name = name
        self.__size = size
        self.__gid = gid
        self.__listener = listener
        self.upload_details = listener.upload_details
        self.__uid = listener.uid
        self.__start_time = time()
        self.message = listener.message

    @property
    def gid(self) -> int:
        """
        Returns the group ID of the ZIP archive.
        """
        return self.__gid

    @property
    def speed_raw(self) -> float:
        """
        Returns the speed of the ZIP archive creation in bytes per second.
        """
        return self.processed_raw / (time() - self.__start_time)

    @property
    def progress_raw(self) -> float:
        """
        Returns the progress of the ZIP archive creation as a percentage.
        """
        try:
            return self.processed_raw / self.__size * 100
        except:
            return 0

    @property
    def progress(self) -> str:
        """
        Returns the progress of the ZIP archive creation as a formatted string.
        """
        return f'{round(self.progress_raw, 2)}%'

    @property
    def speed(self) -> str:
        """
        Returns the speed of the ZIP archive creation as a formatted string.
        """
        return f'{get_readable_file_size(self.speed_raw)}/s'

    @property
    def name(self) -> str:
        """
        Returns the name of the ZIP archive.
        """
        return self.__name

    @property
    def size(self) -> str:
        """
        Returns the size of the ZIP archive as a formatted string.
        """
        return get_readable_file_size(self.__size)

    @property
    def eta(self) -> str:
        """
        Returns the estimated time of arrival of the ZIP archive creation as a formatted string.
        """
        try:
            seconds = (self.__size - self.processed_raw) / self.speed_raw
            return get_readable_time(seconds)
        except:
            return '-'

    @property
    def status(self) -> MirrorStatus:
        """
        Returns the status of the ZIP archive creation.
        """
        return MirrorStatus.STATUS_ARCHIVING

    @property
    def processed_raw(self) -> int:
        """
        Returns the amount of data processed in the ZIP archive creation in bytes.
        """
        if self.__listener.new_dir:
            return async_to_sync(get_path_size, self.__listener.new_dir)
        else:
            return async_to_sync(get_path_size, self.__listener.dir) - self.__size

    @processed_raw.setter
    def processed_raw(self, value: int):
        """
        Sets the amount of data processed in the ZIP archive creation in bytes.
        """
        self.__processed_raw = value

    @property
    def processed_bytes(self) -> str:
        """
        Returns the amount of data processed in the ZIP archive creation as a formatted string.
        """
        return get_readable_file_size(self.processed_raw)

    def download(self) -> 'ZipStatus':
        """
        Returns the ZipStatus object itself.
        """
        return self

    async def cancel_download(self):
        """
        Cancels the ZIP archive creation and logs the event.
        """
        LOGGER.info(f'Cancelling Archive: {self.__name}')
        if self.__listener.suproc is not None:
            self.__listener.suproc.kill()
        else:
            self.__listener.suproc = 'cancelled'
        await self.__listener.on_upload_error('archiving stopped by user!')

    def eng(self) -> EngineStatus:
        """
        Returns the engine status of the ZIP archive creation.
        """
        return EngineStatus().STATUS_ZIP

    def __str__(self):
        """
        Returns a human-readable representation of the ZipStatus object.
        """
        return (
            f'Name: {self.name}\n'
            f'Size: {self.size}\n'
            f'GID: {self.gid}\n'
            f'Speed: {self.speed}\n'
            f'Progress: {self.progress}\n'
            f'ETA: {self.eta}\n'
            f'Status: {self.status}\n'
            f'Processed: {self.processed_bytes}\n'
        )
