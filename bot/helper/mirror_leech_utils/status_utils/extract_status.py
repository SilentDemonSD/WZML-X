#!/usr/bin/env python3
from time import time

from bot import LOGGER, subprocess_lock
from bot.helper.ext_utils.bot_utils import EngineStatus, get_readable_file_size, MirrorStatus, get_readable_time, async_to_sync
from bot.helper.ext_utils.files_utils import get_path_size


class ExtractStatus:
    def __init__(self, listener, gid):
        self.listener = listener
        self._size = self.listener.size
        self._gid = gid
        self._start_time = time()
        self._proccessed_bytes = 0

    def gid(self):
        return self._gid

    def speed_raw(self):
        return self.processed_raw() / (time() - self._start_time)

    async def progress_raw(self):
        await self.processed_raw()
        try:
            return self.processed_raw() / self._size * 100
        except:
            return 0

    async def progress(self):
        return f'{round(self.progress_raw(), 2)}%'

    def speed(self):
        return f'{get_readable_file_size(self.speed_raw())}/s'

    def name(self):
        return self.listener.name

    def size(self):
        return get_readable_file_size(self._size)

    def eta(self):
        try:
            seconds = (self._size - self.processed_raw()) / self.speed_raw()
            return get_readable_time(seconds)
        except:
            return '-'

    def status(self):
        return MirrorStatus.STATUS_EXTRACTING

    def processed_bytes(self):
        return get_readable_file_size(self.processed_raw())

    async def processed_raw(self):
        if self.listener.newDir:
            self._proccessed_bytes = await get_path_size(self.listener.newDir)
        else:
            self._proccessed_bytes = await get_path_size(self.listener.dir) - self._size

    def download(self):
        return self

    async def cancel_task(self):
        LOGGER.info(f"Cancelling Extract: {self.listener.name}")
        self.listener.isCancelled = True
        async with subprocess_lock:
            if (
                self.listener.suproc is not None
                and self.listener.suproc.returncode is None
            ):
                self.listener.suproc.kill()
        await self.listener.onUploadError("extracting stopped by user!")

    def eng(self):
        return EngineStatus().STATUS_EXT