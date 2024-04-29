#!/usr/bin/env python3

import math
from bot.helper.ext_utils.bot_utils import EngineStatus, MirrorStatus, get_readable_file_size, get_readable_time

class TelegramStatus:
    """
    Class representing the status of a file transfer in Telegram.
    """

    def __init__(self, obj, size: int, message, gid: str, status: str, upload_details):
        self.__obj = obj
        self.__size = size
        self.__gid = gid
        self.__status = status
        self.upload_details = upload_details
        self.message = message

    @property
    def processed_bytes(self) -> str:
        """
        Returns the number of processed bytes in a readable format.
        """
        return get_readable_file_size(self.__obj.processed_bytes)

    @property
    def size(self) -> str:
        """
        Returns the total size of the file in a readable format.
        """
        return get_readable_file_size(self.__size)

    @property
    def status(self) -> MirrorStatus:
        """
        Returns the status of the file transfer.
        """
        return MirrorStatus.STATUS_UPLOADING if self.__status == 'up' else MirrorStatus.STATUS_DOWNLOADING

    @property
    def name(self) -> str:
        """
        Returns the name of the file.
        """
        return self.__obj.name

    @property
    def progress(self) -> str:
        """
        Returns the progress of the file transfer as a percentage.
        """
        try:
            progress_raw = self.__obj.processed_bytes / self.__size * 100
            return f'{progress_raw:.2f}%'
        except:
            return '0.00%'

    @property
    def speed(self) -> str:
        """
        Returns the speed of the file transfer in a readable format.
        """
        try:
            speed = self.__obj.speed
            if not isinstance(speed, (int, float)):
                return '-'
            return get_readable_file_size(speed) + '/s'
        except:
            return '-'

    @property
    def eta(self) -> str:
        """
        Returns the estimated time of arrival in a readable format.
        """
        try:
            seconds = (self.__size - self.__obj.processed_bytes) / self.__obj.speed
            if not isinstance(seconds, (int, float)):
                return '-'
            return get_readable_time(seconds)
        except:
            return '-'

    @property
    def gid(self) -> str:
        """
        Returns the global ID of the file transfer.
        """
        return self.__gid

    def download(self) -> object:
        """
        Returns the file object for downloading.
        """
        return self.__obj

    @property
    def eng(self) -> EngineStatus:
        """
        Returns the engine status for Telegram.
        """
        return EngineStatus().STATUS_TG
