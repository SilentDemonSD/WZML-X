import os
from dataclasses import dataclass
from typing import NamedTuple, Optional
from pathlib import Path
from datetime import timedelta
import dateutil.parser

class CustomNamedTuple(NamedTuple):
    """
    A custom version of NamedTuple that allows for class methods and properties.
    """
    user: str
    url: str

    @property
    def readable_size(self) -> str:
        """
        Returns the size of the file in a human-readable format.
        """
        return get_readable_file_size(self.size)

@dataclass
class MegaDownloadStatus:
    """
    A class representing the status of a Mega download.
    """
    name: str
    size: int
    gid: str
    obj: Optional[Path]
    message: Optional[Path]
    upload_details: str
    time: timedelta

    @property
    def readable_size(self) -> str:
        """
        Returns the size of the file in a human-readable format.
        """
        return get_readable_file_size(self.size)

    @property
    def readable_time(self) -> str:
        """
        Returns the time taken for the download in a human-readable format.
        """
        return str(self.time)

    def __str__(self):
        """
        Returns a string representation of the MegaDownloadStatus object.
        """
        return (f"File Name: {self.name}\n"
                f"File Size: {self.readable_size}\n"
                f"GID: {self.gid}\n"
                f"Time Taken: {self.readable_time}\n"
                f"Upload Details: {self.upload_details}\n")
