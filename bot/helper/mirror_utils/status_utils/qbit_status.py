import asyncio
import typing

from bot import LOGGER, get_client, QbTorrents
from bot.helper.ext_utils.bot_utils import EngineStatus, MirrorStatus, get_readable_file_size, get_readable_time

def get_download(client, tag: str) -> typing.Optional[typing.Dict]:
    """
    Fetches the download information for the given tag.

    Args:
    client (object): Qbittorrent client object.
    tag (str): Tag to fetch the download information for.

    Returns:
    download_info (object or None): Download information as an object if found, None otherwise.
    """
    try:
        return client.torrents_info(tag=tag)[0]
    except Exception as e:
        LOGGER.error(f'{e}: Qbittorrent, while getting torrent info. Tag: {tag}')
        return None

class QbittorrentStatus:
    """
    Class to represent the status of a Qbittorrent download.

    Attributes:
    listener (object): Listener object associated with the download.
    seeding (bool): Flag to indicate if the download is in seeding state.
    queued (bool): Flag to indicate if the download is queued.
    upload_details (dict): Details of the upload.
    __info (object): Information about the download.
    """

    def __init__(self, listener, seeding: bool = False, queued: bool = False):
        """
        Initializes the QbittorrentStatus class with the given listener, seeding and queued flags.

        Args:
        listener (object): Listener object associated with the download.
        seeding (bool, optional): Flag to indicate if the download is in seeding state. Defaults to False.
        queued (bool, optional): Flag to indicate if the download is queued. Defaults to False.
        """
        self.__client = get_client()
        self.__listener = listener
        self.upload_details = listener.upload_details
        self.__info = get_download(self.__client, f'{self.__listener.uid}')
        self.queued = queued
        self.seeding = seeding
        self.message = listener.message

    def __update(self):
        """
        Updates the internal download information.
        """
        new_info = get_download(self.__client, f'{self.__listener.uid}')
        if new_info is not None:
            self.__info = new_info

    # Properties with getter methods

    @property
    def progress(self) -> str:
        """
        Returns:
        progress (str): Progress of the download as a percentage.
        """
        return f'{round(self.__info.progress*100, 2)}%'

    @property
    def processed_bytes(self) -> str:
        """
        Returns:
        processed_bytes (str): Downloaded bytes in a human-readable format.
        """
        return get_readable_file_size(self.__info.downloaded)

    @property
    def speed(self) -> str:
        """
        Returns:
        speed (str): Download speed in a human-readable format.
        """
        return f"{get_readable_file_size(self.__info.dlspeed)}/s"

    @property
    def name(self) -> str:
        """
        Returns:
        name (str): Name of the download.
        """
        if self.__info.state in ["metaDL", "checkingResumeData"]:
            return f"[METADATA]{self.__info.name}"
        else:
            return self.__info.name

    @property
    def size(self) -> str:
        """
        Returns:
        size (str): Total size of the download in a human-readable format.
        """
        return get_readable_file_size(self.__info.size)

    @property
    def eta(self) -> str:
        """
        Returns:
        eta (str): Estimated time to completion in a human-readable format.
        """
        return get_readable_time(self.__info.eta)

    @property
    def status(self) -> str:
        """
        Returns:
        status (str): Status of the download.
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

    @property
    def seeders_num(self) -> int:
        """
        Returns:
        seeders_num (int): Number of seeders for the download.
        """
        return self.__info.num_seeds

    @property
    def leechers_num(self) -> int:
        """
        Returns:
        leechers_num (int): Number of leechers for the download.
        """
        return self.__info.num_leechs

    @property
    def uploaded_bytes(self) -> str:
        """
        Returns:
        uploaded_bytes (str): Uploaded bytes in a human-readable format.
        """
        return get_readable_file_size(self.__info.uploaded)

    @property
    def upload_speed(self) -> str:
        """
        Returns:
        upload_speed (str): Upload speed in a human-readable format.
        """
        return f"{get_readable_file_size(self.__info.upspeed)}/s"

    @property
    def ratio(self) -> str:
        """
        Returns:
        ratio (str): Ratio of upload to download.
        """
        return f"{round(self.__info.ratio, 3)}"

    @property
    def seeding_time(self) -> str:
        """
        Returns:
        seeding_time (str): Seeding time in a human-readable format.
        """
        return get_readable_time(self.__info.seeding_time)

    # Methods

    def download(self) -> 'QbittorrentStatus':
        """
        Returns:
        self: QbittorrentStatus object itself for chaining method calls.
        """
        return self

    def gid(self) -> str:
        """
        Returns:
        gid (str): First 12 characters of the hash.
        """
        self.__update()
        return self.__info.hash[:12]

    def hash(self) -> str:
        """
        Returns:
        hash (str): Hash of the download.
        """
        self.__update()
        return self.__info.hash

    def client(self) -> object:
        """
        Returns:
        client (object): Qbittorrent client object.
        """
        return self.__client

    def listener(self) -> object:
        """
        Returns:
        listener (object): Listener object associated with the download.
        """
        return self.__listener

    async def cancel_download(self) -> typing.Coroutine:
        """
        Cancels the download and deletes the associated files and tags.
        """
        self.__update()
        await sync_to_async(self.__client.torrents_pause, torrent_hashes=self.__info.hash)
        if not self.seeding:
            if self.queued:
                LOGGER.info(f'Cancelling QueueDL: {self.name()}')
                msg = 'task have been removed from queue/download'
            else:
                LOGGER.info(f"Cancelling Download: {self.__info.name}")
                msg = 'Download stopped by user!'
            await asyncio.sleep(0.3)
            await self.__listener.onDownloadError(msg)
            await sync_to_async(self.__client.torrents_delete, torrent_hashes=self.__info.hash, delete_files=True)
            await sync_to_async(self.__client.torrents_delete_tags, tags=self.__info.tags)
            async with qb_listener_lock:
                if self.__info.tags in QbTorrents:
                    del QbTorrents[self.__info.tags]

