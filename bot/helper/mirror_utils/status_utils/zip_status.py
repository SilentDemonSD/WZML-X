#!/usr/bin/env python3
import time
from typing import Dict, Optional

from bot import LOGGER
from bot.helper.ext_utils.bot_utils import EngineStatus, get_readable_file_size, MirrorStatus, get_readable_time, async_to_sync
from bot.helper.ext_utils.fs_utils import get_path_size

class ZipStatus:
    """
    A class to represent the status of a ZIP archive.
    """

    def __init__(self, name: str, size: int, gid: int, listener):
        self.name = name
        self.size = size
        self.gid = gid
        self.listener = listener
        self.upload_details = listener.upload_details
        self.uid = listener.uid
        self.start_time = time.time()
        self.message = listener.message
        self._processed_raw = 0

    @property
    def processed_raw(self) -> int:
        """
        Returns the amount of data processed in the ZIP archive creation in bytes.
        """
        if self.listener.new_dir:
            return async_to_sync(get_path_size, self.listener.new_dir)
        else:
            return async_to_sync(get_path_size, self.listener.dir) - self.size

    @processed_raw.setter
    def processed_raw(self, value: int):
        """
        Sets the amount of data processed in the ZIP archive creation in bytes.
        """
        self._processed_raw = value

    @property
    def processed(self) -> str:
        """
        Returns the amount of data processed in the ZIP archive creation as a formatted string.
        """
        return get_readable_file_size(self.processed_raw)

    @property
    def speed_raw(self) -> float:
        """
        Returns the speed of the ZIP archive creation in bytes per second.
        """
        return self.processed_raw / (time.time() - self.start_time)

    @property
    def speed(self) -> str:
        """
        Returns the speed of the ZIP archive creation as a formatted string.
        """
        return get_readable_file_size(self.speed_raw) + '/s'

    @property
    def progress_raw(self) -> float:
        """
        Returns the progress of the ZIP archive creation as a percentage.
        """
        try:
            return self.processed_raw / self.size * 100
        except ZeroDivisionError:
            return 0

    @property
    def progress(self) -> str:
        """
        Returns the progress of the ZIP archive creation as a formatted string.
        """
        return f'{self.progress_raw:.2f}%'

    @property
    def eta(self) -> Optional[str]:
        """
        Returns the estimated time of arrival of the ZIP archive creation as a formatted string.
        """
        try:
            seconds_left = (self.size - self.processed_raw) / self.speed_raw
            return get_readable_time(seconds_left)
        except ZeroDivisionError:
            return '-'

    @property
    def status(self) -> MirrorStatus:
        """
        Returns the status of the ZIP archive creation.
        """
        return MirrorStatus.STATUS_ARCHIVING

    def download(self) -> 'ZipStatus':
        """
        Returns the ZipStatus object itself.
        """
        return self

    async def cancel_download(self):
        """
        Cancels the ZIP archive creation and logs the event.
        """
        LOGGER.info(f'Cancelling Archive: {self.name}')
        if self.listener.suproc is not None:
            self.listener.suproc.kill()
        else:
            self.listener.suproc = 'cancelled'
        await self.listener.on_upload_error('archiving stopped by user!')

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
            f'Processed: {self.processed}\n'
        )
