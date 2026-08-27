from .... import LOGGER
from ....core.seedr_client import seedr
from ...ext_utils.status_utils import (
    EngineStatus,
    MirrorStatus,
    get_readable_file_size,
    get_readable_time,
)


class SeedrStatus:
    def __init__(self, listener, torrent_id, seedr_client=None):
        self.listener = listener
        self._torrent_id = torrent_id
        self._seedr = seedr_client or seedr
        self._info = {}
        self.engine = EngineStatus().STATUS_SEEDR

    def progress(self):
        return f"{round(float(self._info.get('progress', 0)), 2)}%"

    def processed_bytes(self):
        return get_readable_file_size(
            self._info.get("size", 0) * float(self._info.get("progress", 0)) / 100
        )

    def speed(self):
        return f"{get_readable_file_size(self._info.get('speed', 0))}/s"

    def name(self):
        return self._info.get("name") or self.listener.name or "Fetching Metadata..."

    def size(self):
        return get_readable_file_size(self._info.get("size", 0))

    def eta(self):
        speed = self._info.get("speed", 0)
        if not speed:
            return "-"
        size = self._info.get("size", 0)
        left = size - size * float(self._info.get("progress", 0)) / 100
        return get_readable_time(left / speed) if left > 0 else "-"

    async def status(self):
        if self._info.get("stopped"):
            return MirrorStatus.STATUS_PAUSED
        return MirrorStatus.STATUS_SEEDR

    def task(self):
        return self

    def gid(self):
        return str(self._torrent_id)

    async def cancel_task(self):
        self.listener.is_cancelled = True
        LOGGER.info(f"Cancelling Download: {self.name()}")
        try:
            await self._seedr.delete("torrent", self._torrent_id)
        except Exception as e:
            LOGGER.error(f"Failed to delete seedr torrent {self._torrent_id}: {e}")
        await self.listener.on_download_error("Cancelled by user!")
