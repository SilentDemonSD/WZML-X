import asyncio
import typing

from bot import LOGGER, get_client, QbTorrents
from bot.helper.ext_utils.bot_utils import EngineStatus, MirrorStatus, get_readable_file_size, get_readable_time

class QbittorrentStatus:
    def __init__(
        self,
        listener,
        seeding: bool = False,
        queued: bool = False,
    ) -> None:
        self.__client = get_client()
        self.__listener = listener
        self.__info = get_download(self.__client, f'{self.__listener.uid}')
        self.queued = queued
        self.seeding = seeding
        self.message = listener.message

    @property
    def progress(self) -> str:
        return f'{round(self.__info.progress*100, 2)}%'

    @property
    def processed_bytes(self) -> str:
        return get_readable_file_size(self.__info.downloaded)

    @property
    def speed(self) -> str:
        return f"{get_readable_file_size(self.__info.dlspeed)}/s"

    @property
    def name(self) -> str:
        if self.__info.state in ["metaDL", "checkingResumeData"]:
            return f"[METADATA]{self.__info.name}"
        else:
            return self.__info.name

    @property
    def size(self) -> str:
        return get_readable_file_size(self.__info.size)

    @property
    def eta(self) -> str:
        return get_readable_time(self.__info.eta)

    @property
    def status(self) -> str:
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
        return self.__info.num_seeds

    @property
    def leechers_num(self) -> int:
        return self.__info.num_leechs

    @property
    def uploaded_bytes(self) -> str:
        return get_readable_file_size(self.__info.uploaded)

    @property
    def upload_speed(self) -> str:
        return f"{get_readable_file_size(self.__info.upspeed)}/s"

    @property
    def ratio(self) -> str:
        return f"{round(self.__info.ratio, 3)}"

    @property
    def seeding_time(self) -> str:
        return get_readable_time(self.__info.seeding_time)

    async def __aenter__(self) -> "QbittorrentStatus":
        return self

    async def __aexit__(
        self,
        exc_type: typing.Optional[typing.Type[BaseException]],
        exc: typing.Optional[BaseException],
        tb: typing.Optional[traceback.TracebackType],
    ) -> None:
        pass

    async def cancel_download(self) -> typing.Coroutine:
        self.__update()
        await self.__client.torrents_pause(torrent_hashes=self.__info.hash)
        if not self.seeding:
            if self.queued:
                LOGGER.info(f'Cancelling QueueDL: {self.name()}')
                msg = 'task have been removed from queue/download'
            else:
                LOGGER.info(f"Cancelling Download: {self.__info.name}")
                msg = 'Download stopped by user!'
            await asyncio.sleep(0.3)
            await self.__listener.onDownloadError(msg)
            await self.__client.torrents_delete(torrent_hashes=self.__info.hash, delete_files=True)
            await self.__client.torrents_delete_tags(tags=self.__info.tags)
            async with qb_listener_lock:
                if self.__info.tags in QbTorrents:
                    del QbTorrents[self.__info.tags]

    async def __update(self) -> None:
        new_info = get_download(self.__client, f'{self.__listener.uid}')
        if new_info is not None:
            self.__info = new_info

    @final
    def download(self) -> "QbittorrentStatus":
        return self

    @final
    def gid(self) -> str:
        self.__update()
        return self.__info.hash[:12]

    @final
    def hash(self) -> str:
        self.__update()
        return self.__info.hash

    @final
    async def client(self) -> asyncio.AbstractContextManager:
        async with self.__client as client:
            yield client
