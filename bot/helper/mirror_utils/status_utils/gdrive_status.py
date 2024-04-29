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
        size = size // 1024
    return f"{size:.2f} {unit}"

def get_readable_time(seconds: int) -> str:
    """
    Converts a time in seconds to a human-readable format.

    :param seconds: The time in seconds.
    :return: The time in a human-readable format.
    """
    time_parts = []
    time_dict = {
        'days': (86400, 'day'),
        'hours': (3600, 'hour'),
        'minutes': (60, 'minute'),
        'seconds': (1, 'second')
    }

    for unit, (divisor, name) in time_dict.items():
        value = seconds // divisor
        if value > 0:
            time_parts.append(f"{value} {name}{('s' if value > 1 else '')}")
            seconds -= value * divisor

    return ', '.join(time_parts)
