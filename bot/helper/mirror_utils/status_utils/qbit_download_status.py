from time import sleep
from typing import Optional

from bot import LOGGER, get_client
from bot.helper.ext_utils.bot_utils import MirrorStatus, get_readable_file_size, get_readable_time, EngineStatus

def get_download(client, hash_: str) -> Optional[dict]:
    try:
        return client.torrents_info(torrent_hashes=[hash_])[0]
    except Exception as e:
        LOGGER.error(f'{e}: Qbittorrent, Error while getting torrent info')
        return None

class QbDownloadStatus:

    def __init__(self, listener, hash_, seeding: bool = False):
        self.__client = get_client()
        self.__listener = listener
        self.__hash = hash_
        self.__info = get_download(self.__client, self.__hash)
        self.seeding = seeding
        self.message = listener.message

    def progress(self) -> str:
        """
        Calculates the progress of the mirror (upload or download)
        :return: returns progress in percentage
        """
        if self.__info is None:
            return '0%'
        return f'{round(self.__info.progress*100, 2)}%'

    def size_raw(self) -> int:
        """
        Gets total size of the mirror file/folder
        :return: total size of mirror
        """
        if self.__info is None:
            return 0
        return self.__info.size

    def processed_bytes(self) -> int:
        if self.__info is None:
            return 0
        return self.__info.downloaded

    def speed(self) -> str:
        """
        Gets the download/upload speed of the mirror
        :return: returns speed in a human-readable format
        """
        if self.__info is None:
            return '0 B/s'
        return f"{get_readable_file_size(self.__info.dlspeed)}/s" if self.__info.state in ["downloading", "stalledDL"] else "0 B/s"

    def name(self) -> str:
        """
        Gets the name of the mirror
        :return: returns the name of the mirror
        """
        if self.__info is None:
            return ''
        if self.__info.state in ["metaDL", "checkingResumeData"]:
            return f"[METADATA]{self.__info.name}"
        else:
            return self.__info.name

    def size(self) -> str:
        """
        Gets the total size of the mirror in a human-readable format
        :return: returns the total size of the mirror
        """
        if self.__info is None:
            return '0 B'
        return get_readable_file_size(self.__info.size)

    def eta(self) -> str:
        """
        Gets the estimated time of arrival of the mirror
        :return: returns the estimated time of arrival in a human-readable format
        """
        if self.__info is None or self.__info.state not in ["downloading", "stalledDL"]:
            return '0 s'
        return get_readable_time(self.__info.eta)

    def status(self) -> MirrorStatus:
        """
        Gets the status of the mirror
        :return: returns the status of the mirror
        """
        if self.__info is None:
            return MirrorStatus.STATUS_UNKNOWN
        download = self.__info.state
        if download in ["queuedDL", "queuedUP"]:
            return MirrorStatus.STATUS_QUEUEDL
        elif download in ["pausedDL", "pausedUP"]:
            return MirrorStatus.STATUS_PAUSED
        elif download in ["checkingUP", "checkingDL"]:
            return MirrorStatus.STATUS_CHECKING
        elif download in ["stalledUP", "uploading"] and self.seeding:
            return MirrorStatus.STATUS_SEEDING
        else:
            return MirrorStatus.STATUS_DOWNLOADING

    def seeders_num(self) -> int:
        """
        Gets the number of seeders for the mirror
        :return: returns the number of seeders for the mirror
        """
        if self.__info is None:
            return 0
        return self.__info.num_seeds

    def leechers_num(self) -> int:
        """
        Gets the number of leechers for the mirror
        :return: returns the number of leechers for the mirror
        """
        if self.__info is None:
            return 0
        return self.__info.num_leechs

    def uploaded_bytes(self) -> str:
        """
        Gets the number of bytes uploaded for the mirror
        :return: returns the number of bytes uploaded for the mirror in a human-readable format
        """
        if self.__info is None:
            return '0 B'
        return f"{get_readable_file_size(self.__info.uploaded)}"

    def upload_speed(self) -> str:
        """
        Gets the upload speed for the mirror
        :return: returns the upload speed for the mirror in a human-readable format
        """
        if self.__info is None:
            return '0 B/s'
        return f"{get_readable_file_size(self.__info.upspeed)}/s" if self.__info.state in ["uploading", "stalledUP"] else "0 B/s"

    def ratio(self) -> str:
        """
        Gets the upload/download ratio for the mirror
        :return: returns the upload/download ratio for the mirror
        """
        if self.__info is None:
            return '0.000'
        return f"{round(self.__info.ratio, 3)}"

    def seeding_time(self) -> str:
        """
        Gets the time the mirror has been seeding
        :return: returns the time the mirror has been seeding in a human-readable format
        """
        if self.__info is None:
            return '0 s'
        return f"{get_readable_time(self.__info.seeding_time)}"

    def download(self):
        """
        Returns the QbDownloadStatus object itself
        :return: returns the QbDownloadStatus object
        """
        return self

    def gid(self) -> str:
        """
        Gets the ID of the mirror
        :return: returns the ID of the mirror
        """
        if self.__info is None:
            return ''
        return self.__hash[:12]

    def hash(self) -> str:
        """
        Gets the hash of the mirror
        :return: returns the hash of the mirror
        """
        if self.__info is None:
            return ''
        return self.__hash

    def client(self):
        """
        Gets the Qbittorrent client
        :return: returns the Qbittorrent client
        """
        return self.__client

    def listener(self):
        """
        Gets the listener object
        :return: returns the listener object
        """
        return self.__listener

    def eng(self) -> EngineStatus:
        """
        Gets the engine status
        :return: returns the engine status
        """
        return EngineStatus.STATUS_QB

    def cancel_download(self):
        """
        Cancels the download of the mirror
        """
        if self.__info is not None:
            self.__client.torrents_pause(torrent_hashes=[self.__hash])
            if self.status() != MirrorStatus.STATUS_SEEDING:
                LOGGER.info(f"Cancelling Download: {self.__info.name}")
                sleep(0.3)
                self.__listener.onDownloadError('Download stopped by user!')
                self.__client.torrents_delete(torrent_hashes=[self.__hash], delete_files=True)

    def __str__(self):
        """
        Gets a human-readable representation of the QbDownloadStatus object
        :return: returns a human-readable representation of the QbDownloadStatus object
        """
        if self.__info is None:
            return 'QbDownloadStatus(hash=None, name=None, status=None, progress=None, size=None, processed_bytes=None, speed=None, eta=None, seeders_num=None, leechers_num=None, uploaded_bytes=None, upload_speed=None, ratio=None, seeding_time=None)'
        return f'QbDownloadStatus(hash="{self.__hash}", name="{self.__info.name}", status="{self.status()}", progress="{self.progress()}", size="{self.size()}", processed_bytes="{self.processed_bytes()}", speed="{self.speed()}", eta="{self.eta()}", seeders_num="{self.seeders_num()}", leechers_num="{self.leechers_num()}", uploaded_bytes="{self.uploaded_bytes()}", upload_speed="{self.upload_speed()}", ratio="{self.ratio()}", seeding_time="{self.seeding_time()}")'
