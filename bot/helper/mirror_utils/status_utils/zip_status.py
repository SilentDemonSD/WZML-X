#!/usr/bin/env python3
import time
from typing import Dict, Optional

from bot import LOGGER  # Importing LOGGER from bot module
from bot.helper.ext_utils.bot_utils import EngineStatus  # Importing EngineStatus from bot_utils module
from bot.helper.ext_utils.fs_utils import get_path_size  # Importing get_path_size from fs_utils module

class ZipCreationStatus:
    """
    A class to represent the status of a ZIP archive creation process.
    """
    __slots__ = (
        'name', 'size', 'listener', 'upload_details', 'uid', 'start_time', 'message', '_processed_raw',
    )

    def __init__(self, name: str, size: int, listener):
        """
        Initialize a new ZipCreationStatus object.

        :param name: The name of the ZIP archive.
        :param size: The size of the ZIP archive in bytes.
        :param listener: The listener object that is responsible for handling the ZIP archive creation.
        """
        self.name = name  # Name of the ZIP archive
        self.size = size  # Size of the ZIP archive in bytes
        self.listener = listener  # Listener object responsible for handling the ZIP archive creation
        self.upload_details = listener.upload_details  # Upload details of the ZIP archive
        self.uid = listener.uid  # Unique identifier for the ZIP archive creation process
        self.start_time = time.time()  # Start time of the ZIP archive creation process
        self.message = listener.message  # Message associated with the ZIP archive creation process
        self._processed_raw = 0  # Raw processed size of the ZIP archive in bytes

    @property
    def processed_raw(self) -> int:
        """
        Get the amount of data processed in the ZIP archive creation in bytes.

        :return: The amount of data processed in bytes.
        """
        return self._processed_raw

    def _set_processed_raw(self, value: int):
        """
        Set the amount of data processed in the ZIP archive creation in bytes.

        :param value: The amount of data processed in bytes.
        """
        self._processed_raw = value

    @property
    def processed(self) -> str:
        """Get the amount of data processed in the ZIP archive creation as a formatted string."""
        return self._format_size(self.processed_raw)

    @property
    def speed_raw(self) -> float:
        """Get the speed of the ZIP archive creation in bytes per second."""
        return self.processed_raw / (time.time() - self.start_time)

    @property
    def speed(self) -> str:
        """Get the speed of the ZIP archive creation as a formatted string."""
        return self._format_size(self.speed_raw) + '/s'

    @property
    def progress_raw(self) -> float:
        """Get the progress of the ZIP archive creation as a percentage."""
        try:
            return self.processed_raw / self.size * 100  # Calculating the progress as a percentage
        except ZeroDivisionError:
            return 0

    @property
    def progress(self) -> str:
        """Get the progress of the ZIP archive creation as a formatted string."""
        return f'{self.progress_raw:.2f}%'

    @property
    def eta(self) -> Optional[str]:
        """Get the estimated time of arrival of the ZIP archive creation as a formatted string."""
        try:
            seconds_left = (self.size - self.processed_raw) / self.speed_raw  # Calculating the estimated time left
            return self._format_time(seconds_left)  # Formatting the estimated time left
        except ZeroDivisionError:
            return None

    @property
    def status(self) -> EngineStatus:
        """Get the status of the ZIP archive creation."""
        return EngineStatus().STATUS_ZIP  # Returning the status of the ZIP archive creation

    async def cancel_download(self):
        """Cancel the ZIP archive creation and log the event."""
        LOGGER.info(f'Cancelling Archive: {self.name}')  # Logging the cancellation of the ZIP archive creation
        if self.listener.suproc is not None:
            self.listener.suproc.kill()  # Killing the subprocess if it exists
        else:
            self.listener.suproc = 'cancelled'  # Setting the subprocess to 'cancelled' if it doesn't exist
        await self.listener.on_upload_error('archiving stopped by user!')  # Calling the on_upload_error method with an appropriate message

    @property
    def eng(self) -> EngineStatus:
        """Get the engine status of the ZIP archive creation."""
        return EngineStatus().STATUS_ZIP  # Returning the engine status of the ZIP archive creation

    def __str__(self):
        """Get a human-readable representation of the ZipCreationStatus object."""
        return (
            f'Name: {self.name}\n'
            f'Size: {self.size}\n'
            f'Speed: {self.speed}\n'
            f'Progress: {self.progress}\n'
            f'ETA: {self.eta}\n'
            f'Status: {self.status}\n'
            f'Processed: {self.processed}\n'
        )  # Returning a human-readable string representation of the ZipCreationStatus object

    @classmethod
    def from_archive(cls, archive: str) -> 'ZipCreationStatus':
        """Create a new ZipCreationStatus object from an existing archive."""
        size = get_path_size(archive)  # Getting the size of the existing archive
        return cls(archive, size, None)  # Creating a new ZipCreationStatus object with the archive name, size, and no listener

    @classmethod
    def from_values(cls, name: str, size: int, processed_raw: int, start_time: float = None) -> 'ZipCreationStatus':
        """Create a new ZipCreationStatus instance from basic values."""
        if start_time is None:
            start_time = time.time()  # Setting the start time if it's not provided
        return cls(name, size, None, processed_raw=processed_raw, start_time=start_time)  # Creating a new ZipCreationStatus instance with the provided values

    def __len__(self):
        """Get the processed size in bytes."""
        return self.processed_raw  # Returning the processed size in bytes

    def __format__(self, format_spec):
        """Format the ZipCreationStatus object as a string."""
        if format_spec == '':
            format_spec = 'name, size, speed, progress, eta, status'  # Setting the format specification if it's not provided
        parts = format_spec.split(',')  # Splitting the format specification into parts
        result = []  # Initializing an empty list to store the formatted parts
        for part in parts:
            part = part.strip()  # Removing any leading or trailing whitespace from the part
            if part == 'name':
                result.append(self._format_value_part('name', self.name))  # Formatting and appending the name part
            elif part == 'size':
                result.append(self._format_value_part('size', self.size))  # Formatting and appending the size part
            elif part == 'speed':
                result.append(self._format_value_part('speed', self.speed))  # Formatting and appending the speed part
            elif part == 'progress':
                result.append(self._format_value_part('progress', self.progress))  # Formatting and appending the progress part
            elif part == 'eta':
                result.append(self._format_value_part('eta', self.eta))  # Formatting and appending the ETA part
            elif part == 'status':
                result.append(self._format_value_part('status', self.status))  # Formatting and appending the status part
            else:
                result.append(f'Unknown: {part}')  # Appending an 'Unknown' part if the format specification is not recognized
        return '\n'.join(result)  # Joining the formatted parts with newlines and returning the result

    def _format_values(self, values: dict) -> str:
        """Format a dictionary of values as a string."""
        result = []  # Initializing an empty list to store the formatted values
        for key, value in values.items():
            result.append(self._format_value_part(key, value))
        return ', '.join(result)  # Joining the formatted values with commas and returning the result

    def _format_value_part(self, key: str, value) -> str:
        """Format an individual value part."""
        if key == 'name':
            return f'Name: {value}'
        elif key == 'size':
            return f'Size: {self._format_size(value)}'
        elif key == 'speed':
            return f'Speed: {self._format_size(value)}/s'
        elif key == 'progress':
            return f'Progress: {value}'
        elif key == 'eta':
            return f'ETA: {value}'
        elif key == 'status':
            return f'Status: {value}'
        else:
            return f'Unknown: {key}: {value}'

    def _format_time(self, seconds: float) -> str:
        """Format a time value in seconds as a string."""
        if seconds is None:
            return 'Unknown'
        m, s = divmod(seconds, 60)
        h, m = divmod(m, 60)
        if h > 0:
            return f'{h}:{m:02d}:{s:02.2f}'
        else:
            return f'{m}:{s:02.2f}'

    def _format_size(self, bytes: int) -> str:
        """Format a size value in bytes as a string."""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if bytes < 1024:
                break
            bytes /= 1024.0
        return f'{bytes:.2f} {unit}'

    def __repr__(self):
        """Get a developer-friendly representation of the ZipCreationStatus object."""
        return (
            f'ZipCreationStatus(\n'
            f'    name={self.name},\n'
            f'    size={self.size},\n'
            f'    listener={self.listener},\n'
            f'    upload_details={self.upload_details},\n'
            f'    uid={self.uid},\n'
            f'    start_time={self.start_time},\n'
            f'    message={self.message},\n'
            f'    processed_raw={self.processed_raw},\n'
            f'    time_elapsed={self.time_elapsed},\n'
            f')'
        )  # Returning a developer-friendly string representation of the ZipCreationStatus object
