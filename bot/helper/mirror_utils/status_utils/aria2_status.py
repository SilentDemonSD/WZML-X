import asyncio
import datetime
from typing import Any, Callable, Dict, List, Optional

import aioaria2rpc
from bot import aria2, logger
from bot.helper.ext_utils.bot_utils import EngineStatus, MirrorStatus, get_readable_time

def memoized(maxsize=128):
    """
    A decorator for memoizing the results of a function.
    This decorator stores the results of the function in a cache dictionary,
    and returns the cached result if the function has already been called
    with the same arguments. This can improve performance for functions
    that are called multiple times with the same arguments.
    """
    cache: Dict[str, Any] = {}

    def decorator(func: Callable) -> Callable:
        async def wrapper(*args: List[Any], **kwargs: Dict[str, Any]) -> Any:
            key = str(args) + str(kwargs)
            if key not in cache:
                cache[key] = await func(*args, **kwargs)
            return cache[key]

        return wrapper

    return decorator

@memoized
async def get_download_by_gid(gid: str) -> Optional[aioaria2rpc.Download]:
    """
    Get the download object by GID.
    This function sends an RPC request to the Aria2 instance to get the download
    object with the given GID. If the RPC request fails, an error message is
    logged and None is returned.

    :param gid: The GID of the download.
    :return: The download object, or None if the RPC request fails.
    """
    try:
        return await aria2.get_download(gid)
    except aioaria2rpc.RPCError as e:
        logger.error(f'{e}: Aria2c, Error while getting torrent info')
        return None

class Aria2Status:
    """
    A class representing the status of an Aria2 download.
    This class provides methods for getting information about a download,
    such as its name, size, progress, and speed.
    """

    __slots__ = (
        '__gid', '__download', '__listener', 'upload_details', 'queued', 'start_time', 'seeding', 'message'
    )

    def __init__(self, gid: str, listener=None, seeding: bool = False, queued: bool = False):
        """
        Initialize a new Aria2Status object.
        This constructor takes a GID, an optional listener object, and optional
        flags for seeding and queued status. It initializes the object's state
        by getting the download object with the given GID.

        :param gid: The GID of the download.
        :param listener: The listener object for the download.
        :param seeding: Whether the download is in seeding mode.
        :param queued: Whether the download is in the queue.
        """
        self.__gid = gid
        self.__download = None
        self.__listener = listener
        self.upload_details = self.__listener.upload_details if self.__listener else None
        self.queued = queued
        self.start_time = None
        self.seeding = seeding
        self.message = self.__listener.message if self.__listener else None
        self.__update()

    def __update(self):
        """
        Update the internal state of the object with the latest download info.
        This method sends an RPC request to the Aria2 instance to get the latest
        information about the download.
        """
        self.__download = get_download_by_gid(self.__gid)

    @property
    def download(self):
        """
        Get the download object.
        This property returns the download object associated with the GID.
        If the download object is not available, it sends an RPC request to the
        Aria2 instance to get the latest information about the download.

        :return: The download object.
        """
        if not self.__download:
            self.__update()
        return self.__download

    @property
    def gid(self):
        """
        Get the GID of the download.
        This property returns the GID of the download.

        :return: The GID of the download.
        """
        return self.__gid

    @property
    def status_code(self):
        """
        Get the status code of the download.
        This property returns the status code of the download, which can be
        used to determine the current state of the download.

        :return: The status code of the download.
        """
        download = self.download
        return download.status if download else None

    def is_active(self):
        """
        Check if the download is currently active.
        This method returns True if the download is in a state where it is
        actively downloading or seeding, and False otherwise.

        :return: True if the download is active, False otherwise.
        """
        download = self.download
        return download.status in (1, 2, 3, 4) if download else False

    def is_completed(self):
        """
        Check if the download is completed.
        This method returns True if the download is in the completed state,
        and False otherwise.

        :return: True if the download is completed, False otherwise.
        """
        download = self.download
        return download.status == 5 if download else False

    def is_paused(self):
        """
        Check if the download is paused.
        This method returns True if the download is in the paused state,
        and False otherwise.

        :return: True if the download is paused, False otherwise.
        """
        download = self.download
        return download.status == 6 if download else False

    def is_seeding(self):
        """
        Check if the download is in seeding mode.
        This method returns True if the download is in the seeding state,
        and False otherwise.

        :return: True if the download is in seeding mode, False otherwise.
        """
        download = self.download
        return download.status == 7 if download else False

    def is_queued(self):
        """
        Check if the download is in the queue.
        This method returns True if the download is in the queue,
        and False otherwise.

        :return: True if the download is in the queue, False otherwise.
        """
        download = self.download
        return download.status == 8 if download else False

    def is_removed(self):
        """
        Check if the download has been removed from Aria2.
        This method returns True if the download object is None,
        indicating that the download has been removed from Aria2.

        :return: True if the download has been removed, False otherwise.
        """
        return self.__download is None

    def progress(self):
        """
        Get the progress of the download as a string.
        This method returns a string representing the progress of the download,
        such as "20%".

        :return: The progress of the download as a string.
        """
        download = self.download
        return download.progress_string() if download else ""

    def processed_bytes(self):
        """
        Get the number of bytes processed by the download as a string.
        This method returns a string representing the number of bytes
        processed by the download, such as "10 MB".

        :return: The number of bytes processed by the download as a string.
        """
        download = self.download
        return download.completed_length_string() if download else "0 B"

    def speed(self):
        """
        Get the download speed of the download as a string.
        This method returns a string representing the download speed of the
        download, such as "10 MB/s".

        :return: The download speed of the download as a string.
        """
        download = self.download
        return download.download_speed_string() if download else "0 B/s"

    def name(self):
        """
        Get the name of the download.
        This method returns the name of the download.

        :return: The name of the download.
        """
        download = self.download
        return download.name if download else ""

    def size(self):
        """
        Get the size of the download as a string.
        This method returns a string representing the size of the download,
        such as "10 GB".

        :return: The size of the download as a string.
        """
        download = self.download
        return download.total_length_string() if download else "0 B"

    def eta(self):
        """
        Get the estimated time of arrival of the download as a string.
        This method returns a string representing the estimated time of
        arrival of the download, such as "10 minutes".

        :return: The estimated time of arrival of the download as a string.
        """
        download = self.download
        return download.eta_string() if download else ""

    def listener(self):
        """
        Get the listener object of the download.
        This method returns the listener object associated with the download.

        :return: The listener object of the download.
        """
        return self.__listener

    def status(self):
        """
        Get the status of the download as a string.
        This method returns a string representing the status of the download,
        such as "downloading" or "seeding".

        :return: The status of the download as a string.
        """
        download = self.download
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

