#!/usr/bin/env python3
from time import time
from typing import Optional

from bot.helper.ext_utils.bot_utils import EngineStatus, get_readable_file_size
from bot.helper.ext_utils.fs_utils import get_path_size

class ExtractStatus:
    """
    Class representing the status of an extraction process.
    """
    def __init__(self, name: str, size: int, group_id: int, listener):
        """
        Initialize the ExtractStatus object.

        :param name: The name of the file or directory being extracted.
        :param size: The size of the file or directory being extracted in bytes.
        :param group_id: The group id associated with the file or directory.
        :param listener: The listener object that is responsible for handling the extraction process.
        """
        self.name = name
        self.size = size
        self.group_id = group_id
        self.listener = listener
        self.upload_details = listener.upload_details
        self.user_id = listener.user_id
        self.start_time = time()
        self.message = listener.message

    @property
    def readable_size(self) -> str:
        """
        Get the size of the file or directory in a human-readable format.

        :return: The size of the file or directory in a human-readable format.
        """
        return get_readable_file_size(self.size)

    @property
    def readable_time_elapsed(self) -> str:
        """
        Get the time elapsed since the start of the extraction process in a human-readable format.

        :return: The time elapsed since the start of the extraction process in a human-readable format.
        """
        return get_readable_time(time() - self.start_time)

    @property
    def path_size(self) -> int:
        """
        Get the size of the path (file or directory) in bytes.

        :return: The size of the path in bytes.
        """
        return get_path_size(self.name)

    def __str__(self) -> str:
        """
        Get a human-readable representation of the ExtractStatus object.

        :return: A string representation of the ExtractStatus object.
        """
        return f"ExtractStatus(name='{self.name}', size={self.readable_size}, group_id={self.group_id}, user_id={self.user_id}, start_time={self.start_time}, message={self.message})"

    def __repr__(self) -> str:
        """
        Get a more informative representation of the ExtractStatus object.

        :return: A string representation of the ExtractStatus object.
        """
        return (f"ExtractStatus("
                f"name='{self.name}', "
                f"size={self.readable_size}, "
                f"group_id={self.group_id}, "
                f"user_id={self.user_id}, "
                f"start_time={self.start_time}, "
                f"message={self.message})")

    def status(self) -> str:
        """
        Get a summary of the extraction status.

        :return: A string summary of the extraction status.
        """
        status = f"Extraction of {self.name} started at {self.start_time}."
        if self.size:
            status += f"\nSize: {self.readable_size}"
        if self.path_size != self.size:
            status += f"\nPath size: {get_readable_file_size(self.path_size)}"
        status += f"\nTime elapsed: {self.readable_time_elapsed}"
        return status
