import asyncio
from typing import Optional, Type, Union

from bot import LOGGER, get_client, QbTorrents
from bot.helper.ext_utils.bot_utils import EngineStatus, MirrorStatus, get_readable_file_size, get_readable_time
from bot.qbittorrentclient import QbittorrentClient

class QbittorrentStatus:
    __slots__ = (
        "__client",
        "__info",
        "__listener",
        "queued",
        "seeding",
        "message",
    )

    def __init__(
        self,
        client: QbittorrentClient,
        listener: QbittorrentClient,  # Replace typing.Any with the actual type when known
        seeding: bool = False,
        queued: bool = False,
    ) -> None:
        """
        Initialize the QbittorrentStatus object.

        :param client: The QbittorrentClient object.
        :param listener: The listener QbittorrentClient object.
        :param seeding: Whether the torrent is in seeding state.
        :param queued: Whether the torrent is in queued state.
        """
        self.__client = client
        self.__listener = listener
        self.__info = self.__client.torrents_info(f'{self.__listener.uid}')
        self.queued = queued
        self.seeding = seeding
        self.message = listener.message

    @property
    def progress(self) -> str:
        """
        Get the progress of the torrent as a string.

        :return: The progress of the torrent.
        """
        return f'{round(self.__info.progress*100, 2)}%'

    @property
    def processed_bytes(self) -> str:
        """
        Get the processed bytes of the torrent as a string.

        :return: The processed bytes of the torrent.
        """
        return get_readable_file_size(self.__info.downloaded)

    @property
    def speed(self) -> str:
        """
        Get the speed of the torrent as a string.

        :return: The speed of the torrent.
        """
        return f"{get_readable_file_size(self.__info.dlspeed)}/s"

    @property
    def name(self) -> str:
        """
        Get the name of the torrent.

        :return: The name of the torrent.
        """
        if self.__info.state in ["metaDL", "checkingResumeData"]:
            return f"[METADATA]{self.__info.name}"
        else:
            return self.__info.name

    @property
    def size(self) -> str:
        """
        Get the size of the torrent as a string.

        :return: The size of the torrent.
        """
        return get_readable_file_size(self.__info.size)

    @property
    def eta(self) -> str:
        """
        Get the ETA of the torrent as a string.

        :return: The ETA of the torrent.
        """
        return get_readable_time(self.__info.eta)

    @property
    def status(self) -> str:
        """
        Get the status of the torrent.

        :return: The status of the torrent.
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
        Get the number of seeders of the torrent.

        :return: The number of seeders of the torrent.
        """
        return self.__info.num_seeds

    @property
    def leechers_num(self) -> int:
        """
        Get the number of leechers of the torrent.

        :return: The number of leechers of the torrent.
        """
        return self.__info.num_leechs

    @property
    def uploaded_bytes(self) -> str:
        """
        Get the uploaded bytes of the torrent as a string.

        :return: The uploaded bytes of the torrent.
        """
        return get_readable_file_size(self.__info.uploaded)

    @property
    def upload_speed(self) -> str:
        """
        Get the upload speed of the torrent as a string.

        :return: The upload speed of the torrent.
        """
        return f"{get_readable_file_size(self.__info.upspeed)}/s"

    @property
    def ratio(self) -> str:
        """
        Get the ratio of the torrent.

        :return: The ratio of the torrent.
        """
        return f"{round(self.__info.ratio, 3)}"

    @property
    def seeding_time(self) -> str:
        """
        Get the seeding time of the torrent as a string.

        :return: The seeding time of the torrent.
        """
        return get_readable_time(self.__info.seeding_time)

    async def __aenter__(self) -> "QbittorrentStatus":
        """
        Enter the context manager.

        :return: The QbittorrentStatus object.
        """
        return self

    async def __aexit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc: Optional[BaseException],
        tb: Optional[traceback.TracebackType],
    ) -> None:
        """
        Exit the context manager.

        :param exc_type: The exception type.
        :param exc: The exception object.
        :param tb: The traceback object.
        """
        pass

    async def cancel_download(self) -> Union[Coroutine, None]:
        """
        Cancel the download of the torrent.

        :return: A coroutine object or None.
        """
        self.__update()
        if self.__info is not None and self.__info.state not in ["downloading", "stalledDL"]:
            await self.__client.torrents_pause(torrent_hashes=self.__info.hash)
            if not self.seeding:
                if self.queued:
                    LOGGER.info(f'Cancelling QueueDL: {self.name()}')
                    msg = 'task have been removed from queue/download'
                else:
                    LOGGER.info(f"Cancelling Download: {self.__info.name}")
                    msg = 'Download stopped by user!'
                await asyncio.sleep(0.5)
                await self.__listener.onDownloadError(msg)
                await self.__client.torrents_delete(torrent_hashes=self.__info.hash, delete_files=True)
                await self.__client.torrents_delete_tags(tags=self.__info.tags)
                async with qb_listener_lock:
                    if self.__info.tags in QbTorrents:
                        del QbTorrents[self.__info.tags]

    def __update(self) -> None:
        """
        Update the info object.
        """
        new_info = self.__client.torrents_info(f'{self.__listener.uid}')
        if new_info is not None:
            self.__info = new_info

    @final
    def download(self) -> "QbittorrentStatus":
        """
        Download the torrent.

        :return: The QbittorrentStatus object.
        """
        return self

    @final
    def gid(self) -> str:
        """
        Get the GID of the torrent.

        :return: The GID of the torrent.
        """
        self.__update()
        return self.__info.hash[:12]

    @final
    def hash(self) -> str:
        """
        Get the hash of the torrent.

        :return: The hash of the torrent.
        """
        self.__update()
        return self.__info.hash

    @final
    async def client(self) -> asyncio.AbstractContextManager:
        """
        Get the client object.

        :return: The client object.
        """
        if self.__client is not None:
            async with self.__client as client:
                yield client
        else:
            raise RuntimeError("Client object is not initialized.")

    def __repr__(self) -> str:
        """
        Get the string representation of the object.

        :return: The string representation of the object.
        """
        return f"<QbittorrentStatus(name='{self.name}', progress='{self.progress}', status='{self.status}')>"
