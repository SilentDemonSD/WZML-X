#!/usr/bin/env python3
import time
from typing import Dict, Optional

from bot import LOGGER
from bot.helper.ext_utils.bot_utils import EngineStatus, get_readable_file_size, MirrorStatus, async_to_sync
from bot.helper.ext_utils.fs_utils import get_path_size

class ZipArchiveStatus:
    """
    A class to represent the status of a ZIP archive creation process.
    """

    def __init__(self, name: str, size: int, gid: int, listener):
        """
        Initialize a new ZipArchiveStatus object.

        :param name: The name of the ZIP archive.
        :param size: The size of the ZIP archive in bytes.
        :param gid: The group ID associated with the ZIP archive.
        :param listener: The listener object that is responsible for handling the ZIP archive creation.
        """
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
        Get the amount of data processed in the ZIP archive creation in bytes.

        :return: The amount of data processed in bytes.
        """
        if self.listener.new_dir:
            return async_to_sync(get_path_size, self.listener.new_dir)
        else:
            return async_to_sync(get_path_size, self.listener.dir) - self.size

    @processed_raw.setter
    def processed_raw(self, value: int):
        """
        Set the amount of data processed in the ZIP archive creation in bytes.

        :param value: The amount of data processed in bytes.
        """
        self._processed_raw = value

    @property
    def processed(self) -> str:
        """
        Get the amount of data processed in the ZIP archive creation as a formatted string.

        :return: The amount of data processed as a formatted string.
        """
        return get_readable_file_size(self.processed_raw)

    @property
    def speed_raw(self) -> float:
        """
        Get the speed of the ZIP archive creation in bytes per second.

        :return: The speed of the ZIP archive creation in bytes per second.
        """
        return self.processed_raw / (time.time() - self.start_time)

    @property
    def speed(self) -> str:
        """
        Get the speed of the ZIP archive creation as a formatted string.

        :return: The speed of the ZIP archive creation as a formatted string.
        """
        return get_readable_file_size(self.speed_raw) + '/s'

    @property
    def progress_raw(self) -> float:
        """
        Get the progress of the ZIP archive creation as a percentage.

        :return: The progress of the ZIP archive creation as a percentage.
        """
        try:
            return self.processed_raw / self.size * 100
        except ZeroDivisionError:
            return 0

    @property
    def progress(self) -> str:
        """
        Get the progress of the ZIP archive creation as a formatted string.

        :return: The progress of the ZIP archive creation as a formatted string.
        """
        return f'{self.progress_raw:.2f}%'

    @property
    def eta(self) -> Optional[str]:
        """
        Get the estimated time of arrival of the ZIP archive creation as a formatted string.

        :return: The estimated time of arrival as a formatted string or None if it cannot be calculated.
        """
        try:
            seconds_left = (self.size - self.processed_raw) / self.speed_raw
            return get_readable_time(seconds_left)
        except ZeroDivisionError:
            return None

    @property
    def status(self) -> MirrorStatus:
        """
        Get the status of the ZIP archive creation.

        :return: The status of the ZIP archive creation.
        """
        return MirrorStatus.STATUS_ARCHIVING

    def download(self) -> 'ZipArchiveStatus':
        """
        Return the ZipArchiveStatus object itself.

        :return: The ZipArchiveStatus object.
        """
        return self

    async def cancel_download(self):
        """
        Cancel the ZIP archive creation and log the event.
        """
        LOGGER.info(f'Cancelling Archive: {self.name}')
        if self.listener.suproc is not None:
            self.listener.suproc.kill()
        else:
            self.listener.suproc = 'cancelled'
        await self.listener.on_upload_error('archiving stopped by user!')

    def eng(self) -> EngineStatus:
        """
        Get the engine status of the ZIP archive creation.

        :return: The engine status of the ZIP archive creation.
        """
        return EngineStatus().STATUS_ZIP

    def __str__(self):
        """
        Get a human-readable representation of the ZipArchiveStatus object.

        :return: A human-readable string representation of the ZipArchiveStatus object.
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

    def __repr__(self):
        """
        Get a developer-friendly representation of the ZipArchiveStatus object.

        :return: A developer-friendly string representation of the ZipArchiveStatus object.
        """
        return (
            f'ZipArchiveStatus(\n'
            f'    name={self.name},\n'
            f'    size={self.size},\n'
            f'    gid={self.gid},\n'
            f'    listener={self.listener},\n'
            f'    upload_details={self.upload_details},\n'
            f'    uid={self.uid},\n'
            f'    start_time={self.start_time},\n'
            f'    message={self.message},\n'
            f'    processed_raw={self.processed_raw},\n'
            f')'
        )
