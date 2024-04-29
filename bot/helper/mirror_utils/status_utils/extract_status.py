#!/usr/bin/env python3
from time import time, sleep
from typing import Optional

from bot.helper.ext_utils.bot_utils import EngineStatus, get_readable_file_size
from bot.helper.ext_utils.fs_utils import get_path_size

class ExtractionStatus:
    """
    Class representing the status of an extraction process.
    """
    _progress_update_interval = 5  # seconds

    def __init__(self, name: str, size: int, group_id: int, listener):
        """
        Initialize the ExtractionStatus object.

        :param name: The name of the file or directory being extracted.
        :param size: The size of the file or directory being extracted in bytes.
        :param group_id: The group id associated with the file or directory.
        :param listener: The listener object that is responsible for handling the extraction process.
        """
        self.name = name
        self.size = size
        self.group_id = group_id
        self.listener = listener
        self.user_id = listener.user_id
        self.start_time = time()
        self.message = listener.message
        self.total_transferred = 0

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

    def update_progress(self):
        """
        Calculate and update the progress of the extraction.
        """
        current_time = time()
        if current_time - self.start_time > self._progress_update_interval:
            self.total_transferred = get_path_size(self.name)
            self.start_time = current_time

    @property
    def progress(self) -> float:
        """
        Get the current progress of the extraction as a float between 0 and 1.

        :return: The current progress of the extraction as a float between 0 and 1.
        """
        if self.size == 0:
            return 0
        return self.total_transferred / self.size

    @property
    def eta(self) -> Optional[str]:
        """
        Estimate the time remaining for the extraction to complete.

        :return: The estimated time remaining as a string, or None if the extraction is complete.
        """
        if self.total_transferred == self.size:
            return None
        time_elapsed = time() - self.start_time
        speed = self.total_transferred / time_elapsed
        time_remaining = (self.size - self.total_transferred) / speed
        return get_readable_time(time_remaining)

    @property
    def speed(self) -> Optional[str]:
        """
        Get the current extraction speed in a human-readable format.

        :return: The current extraction speed in a human-readable format, or None if the extraction is complete.
        """
        if self.total_transferred == self.size:
            return None
        time_elapsed = time() - self.start_time
        speed = self.total_transferred / time_elapsed
        return get_readable_file_size(speed)

    def __str__(self) -> str:
        """
        Get a human-readable representation of the ExtractionStatus object.

        :return: A string representation of the ExtractionStatus object.
        """
        return f"ExtractionStatus(name='{self.name}', size={self.readable_size}, group_id={self.group_id}, user_id={self.user_id}, start_time={self.start_time}, message={self.message}, total_transferred={self.total_transferred})"

    def __repr__(self) -> str:
        """
        Get a more informative representation of the ExtractionStatus object.

        :return: A string representation of the ExtractionStatus object.
        """
        return (f"ExtractionStatus("
                f"name='{self.name}', "
                f"size={self.readable_size}, "
                f"group_id={self.group_id}, "
                f"user_id={self.user_id}, "
                f"start_time={self.start_time}, "
                f"message={self.message}, "
                f"total_transferred={self.total_transferred})")

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
        status += f"\nProgress: {self.progress:.2%}"
        eta = self.eta
        if eta is not None:
            status += f"\nETA: {eta}"
        speed = self.speed
        if speed is not None:
            status += f"\nSpeed: {speed}"
        return status
