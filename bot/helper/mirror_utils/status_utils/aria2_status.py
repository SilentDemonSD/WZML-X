import asyncio
import datetime
from typing import Any

import aioaria2rpc
from bot import aria2, logger
from bot.helper.ext_utils.bot_utils import EngineStatus, MirrorStatus, get_readable_time

def memoized(maxsize=128):
    """
    A decorator for memoizing the results of a function.
    """
    cache = {}

    def decorator(func):
        def wrapper(*args, **kwargs):
            key = str(args) + str(kwargs)
            if key not in cache:
                cache[key] = func(*args, **kwargs)
            return cache[key]

        return wrapper

    return decorator

def get_download_by_gid(gid: str) -> aioaria2rpc.Download:
    """
    Get the download object by GID.

    :param gid: The GID of the download.
    :return: The download object.
    """
    try:
        return aria2.get_download(gid)
    except aioaria2rpc.RPCError as e:
        logger.error(f'{e}: Aria2c, Error while getting torrent info')
        return None

class Aria2Status:
    """
    A class representing the status of an Aria2 download.
    """

    __slots__ = (
        '__gid', '__download', '__listener', 'upload_details', 'queued', 'start_time', 'seeding', 'message'
    )

    def __init__(self, gid: str, listener, seeding: bool = False, queued: bool = False):
        """
        Initialize a new Aria2Status object.

        :param gid: The GID of the download.
        :param listener: The listener object for the download.
        :param seeding: Whether the download is in seeding mode.
        :param queued: Whether the download is in the queue.
        """
        self.__gid = gid
        self.__download = get_download_by_gid(gid)
        self.__listener = listener
        self.upload_details = self.__listener.upload_details if self.__listener else None
        self.queued = queued
        self.start_time = datetime.datetime.now() if self.__download else None
        self.seeding = seeding
        self.message = self.__listener.message if self.__listener else None

    def __update(self):
        """
        Update the internal state of the object with the latest download info.
        """
        self.__download = get_download_by_gid(self.__gid)

    @memoized
    def __download_info(self):
        """
        Get the download object and update the internal state.

        :return: The download object.
        """
        self.__update()
        return self.__download

    def __str__(self):
        """
        Return a string representation of the object.

        :return: A string representation of the object.
        """
        return f"Aria2Status(gid={self.gid}, status={self.status}, progress={self.progress})"

    def __repr__(self):
        """
        Return a more informative string representation of the object.

        :return: A string representation of the object.
        """
        return (
            f"<Aria2Status gid={self.gid} status={self.status} progress={self.progress}"
            f" queued={self.queued} seeding={self.seeding}>"
        )

    @property
    def download(self):
        """
        Get the download object.

        :return: The download object.
        """
        return self.__download_info()

    @property
    def gid(self):
        """
        Get the GID of the download.

        :return: The GID of the download.
        """
        return self.__gid

    @property
    def status_code(self):
        """
        Get the status code of the download.

        :return: The status code of the download.
        """
        download = self.__download_info()
        return download.status if download else None

    def is_active(self):
        """
        Check if the download is currently active.

        :return: True if the download is active, False otherwise.
        """
        download = self.__download_info()
        return download.status in (1, 2, 3, 4) if download else False

    def is_completed(self):
        """
        Check if the download is completed.

        :return: True if the download is completed, False otherwise.
        """
        download = self.__download_info()
        return download.status == 5 if download else False

    def is_paused(self):
        """
        Check if the download is paused.

        :return: True if the download is paused, False otherwise.
        """
        download = self.__download_info()
        return download.status == 6 if download else False

    def is_seeding(self):
        """
        Check if the download is in seeding mode.

        :return: True if the download is in seeding mode, False otherwise.
        """
        download = self.__download_info()
        return download.status == 7 if download else False

    def is_queued(self):
        """
        Check if the download is in the queue.

        :return: True if the download is in the queue, False otherwise.
        """
        download = self.__download_info()
        return download.status == 8 if download else False

    def is_removed(self):
        """
        Check if the download has been removed from Aria2.

        :return: True if the download has been removed, False otherwise.
        """
        return self.__download is None

    def progress(self):
        """
        Get the progress of the download as a string.

        :return: The progress of the download as a string.
        """
        download = self.__download_info()
        return download.progress_string() if download else ""

    def processed_bytes(self):
        """
        Get the number of bytes processed by the download as a string.

        :return: The number of bytes processed by the download as a string.
        """
        download = self.__download_info()
        return download.completed_length_string() if download else "0 B"

    def speed(self):
        """
        Get the download speed of the download as a string.

        :return: The download speed of the download as a string.
        """
        download = self.__download_info()
        return download.download_speed_string() if download else "0 B/s"

    def name(self):
        """
        Get the name of the download.

        :return: The name of the download.
        """
        download = self.__download_info()
        return download.name if download else ""

    def size(self):
        """
        Get the size of the download as a string.

        :return: The size of the download as a string.
        """
        download = self.__download_info()
        return download.total_length_string() if download else "0 B"

    def eta(self):
        """
        Get the estimated time of arrival of the download as a string.

        :return: The estimated time of arrival of the download as a string.
        """
        download = self.__download_info()
        return download.eta_string() if download else ""

    def listener(self):
        """
        Get the listener object of the download.

        :return: The listener object of the download.
        """
        return self.__listener

    def status(self):
        """
        Get the status of the download as a string.

        :return: The status of the download as a string.
        """
        download = self.__download_info()
        if download is None:
            return ""

        if download.is_waiting or self.queued:
            if self.seeding:
                return MirrorStatus.STATUS_QUEUEUP
            else:
                return MirrorStatus.STATUS_QUEUEDL
        elif download.is_paused:
            return MirrorStatus.STATUS_PAUSED
        elif download.seeder and self.seeding:
            return MirrorStatus.STATUS_SEEDING
        else:
            return MirrorStatus.STATUS_DOWNLOADING

    def seeders_num(self):
        """
        Get the number of seeders of the download.

        :return: The number of seeders of the download.
        """
        download = self.__download_info()
        return download.num_seeders if download else 0

    def leechers_num(self):
        """
        Get the number of leechers of the download.

        :return: The number of leechers of the download.
        """
        download = self.__download_info()
        return download.connections if download else 0

    def uploaded_bytes(self):
        """
        Get the number of bytes uploaded by the download as a string.

        :return: The number of bytes uploaded by the download as a string.
        """
        download = self.__download_info()
        return download.upload_length_string() if download else "0 B"

    def upload_speed(self):
        """
        Get the upload speed of the download as a string.

        :return: The upload speed of the download as a string.
        """
        download = self.__download_info()
        return download.upload_speed_string() if download else "0 B/s"

    def ratio(self):
        """
        Get the upload/download ratio of the download as a string.

        :return: The upload/download ratio of the download as a string.
        """
        download = self.__download_info()
        if not download:
            return "0.00"
        return f"{round(download.upload_length / download.completed_length, 3)}"

    def seeding_time(self):
        """
        Get the seeding time of the download as a string.

        :return: The seeding time of the download as a string.
        """
        return get_readable_time(
