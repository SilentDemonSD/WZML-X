#!/usr/bin/env python3
from typing import Optional

from bot import LOGGER, get_client, QbTorrents, qb_listener_lock
from bot.helper.ext_utils.bot_utils import EngineStatus, MirrorStatus, get_readable_file_size, get_readable_time, sync_to_async

def get_download(client: object, tag: str) -> Optional[object]:
    try:
        return client.torrents_info(tag=tag)[0]
    except Exception as e:
        LOGGER.error(f'{e}: Qbittorrent, while getting torrent info. Tag: {tag}')
        return None

class QbittorrentStatus:
    """
    Class to represent the status of a Qbittorrent download.
    """

    def __init__(self, listener, seeding: bool = False, queued: bool = False):
        self.__client = get_client()
        self.__listener = listener
        self.upload_details = listener.upload_details
        self.__info = get_download(self.__client, f'{self.__listener.uid}')
        self.queued = queued
        self.seeding = seeding
        self.message = listener.message

    def __update(self):
        """
        Update the internal state of the object with the latest information from Qbittorrent.
        """
        new_info = get_download(self.__client, f'{self.__listener.uid}')
        if new_info is not None:
            self.__info = new_info

    def __str__(self):
        """
        Return a human-readable representation of the object.
        """
        return f"QbittorrentStatus(name={self.name()}, status={self.status()}, progress={self.progress()})"

    def progress(self):
        """
        Return the progress of the download as a percentage.
        """
        return f'{round(self.__info.progress*100, 2)}%'

    def processed_bytes(self):
        """
        Return the number of bytes that have been downloaded.
        """
        return get_readable_file_size(self.__info.downloaded)

    def speed(self):
        """
        Return the download speed in a human-readable format.
        """
        return f"{get_readable_file_size(self.__info.dlspeed)}/s"

    def name(self):
        """
        Return the name of the download.
        """
        if self.__info.state in ["metaDL", "checkingResumeData"]:
            return f"[METADATA]{self.__info.name}"
        else:
            return self.__info.name

    def size(self):
        """
        Return the size of the download in a human-readable format.
        """
        return get_readable_file_size(self.__info.size)

    def eta(self):
        """
        Return the estimated time of arrival in a human-readable format.
        """
        return get_readable_time(self.__info.eta)

    def status(self):
        """
        Return the current status of the download as a MirrorStatus object.
        """
        self.__update()
        state = self.__info.state
        if state == "queuedDL" or self.queued:
            return MirrorStatus.STATUS_QUEUEDL
        elif state == "queuedUP":
            return MirrorStatus.STATUS_QUEUEUP
        elif state in ["pausedDL", "pausedUP"]:
            return MirrorStatus.STATUS_PAUSED
        elif state in ["checkingUP", "checkingDL"]:
            return MirrorStatus.STATUS_CHECKING
        elif state in ["stalledUP", "uploading"] and self.seeding:
            return MirrorStatus.STATUS_SEEDING
        else:
            return MirrorStatus.STATUS_DOWNLOADING

    def seeders_num(self):
        """
        Return the number of seeders for the download.
        """
        return self.__info.num_seeds

    def leechers_num(self):
        """
        Return the number of leechers for the download.
        """
        return self.__info.num_leechs

    def uploaded_bytes(self):
        """
        Return the number of bytes that have been uploaded.
        """
        return get_readable_file_size(self.__info.uploaded)

    def upload_speed(self):
        """
        Return the upload speed in a human-readable format.
        """
        return f"{get_readable_file_size(self.__info.upspeed)}/s"

    def ratio(self):
        """
        Return the upload-to-download ratio.
        """
        return f"{round(self.__info.ratio, 3)}"

    def seeding_time(self):
        """
        Return the amount of time the download has been seeding.
        """
        return get_readable_time(self.__info.seeding_time)

    def download(self):
        """
        Return the download object.
        """
        return self

    def gid(self):
        """
        Return the first 12 characters of the hash.
        """
        self.__update()
        return self.__info.hash[:12]

    def hash(self):
        """
        Return the hash of the download.
        """
        self.__update()
        return self.__info.hash

    def client(self):
        """
        Return the Qbittorrent client object.
        """
        return self.__client

    def listener(self):
        """
        Return the listener object.
        """
        return self.__listener

    async def cancel_download(self):
        """
        Cancel the download and delete it from Qbittorrent.
        """
        self.__update()
        try:
            await sync_to_async(self.__client.torrents_pause, torrent_hashes=self.__info.hash)
        except Exception as e:
            LOGGER.error(f'Error pausing torrent: {e}')

        if not self.seeding:
            if self.queued:
                LOGGER.info(f'Cancelling QueueDL: {self.name()}')
                msg = 'task have been removed from queue/download'
            else:
                LOGGER.info(f"Cancelling Download: {self.__info.name}")
                msg = 'Download stopped by user!'
            await sleep(0.3)
            await self.__listener.onDownloadError(msg)

        try:
            await sync_to_async(self.__client.torrents_delete, torrent_hashes=self.__info.hash, delete_files=True)
        except Exception as e:
            LOGGER.error(f'Error deleting torrent: {e}')

        try:
            await sync_to_async(self.__client.torrents_delete_tags, tags=self.__info.tags)
        except Exception as e:
            LOGGER.error(f'Error deleting tags: {e}')

        async with qb_listener_lock:
            if self.__info.tags in QbTorrents:
                del QbTorrents[self.__info.tags]

    def eng(self):
        """
        Return the engine status.
        """
        return EngineStatus().STATUS_QB
