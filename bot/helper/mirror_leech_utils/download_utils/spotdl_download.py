from logging import getLogger
from os import path as ospath, stat, walk as oswalk, getcwd, chdir, makedirs
from secrets import token_hex

from .... import task_dict_lock, task_dict
from ....core.config_manager import BinConfig
from ...ext_utils.bot_utils import sync_to_async
from .yt_dlp_download import get_cookie_file
from ...ext_utils.task_manager import (
    check_running_tasks,
    stop_duplicate_check,
    limit_checker,
)
from ...mirror_leech_utils.status_utils.queue_status import QueueStatus
from ...telegram_helper.message_utils import send_status_message
from ..status_utils.spotdl_status import SpotDLStatus

LOGGER = getLogger(__name__)


def _create_spotdl(output_format, cookie_path):
    from spotdl import Spotdl
    from spotdl.utils.spotify import SpotifyClient

    SpotifyClient._instance = None

    ffmpeg_path = f"/bin/{BinConfig.FFMPEG_NAME}"
    if not cookie_path or not ospath.exists(cookie_path):
        cookie_path = None

    fmt = output_format
    bitrate = None
    if ":" in output_format:
        fmt, bitrate = output_format.split(":", 1)

    settings = {
        "output": "{artists}/{album}/{title} - {artist}.{ext}",
        "format": fmt,
        "threads": 4,
        "ffmpeg": ffmpeg_path,
        "cookie_file": cookie_path,
        "simple_tui": True,
    }
    if bitrate:
        settings["bitrate"] = bitrate

    return Spotdl(
        client_id="-",
        client_secret="",
        no_cache=True,
        downloader_settings=settings,
    )


class SpotDLHelper:
    def __init__(self, listener):
        self._progress = 0
        self._downloaded_bytes = 0
        self._total_songs = 0
        self._completed_songs = 0
        self._listener = listener
        self._gid = ""
        self._path = ""

    @property
    def download_speed(self):
        return 0

    @property
    def downloaded_bytes(self):
        return self._downloaded_bytes

    @property
    def size(self):
        return self._listener.size

    @property
    def progress(self):
        return self._progress

    @property
    def eta(self):
        return "-"

    async def _on_download_start(self, from_queue=False):
        async with task_dict_lock:
            task_dict[self._listener.mid] = SpotDLStatus(
                self._listener, self, self._gid
            )
        if not from_queue:
            await self._listener.on_download_start()
            if self._listener.multi <= 1 and not self._listener.is_rss:
                await send_status_message(self._listener.message)

    def _on_download_error(self, error):
        from ...ext_utils.bot_utils import async_to_sync

        self._listener.is_cancelled = True
        async_to_sync(self._listener.on_download_error, error)

    def _run_spotdl(self, path, output_format):
        makedirs(path, exist_ok=True)
        old_cwd = getcwd()
        cookie = get_cookie_file(self._listener.user_dict)
        if cookie == "cookies.txt":
            cookie = f"{old_cwd}/{cookie}"
        chdir(path)
        try:
            spotdl = _create_spotdl(output_format, cookie)

            try:
                songs = spotdl.search([self._listener.link])
            except Exception as e:
                self._on_download_error(str(e))
                return

            if not songs:
                self._on_download_error("No songs found for the given link.")
                return

            self._total_songs = len(songs)
            self._listener.name = ""

            for i, song in enumerate(songs):
                if self._listener.is_cancelled:
                    return

                self._current_song = song.name

                try:
                    spotdl.download(song)
                    self._completed_songs = i + 1
                    self._progress = (
                        ((i + 1) / self._total_songs) * 100 if self._total_songs > 0 else 0
                    )
                    self._update_size(path)
                except Exception as e:
                    LOGGER.error(f"SpotDL failed to download: {song.name} - {e}")

            if self._listener.is_cancelled:
                return

            if self._completed_songs == 0:
                self._on_download_error("Failed to download any songs.")
                return

            self._set_listener_name(path)

            chdir(old_cwd)

            from ...ext_utils.bot_utils import async_to_sync

            async_to_sync(self._listener.on_download_complete)
            return
        finally:
            chdir(old_cwd)

    def _update_size(self, path):
        total = 0
        try:
            for root, dirs, files in oswalk(path):
                for f in files:
                    fp = ospath.join(root, f)
                    try:
                        total += stat(fp).st_size
                    except Exception:
                        pass
        except Exception:
            pass
        self._downloaded_bytes = total
        if total > self._listener.size:
            self._listener.size = total

    def _set_listener_name(self, path):
        try:
            for root, dirs, files in oswalk(path):
                for f in files:
                    if not f.endswith((".jpg", ".png", ".jpeg", ".webp")):
                        self._listener.name = f
                        return
        except Exception:
            pass

    async def add_download(self, path, output_format):
        self._gid = token_hex(5)
        self._path = path

        await self._on_download_start()

        msg, button = await stop_duplicate_check(self._listener)
        if msg:
            await self._listener.on_download_error(msg, button)
            return

        if limit_exceeded := await limit_checker(self._listener):
            await self._listener.on_download_error(limit_exceeded, is_limit=True)
            return

        add_to_queue, event = await check_running_tasks(self._listener)
        if add_to_queue:
            LOGGER.info(f"Added to Queue/Download: {self._listener.name}")
            async with task_dict_lock:
                task_dict[self._listener.mid] = QueueStatus(
                    self._listener, self._gid, "dl"
                )
            await event.wait()
            if self._listener.is_cancelled:
                return
            LOGGER.info(
                f"Start Queued Download from SpotDL: {self._listener.name}"
            )
            await self._on_download_start(True)

        if not add_to_queue:
            LOGGER.info(f"Download with SpotDL: {self._listener.name}")

        await sync_to_async(self._run_spotdl, path, output_format)

    async def cancel_task(self):
        self._listener.is_cancelled = True
        LOGGER.info(f"Cancelling Download: {self._listener.name}")
        await self._listener.on_download_error("Stopped by User!")
