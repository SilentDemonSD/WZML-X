#!/usr/bin/env python3

"""
This module contains utility functions for converting file sizes and times to human-readable formats.
"""

def get_readable_file_size(size: int) -> str:
    """
    Converts a file size in bytes to a human-readable format.

    :param size: The file size in bytes.
    :return: The file size in a human-readable format.
    """
    units = ['B', 'KB', 'MB', 'GB', 'TB']
    for i, unit in enumerate(units):
        if size < 1024:
            break
        size /= 1024.0
    return f"{size:.2f} {unit}"

def get_readable_time(seconds: int) -> str:
    """
    Converts a time in seconds to a human-readable format.

    :param seconds: The time in seconds.
    :return: The time in a human-readable format.
    """
    minutes, seconds = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    days, hours = divmod(hours, 24)
    if days > 0:
        return f"{days} days, {hours} hours, {minutes} minutes, {seconds} seconds"
    elif hours > 0:
        return f"{hours} hours, {minutes} minutes, {seconds} seconds"
    elif minutes > 0:
        return f"{minutes} minutes, {seconds} seconds"
    else:
        return f"{seconds} seconds"
