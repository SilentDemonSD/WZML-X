#!/usr/bin/env python3
from time import time

from bot import aria2, LOGGER
from bot.helper.ext_utils.bot_utils import EngineStatus, MirrorStatus, get_readable_time, sync_to_async


def get_download(gid, old_info=None):
    try:
        res = aria2.get_download(gid)
        return res or old_info
    except Exception as e:
        LOGGER.error(f"{e}: Aria2c, Error while getting torrent info")
        return old_info


class Aria2Status:

    def __init__(self, gid, listener, seeding=False, queued=False):
        self.gid = gid
        self.download = None
        self.listener = listener
        self.queued = queued
        self.start_time = 0
        self.seeding = seeding

    def update(self):
        if self.download is None:
            self.download = get_download(self.gid)
        else:
            self.download = self.download.live
        if self.download.followed_by_ids:
            self.gid = self.download.followed_by_ids[0]
            self.download = get_download(self.gid)

    def progress(self):
        return self.download.progress_string()

    def processed_bytes(self):
        return self.download.completed_length_string()

    def speed(self):
        return self.download.download_speed_string()

    def name(self):
        return self.download.name

    def size(self):
        return self.download.total_length_string()

    def eta(self):
        return self.download.eta_string()
        
    def listener(self):
        return self.listener

    def status(self):
        self.update()
        if self.download.is_waiting or self.queued:
            if self.seeding:
                return MirrorStatus.STATUS_QUEUEUP
            else:
                return MirrorStatus.STATUS_QUEUEDL
        elif self.download.is_paused:
            return MirrorStatus.STATUS_PAUSED
        elif self.download.seeder and self.seeding:
            return MirrorStatus.STATUS_SEEDING
        else:
            return MirrorStatus.STATUS_DOWNLOADING

    def seeders_num(self):
        return self.download.num_seeders

    def leechers_num(self):
        return self.download.connections

    def uploaded_bytes(self):
        return self.download.upload_length_string()

    def upload_speed(self):
        self.update()
        return self.download.upload_speed_string()

    def ratio(self):
        return f"{round(self.download.upload_length / self.download.completed_length, 3)}"

    def seeding_time(self):
        return get_readable_time(time() - self.start_time)

    def task(self):
        return self

    def gid(self):
        return self.gid

    async def cancel_task(self):
        self.listener.isCancelled = True
        await sync_to_async(self.update)
        if self.download.seeder and self.seeding:
            LOGGER.info(f"Cancelling Seed: {self.name()}")
            await self.listener.onUploadError(f"Seeding stopped with Ratio: {self.ratio()} and Time: {self.seeding_time()}")
            await sync_to_async(aria2.remove, [self.download], force=True, files=True)
        elif downloads := self.download.followed_by:
            LOGGER.info(f"Cancelling Download: {self.name()}")
            await self.listener.onDownloadError('Download cancelled by user!')
            downloads.append(self.download)
            await sync_to_async(aria2.remove, downloads, force=True, files=True)
        else:
            if self.queued:
                LOGGER.info(f'Cancelling QueueDl: {self.name()}')
                msg = 'task have been removed from queue/download'
            else:
                LOGGER.info(f"Cancelling Download: {self.name()}")
                msg = 'Download stopped by user!'
            await self.listener.onDownloadError(msg)
            await sync_to_async(aria2.remove, [self.download], force=True, files=True)

    def eng(self):
        return EngineStatus().STATUS_ARIA
