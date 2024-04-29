#!/usr/bin/env python3
from bot.helper.ext_utils.bot_utils import EngineStatus, get_readable_file_size, MirrorStatus, get_readable_time

class MegaDownloadStatus:
    def __init__(self, name: str, size: int, gid: str, obj, message, upload_details):
        """
        Initialize the MegaDownloadStatus class with the given parameters.

        :param name: The name of the file being downloaded
        :param size: The size of the file in bytes
        :param gid: The globally unique identifier for the download
        :param obj: The object containing the download details
        :param message: The message object associated with the download
        :param upload_details: The upload details of the file
        """
        self.__obj = obj
        self.__name = name
        self.__size = size
        self.__gid = gid
        self.message = message
        self.upload_details = upload_details

    @property
    def name(self) -> str:
        """
        Return the name of the file being downloaded.

        :return: The name of the file
        """
        return self.__name

    @property
    def progress_raw(self) -> float:
        """
        Return the progress of the download as a raw value between 0 and 100.

        :return: The progress of the download
        """
        try:
            return round(self.__obj.downloaded_bytes / self.__size * 100, 2)
        except:
            return 0.0

    @property
    def progress(self) -> str:
        """
        Return the progress of the download as a formatted string with a percentage sign.

        :return: The progress of the download as a formatted string
        """
        return f"{self.progress_raw}%"

    @property
    def status(self) -> MirrorStatus:
        """
        Return the status of the download as MirrorStatus.STATUS_DOWNLOADING.

        :return: The status of the download
        """
        return MirrorStatus.STATUS_DOWNLOADING

    @property
    def processed_bytes(self) -> str:
        """
        Return the number of bytes downloaded as a human-readable string.

        :return: The number of bytes downloaded as a human-readable string
        """
        return get_readable_file_size(self.__obj.downloaded_bytes)

    @property
    def eta(self) -> str:
        """
        Return the estimated time of arrival of the download as a human-readable string.

        :return: The estimated time of arrival of the download as a human-readable string
        """
        try:
            seconds = (self.__size - self.__obj.downloaded_bytes) / self.__obj.speed
            return get_readable_time(seconds)
        except ZeroDivisionError:
            return '-'

    @property
    def size(self) -> str:
        """
        Return the size of the file as a human-readable string.

        :return: The size of the file as a human-readable string
        """
        return get_readable_file_size(self.__size)

    @property
    def speed(self) -> str:
        """
        Return the speed of the download as a human-readable string.

        :return: The speed of the download as a human-readable string
        """
        return f'{get_readable_file_size(self.__obj.speed)}/s'

    @property
    def gid(self) -> str:
        """
        Return the globally unique identifier for the download.

        :return: The globally unique identifier for the download
        """
        return self.__gid

    @property
    def download(self) -> object:
        """
        Return the object containing the download details.

        :return: The object containing the download details
        """
        return self.__obj

    @property
    def eng(self) -> EngineStatus:
        """
        Return the engine status as EngineStatus.STATUS_MEGA.

        :return: The engine status
        """
        return EngineStatus().STATUS_MEGA
