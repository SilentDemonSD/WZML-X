#!/usr/bin/env python3

from bot.helper.ext_utils.bot_utils import MirrorStatus, get_readable_file_size, get_readable_time

class DDLStatus:
    """
    A class representing the status of a file upload.
    """
    def __init__(self, obj, size: int, message, gid):
        """
        Initialize a new DDLStatus object.

        :param obj: An object that contains information about the file being uploaded.
        :param size: The size of the file in bytes.
        :param message: A message associated with the upload.
        :param gid: A globally unique identifier for the upload.
        """
        self.__obj = obj
        self.__size = size
        self.__gid = gid
        self.message = message

    @property
    def processed_bytes(self) -> int:
        """
        Return the number of bytes that have been processed during the upload.

        :return: The processed bytes.
        """
        return self.__obj.processed_bytes

    @property
    def size(self) -> int:
        """
        Return the size of the file.

        :return: The file size.
        """
        return self.__size

    @property
    def status(self) -> MirrorStatus:
        """
        Return the status of the upload.

        :return: The status of the upload.
        """
        return MirrorStatus.STATUS_UPLOADING

    @property
    def name(self) -> str:
        """
        Return the name of the file being uploaded.

        :return: The name of the file being uploaded.
        """
        return self.__obj.name

    @property
    def progress(self) -> float:
        """
        Return the progress of the upload as a percentage.

        :return: The progress of the upload as a percentage.
        """
        progress_raw = self.__obj.processed_bytes / self.__size * 100 if self.__size != 0 else 0
        return round(progress_raw, 2)

    @property
    def speed(self) -> str:
        """
        Return the current upload speed in a human-readable format.

        :return: The current upload speed in a human-readable format.
        """
        speed = self.__obj.speed
        if speed == 0:
            return "0 B/s"
        else:
            return get_readable_file_size(speed) + "/s"

    @property
    def eta(self) -> str:
        """
        Return the estimated time of arrival for the upload.

        :return: The estimated time of arrival for the upload.
        """
        try:
            seconds = (self.__size - self.__obj.processed_bytes) / self.__obj.speed if self.__obj.speed != 0 else 0
            if seconds < 0:
                return "-"
            else:
                return get_readable_time(seconds)
        except:
            return '-'

    @property
    def gid(self) -> str:
        """
        Return the globally unique identifier for the upload.

        :return: The globally unique identifier for the upload.
        """
        return self.__gid

    @property
    def download(self) -> object:
        """
        Return the object that contains information about the file being uploaded.

        :return: The object that contains information about the file being uploaded.
        """
        return self.__obj

    @property
    def eng(self) -> object:
        """
        Return the engine associated with the upload.

        :return: The engine associated with the upload.
        """
        return self.__obj.engine

