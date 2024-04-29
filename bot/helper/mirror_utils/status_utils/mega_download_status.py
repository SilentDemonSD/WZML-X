#!/usr/bin/env python3
from bot.helper.ext_utils.bot_utils import EngineStatus, get_readable_file_size, MirrorStatus, get_readable_time

class MegaDownloadStatus:
    def __init__(self, name: str, size: int, gid: str, obj, message, upload_details):
        """
        Initialize the MegaDownloadStatus object.

        :param name: Name of the file being downloaded
        :param size: Size of the file in bytes
        :param gid: The unique identifier of the download
        :param obj: The object containing download details
        :param message: The message object associated with the download
        :param upload_details: Details of the upload
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
        Get the name of the file being downloaded.

        :return: Name of the file
        """
        return self.__name

    @property
    def progress_raw(self) -> float:
        """
        Get the progress of the download in percentage.

        :return: Progress in percentage
        """
        try:
            return round(self.__obj.downloaded_bytes / self.__size * 100, 2)
        except:
            return 0.0

    @property
    def progress(self) -> str:
        """
        Get the progress of the download in percentage as a string.

        :return: Progress in percentage as a string
        """
        return f"{self.progress_raw}%"

    @property
    def status(self) -> MirrorStatus:
        """
        Get the status of the download.

        :return: Download status
        """
        return MirrorStatus.STATUS_DOWNLOADING

    @property
    def processed_bytes(self) -> str:
        """
        Get the size of the data downloaded in a human-readable format.

        :return: Downloaded data size in a human-readable format
        """
        return get_readable_file_size(self.__obj.downloaded_bytes)

    @property
    def eta(self) -> str:
        """
        Get the estimated time of arrival of the download.

        :return: Estimated time of arrival of the download
        """
        try:
            seconds = (self.__size - self.__obj.downloaded_bytes) / self.__obj.speed
            return get_readable_time(seconds)
        except ZeroDivisionError:
            return '-'

    @property
    def size(self) -> str:
        """
        Get the size of the file in a human-readable format.

        :return: File size in a human-readable format
        """
        return get_readable_file_size(self.__size)

    @property
    def speed(self) -> str:
        """
        Get the download speed in a human-readable format.

        :return: Download speed in a human-readable format
        """
        return f'{get_readable_file_size(self.__obj.speed)}/s'

    @property
    def gid(self) -> str:
        """
        Get the unique identifier of the download.

        :return: Unique identifier of the download
        """
        return self.__gid

    @property
    def download(self) -> object:
        """
        Get the object containing download details.

        :return: Object containing download details
        """
        return self.__obj

    @property
    def eng(self) -> EngineStatus:
        """
        Get the engine status.

        :return: Engine status
        """
        return EngineStatus().STATUS_MEGA
