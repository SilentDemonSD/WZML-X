#!/usr/bin/env python3
import math
from bot.helper.ext_utils.bot_utils import EngineStatus, MirrorStatus, get_readable_file_size, get_readable_time

class TelegramStatus:
    """
    Class representing the status of a file being uploaded or downloaded in Telegram.
    """
    def __init__(self, obj, size, message, gid, status, upload_details):
        """
        Initialize the TelegramStatus object.

        :param obj: The object representing the file being uploaded/downloaded
        :param size: The total size of the file
        :param message: The message object associated with the file
        :param gid: The global ID of the file
        :param status: The status of the file (uploading/downloading)
        :param upload_details: The details of the upload
        """
        self.__obj = obj
        self.__size = size
        self.__gid = gid
        self.__status = status
        self.upload_details = upload_details
        self.message = message

    def processed_bytes(self):
        """
        Return the processed bytes of the file as a human-readable string.

        :return: The processed bytes as a string
        """
        return get_readable_file_size(self.__obj.processed_bytes)

    def size(self):
        """
        Return the total size of the file as a human-readable string.

        :return: The total size as a string
        """
        return get_readable_file_size(self.__size)

    def status(self):
        """
        Return the status of the file as a MirrorStatus object.

        :return: The status as a MirrorStatus object
        """
        if self.__status == 'up':
            return MirrorStatus.STATUS_UPLOADING
        return MirrorStatus.STATUS_DOWNLOADING

    def name(self):
        """
        Return the name of the file.

        :return: The name of the file
        """
        return self.__obj.name if self.__obj else ""

    def progress(self):
        """
        Return the progress of the file as a string.

        :return: The progress as a string
        """
        if self.__obj is None:
            return "0%"
        try:
            progress_raw = self.__obj.processed_bytes / self.__size * 100
            return f'{round(progress_raw, 2)}%' if math.isclose(progress_raw, 100.0), 100.0 else f'{round(progress_raw, 2)}%'
        except:
            return '0%'

    def speed(self):
        """
        Return the speed of the file transfer as a human-readable string.

        :return: The speed as a string
        """
        return f'{get_readable_file_size(self.__obj.speed)}/s' if self.__obj else "0/s"

    def eta(self):
        """
        Return the estimated time of arrival as a human-readable string.

        :return: The ETA as a string
        """
        if self.__obj is None:
            return '-'
        try:
            seconds = (self.__size - self.__obj.processed_bytes) / self.__obj.speed
            return get_readable_time(seconds)
        except:
            return '-'

    def gid(self) -> str:
        """
        Return the global ID of the file.

        :return: The global ID as a string
        """
        return self.__gid

    def download(self):
        """
        Return the file object for downloading.

        :return: The file object
        """
        return self.__obj

    def eng(self):
        """
        Return the engine status as a EngineStatus object.

        :return: The engine status as a EngineStatus object
        """
        return EngineStatus().STATUS_TG
