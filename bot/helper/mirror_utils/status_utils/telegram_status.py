#!/usr/bin/env python3

import math
from bot.helper.ext_utils.bot_utils import EngineStatus, MirrorStatus, get_readable_file_size, get_readable_time

class TelegramStatus:
    """
    Class representing the status of a file transfer in Telegram.
    """

    def __init__(self, obj, size: int, message, gid: str, status: str, upload_details):
        """
        Initialize the TelegramStatus object.

        :param obj: The file transfer object
        :param size: The total size of the file
        :param message: The message object
        :param gid: The global ID of the file transfer
        :param status: The status of the file transfer
        :param upload_details: The upload details
        """
        self._obj = obj
        self._size = size
        self._gid = gid
        self._status = status
        self.upload_details = upload_details
        self.message = message
        self._engine_status = EngineStatus().STATUS_TG if status == 'tg' else EngineStatus().STATUS_MD

    @property
    def processed_bytes(self) -> str:
        """
        Returns the number of processed bytes in a readable format.

        :return: The processed bytes in a readable format
        """
        return get_readable_file_size(self._obj.processed_bytes)

    @property
    def size(self) -> str:
        """
        Returns the total size of the file in a readable format.

        :return: The total size of the file in a readable format
        """
        return get_readable_file_size(self._size)

    @property
    def status(self) -> MirrorStatus:
        """
        Returns the status of the file transfer.

        :return: The status of the file transfer
        """
        return MirrorStatus[self._status.upper()]

    @property
    def name(self) -> str:
        """
        Returns the name of the file.

        :return: The name of the file
        """
        return self._obj.name

    @property
    def progress(self) -> str:
        """
        Returns the progress of the file transfer as a percentage.

        :return: The progress of the file transfer as a percentage
        """
        try:
            progress_raw = self._obj.processed_bytes / self._size * 100
            return f'{progress_raw:.2f}%'
        except:
            return '0.00%'

    @property
    def speed(self) -> str:
        """
        Returns the speed of the file transfer in a readable format.

        :return: The speed of the file transfer in a readable format
        """
        try:
            speed = self._obj.speed
            if not isinstance(speed, (int, float)):
                return '-'
            return get_readable_file_size(speed) + '/s'
        except:
            return '-'

    @property
    def eta(self) -> str:
        """
        Returns the estimated time of arrival in a readable format.

        :return: The estimated time of arrival in a readable format
        """
        try:
            seconds = (self._size - self._obj.processed_bytes) / self._obj.speed
            if not isinstance(seconds, (int, float)):
                return '-'
            return get_readable_time(seconds)
        except:
            return '-'

    @property
    def gid(self) -> str:
        """
        Returns the global ID of the file transfer.

        :return: The global ID of the file transfer
        """
        return self._gid

    @property
    def download(self) -> object:
        """
        Returns the file object for downloading.

        :return: The file object for downloading
        """
        if not self._obj:
            raise AttributeError("File object not initialized.")
        return self._obj

    @engine_status.setter
    def engine_status(self, status: str):
        """
        Set the engine status for Telegram.

        :param status: The engine status
        """
        if status not in ['tg', 'md']:
            raise ValueError("Invalid engine status.")
        self._engine_status = EngineStatus().STATUS_TG if status == 'tg' else EngineStatus().STATUS_MD

    @property
    def engine_status(self) -> str:
        """
        Returns the engine status for Telegram.

        :return: The engine status for Telegram
        """
        return self._engine_status
