import os
from dataclasses import dataclass
from typing import NamedTuple
from pathlib import Path
from datetime import timedelta
import dateutil.parser

# Custom classes
# from bot.helper.ext_utils.bot_utils import EngineStatus, MirrorStatus, get_readable_file_size, get_readable_time

class CustomNamedTuple(NamedTuple):
    """
    A custom version of NamedTuple that allows for class methods and properties.
    """
    user: str
    url: str

    @property
    def readable_size(self):
        """
        Returns the size of the file in a human-readable format.
        """
        return get_readable_file_size(self.size)


class MegaDownloadStatus:
    """
    A class representing the status of a Mega download.
    """
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
    def readable_size(self):
        """
        Returns the size of the file in a human-readable format.
        """
        return get_readable_file_size(self.size)

    @property
    def readable_time(self):
        """
        Returns the time taken for the download in a human-readable format.
        """
        return get_readable_time(self.obj.time)

    def __str__(self):
        """
        Returns a string representation of the MegaDownloadStatus object.
        """
        return (f"File Name: {self.name}\n"
                f"File Size: {self.readable_size}\n"
                f"GID: {self.gid}\n"
                f"Time Taken: {self.readable_time}\n"
                f"Upload Details: {self.upload_details}\n")
