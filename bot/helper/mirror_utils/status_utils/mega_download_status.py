import os
from dataclasses import dataclass
from typing import NamedTuple
from pathlib import Path
from datetime import timedelta

import dateutil.parser

# Custom classes
from bot.helper.ext_utils.bot_utils import EngineStatus, MirrorStatus, get_readable_file_size, get_readable_time


class UploadDetails(NamedTuple):
    user: str
    url: str


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
        self.name = name
        self.size = size
        self.gid = gid
        self.obj = obj
        self.message = message
        self.upload_details = upload_details

    @property
    def progress_raw(self) -> float:
        """
        Get the progress of the download in percentage.

        :return: Progress in percentage
        """
        try:
            return round(self.obj.downloaded_bytes / self.size * 100, 2)
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
        return get_readable_file_size(self.obj.downloaded_bytes)

    @property
    def eta(self) -> str:
        """
        Get the estimated time of arrival of the download.

        :return: Estimated time of arrival of the download
        """
        try:
            seconds = (self.size - self.obj.downloaded_bytes) / self.obj.speed
            return get_readable_time(timedelta(seconds=seconds).total_seconds())
        except ZeroDivisionError:
            return '-'

    @property
    def speed(self) -> str:
        """
        Get the download speed in a human-readable format.

        :return: Download speed in a human-readable format
        """
        return f'{get_readable_file_size(self.obj.speed)}/s'

    @property
    def gid(self) -> str:
        """
        Get the unique identifier of the download.

        :return: Unique identifier of the download
        """
        return self.gid

    @property
    def download(self) -> object:
        """
        Get the object containing download details.

        :return: Object containing download details
        """
        return self.obj

    @property
    def eng(self) -> EngineStatus:
        """
        Get the engine status.

        :return: Engine status
        """
        return EngineStatus().STATUS_MEGA

    @classmethod
    def from_dict(cls, data: dict):
        """
        Create a MegaDownloadStatus object from a dictionary.

        :param data: Dictionary containing download details
        :return: MegaDownloadStatus object
        """
        name = data['name']
        size = data['size']
        gid = data['gid']
        obj = data['obj']
        message = data['message']
        upload_details = UploadDetails(user=data['upload_details']['user'],
                                       url=data['upload_details']['url'])
        return cls(name, size, gid, obj, message, upload_details)

