import os
from dataclasses import dataclass
from typing import Optional, Union
from pathlib import Path
from datetime import timedelta
import dateutil.parser

@dataclass
class CustomFile:
    """
    A custom class representing a file with a human-readable size.
    """
    user: str
    url: str
    size: int

    @property
    def readable_size(self) -> str:
        """
        Returns the size of the file in a human-readable format.
        """
        return get_readable_file_size(self.size)

def get_readable_file_size(size: int) -> str:
    """
    Returns the size of the file in a human-readable format.
    """
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size < 1024:
            break
        size /= 1024.0
    return f"{size:.2f} {unit}"

@dataclass
class MegaDownloadStatus:
    """
    A class representing the status of a Mega download.
    """
    name: str
    size: int
    gid: str
    obj: Optional[Path] = None
    message: Optional[Path] = None
    upload_details: Union[str, None] = None
    time: Optional[str] = None

    def __post_init__(self):
        """
        Handles the parsing of the `time` attribute.
        """
        if self.time is not None:
            self.time = parse_time(self.time)

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
        if self.time is not None:
            return str(self.time)
        return "N/A"

    def __str__(self):
        """
        Returns a string representation of the MegaDownloadStatus object.
        """
        return (f"File Name: {self.name}\n"
                f"File Size: {self.readable_size}\n"
                f"GID: {self.gid}\n"
                f"Time Taken: {self.readable_time}\n"
                f"Upload Details: {self.upload_details}\n")

def parse_time(time_str: str) -> timedelta:
    """
    Parses a time string into a `timedelta` object.
    """
    try:
        return dateutil.parser.parse(time_str) - dateutil.parser.parse("1970-01-01T00:00:00Z")
    except ValueError:
        raise ValueError(f"Invalid time string: {time_str}")
