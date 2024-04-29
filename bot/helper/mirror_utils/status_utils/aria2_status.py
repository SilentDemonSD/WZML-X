#!/usr/bin/env python3
from typing import Optional

from time import time, sleep

from bot import aria2, LOGGER
from bot.helper.ext_utils.bot_utils import EngineStatus, MirrorStatus, get_readable_time, sync_to_async

def get_download(gid) -> Optional[object]:
    try:
        return aria2.get_download(gid)
    except Exception as e:
        LOGGER.error(f'{e}: Aria2c, Error while getting torrent info')
        return None

class Aria2Status:
    """
    A class representing the status of an Aria2 download.
    """

    def __init__(self, gid: str, listener, seeding: bool = False, queued: bool = False):
        """
        Initialize a new Aria2Status object.

        :param gid: The GID of the download.
        :param listener: The listener object for the download.
        :param seeding: Whether the download is in seeding mode.
        :param queued: Whether the download is in the queue.
        """
        self.__gid = gid
        self.__download = get_download(gid)
        self.__listener = listener
        self.upload_details = self.__listener.upload_details if self.__listener else None
        self.queued = queued
        self.start_time = 0
        self.seeding = seeding
        self.message = self.__listener.message if self.__listener else None

    def __update(self):
        """
        Update the internal state of the object with the latest download info.
        """
        if self.__download is None:
            return
        self.__download = get_download(self.__gid) if self.__download is None else self.__download.live
        if self.__download.followed_by_ids:
            self.__gid = self.__download.followed_by_ids[0]
            self.__download = get_download(self.__gid)

    def __str__(self):
        """
        Return a string representation of the object.

        :return: A string representation of the object.
        """
        return f"Aria2Status(gid={self.gid()}, status={self.status()}, progress={self.progress()})"

    @property
    def download(self):
        """
        Get the download object.

        :return: The download object.
        """
        self.__update()
        return self.__download

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
        self.__update()
        return self.__download.status

    @property
    def is_active(self):
        """
        Check if the download is currently active.

        :return: True if the download is active, False otherwise.
        """
        return self.status_code in (1, 2, 3, 4)

    @property
    def is_completed(self):
        """
        Check if the download is completed.

        :return: True if the download is completed, False otherwise.
        """
        return self.status_code == 5

    @property
    def is_paused(self):
        """
        Check if the download is paused.

        :return: True if the download is paused, False otherwise.
        """
        return self.status_code == 6

    @property
    def is_seeding(self):
        """
        Check if the download is in seeding mode.

        :return: True if the download is in seeding mode, False otherwise.
        """
        return self.status_code == 7

    @property
    def is_queued(self):
        """
        Check if the download is in the queue.

        :return: True if the download is in the queue, False otherwise.
        """
        return self.status_code == 8

    @property
    def is_removed(self):
        """
        Check if the download has been removed from Aria2.

        :return: True if the download has been removed, False otherwise.
        """
        return self.__download is None

    def __update(self):
        """
        Update the internal state of the object with the latest download info.
        """
        if self.__download is None:
            return
        self.__download = get_download(self.__gid) if self.__download is None else self.__download.live
        if self.__download.followed_by_ids:
            self.__gid = self.__download.followed_by_ids[0]
            self.__download = get_download(self.__gid)

    def __del__(self):
        """
        Gracefully handle the removal of the download from Aria2 when the object is deleted.
        """
        if not self.is_removed and self.__download is not None:
            aria2.remove(self.__download, force=True, files=True)

    def progress(self):
        """
        Get the progress of the download as a string.

        :return: The progress of the download as a string.
        """
        self.__update()
        return self.__download.progress_string()

    def processed_bytes(self):
        """
        Get the number of bytes processed by the download as a string.

        :return: The number of bytes processed by the download as a string.
        """
        return self.__download.completed_length_string()

    def speed(self):
        """
        Get the download speed of the download as a string.

        :return: The download speed of the download as a string.
        """
        return self.__download.download_speed_string()

    def name(self):
        """
        Get the name of the download.

        :return: The name of the download.
        """
        return self.__download.name

    def size(self):
        """
        Get the size of the download as a string.

        :return: The size of the download as a string.
        """
        return self.__download.total_length_string()

    def eta(self):
        """
        Get the estimated time of arrival of the download as a string.

        :return: The estimated time of arrival of the download as a string.
        """
        return self.__download.eta_string()

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
        self.__update()
        if self.__download.is_waiting or self.queued:
            if self.seeding:
                return MirrorStatus.STATUS_QUEUEUP
            else:
                return MirrorStatus.STATUS_QUEUEDL
        elif self.__download.is_paused:
            return MirrorStatus.STATUS_PAUSED
        elif self.__download.seeder and self.seeding:
            return MirrorStatus.STATUS_SEEDING
        else:
            return MirrorStatus.STATUS_DOWNLOADING

    def seeders_num(self):
        """
        Get the number of seeders of the download.

        :return: The number of seeders of the download.
        """
        return self.__download.num_seeders

    def leechers_num(self):
        """
        Get the number of leechers of the download.

        :return: The number of leechers of the download.
        """
        return self.__download.connections

    def uploaded_bytes(self):
        """
        Get the number of bytes uploaded by the download as a string.

        :return: The number of bytes uploaded by the download as a string.
        """
        return self.__download.upload_length_string()

    def upload_speed(self):
        """
        Get the upload speed of the download as a string.

        :return: The upload speed of the download as a string.
        """
        self.__update()
        return self.__download.upload_speed_string()

    def ratio(self):
        """
        Get the upload/download ratio of the download as a string.

        :return: The upload/download ratio of the download as a string.
        """
        return f"{round(self.__download.upload_length / self.__download.completed_length, 3)}"

    def seeding_time(self):
        """
        Get the seeding time of the download as a string.

        :return: The seeding time of the download as a string.
        """
        return get_readable_time(time() - self.start_time)

    @staticmethod
    def get_readable_time(seconds):
        """
        Get a human-readable string representation of a number of seconds.

        :param seconds: The number of seconds to convert to a string.
        :return: A human-readable string representation of the number of seconds.
        """
        minutes, seconds = divmod(int(seconds), 60)
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

    @classmethod
    def Eng(cls):
        """
        Get the engine status of the download.

        :return: The engine status of the download.
        """
        return EngineStatus().STATUS_ARIA

    async def cancel_download(self):
        """
        Cancel the download.
        """
        self.__update()
        if self.__download is None:
            return
        if self.__download.seeder and self.seeding:
            LOGGER.info(f"Cancelling Seed: {self.name()}")
            await self.__listener.onUploadError(f"Seeding stopped with Ratio: {self.ratio()} and Time: {self.seeding_time()}")
            await sync_to_async(aria2.remove, [self.__download], force=True, files=True)
        elif downloads := self.__download.followed_by:
            LOGGER.info(f"Cancelling Download: {self.name()}")
            await self.__listener.onDownloadError('Download cancelled by user!')
            downloads.append(self.__download)
            await sync_to_async(aria2.remove, downloads, force=True, files=True)
        else:
            if self.queued:
                LOGGER.info(f'Cancelling QueueDl: {self.name()}')
                msg = 'task have been removed from queue/download'
            else:
                LOGGER.info(f"Cancelling Download: {self.name()}")
                msg = 'Download stopped by user!'
            await self.__listener.onDownloadError(msg)
            await sync_to_async(aria2.remove, [self.__download], force=True, files=True)
