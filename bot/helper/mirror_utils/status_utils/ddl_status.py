#!/usr/bin/env python3

from bot.helper.ext_utils.bot_utils import MirrorStatus, get_readable_file_size, get_readable_time

class DDLStatus:
    def __init__(self, obj, size: int, message, gid, upload_details):
        """
        Initialize a new DDLStatus object.

        :param obj: An object that contains information about the file being uploaded.
        :param size: The size of the file in bytes.
        :param message: A message associated with the upload.
        :param gid: A globally unique identifier for the upload.
        :param upload_details: Additional details about the upload.
        """
        self.__obj = obj
        self.__size = size
        self.__gid = gid
        self.upload_details = upload_details
        self.message = message

    def processed_bytes(self) -> str:
        """
        Return the number of bytes that have been processed during the upload in a human-readable format.

        :return: The processed bytes in a human-readable format.
        """
        return get_readable_file_size(self.__obj.processed_bytes)

    def size(self) -> str:
        """
        Return the size of the file in a human-readable format.

        :return: The file size in a human-readable format.
        """
        return get_readable_file_size(self.__size)

    @property
    def status(self) -> MirrorStatus:
        """
        Return the status of the upload.

        :return: The status of the upload.
        """
        return MirrorStatus.STATUS_UPLOADING

    def name(self) -> str:
        """
        Return the name of the file being uploaded.

        :return: The name of the file being uploaded.
        """
        return self.__obj.name

    def progress(self) -> str:
        """
        Return the progress of the upload as a percentage.

        :return: The progress of the upload as a percentage.
        """
        progress_raw = self.__obj.processed_bytes / self.__size * 100 if self.__size != 0 else 0
        return f'{round(progress_raw, 2)}%'

    def speed(self) -> str:
        """
        Return the current upload speed in a human-readable format.

        :return: The current upload speed in a human-readable format.
        """
        return f'{get_readable_file_size(self.__obj.speed)}/s'

    def eta(self) -> str:
        """
        Return the estimated time of arrival for the upload.

        :return: The estimated time of arrival for the upload.
        """
        try:
            seconds = (self.__size - self.__obj.processed_bytes) / self.__obj.speed if self.__obj.speed != 0 else 0
            return get_readable_time(seconds)
        except:
            return '-'

    def gid(self) -> str:
        """
        Return the globally unique identifier for the upload.

        :return: The globally unique identifier for the upload.
        """
        return self.__gid

    def download(self):
        """
        Return the object that contains information about the file being uploaded.

        :return: The object that contains information about the file being uploaded.
        """
        return self.__obj

    def eng(self):
        """
        Return the engine associated with the upload.

        :return: The engine associated with the upload.
        """
        return self.__obj.engine
