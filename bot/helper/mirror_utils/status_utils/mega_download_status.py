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

