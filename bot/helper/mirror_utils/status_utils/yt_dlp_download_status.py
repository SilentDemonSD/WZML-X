#!/usr/bin/env python3
from bot.helper.ext_utils.bot_utils import EngineStatus, MirrorStatus, get_readable_file_size, get_readable_time, async_to_sync
from bot.helper.ext_utils.fs_utils import get_path_size

class YtDlpDownloadStatus:
    def __init__(self, obj, listener, gid):
        self.obj = obj
        self.listener = listener
        self.upload_details = listener.upload_details
        self.gid = gid
        self.message = listener.message

    def get_gid(self):
        return self.gid

    def processed_bytes(self):
        return get_readable_file_size(self.processed_raw())

    def processed_raw(self):
        if self.obj.downloaded_bytes != 0:
            return self.obj.downloaded_bytes
        else:
            return async_to_sync(get_path_size, self.listener.dir)

    def size(self):
        return get_readable_file_size(self.obj.size)

    def status(self):
        return MirrorStatus.STATUS_DOWNLOADING

    def name(self):
        return self.obj.name

    def progress(self):
        return f'{round(self.obj.progress, 2)}%'

    def speed(self):
        return f'{get_readable_file_size(self.obj.download_speed)}/s'

    def eta(self):
        if self.obj.eta != '-':
            return get_readable_time(self.obj.eta)
        try:
            seconds = (self.obj.size - self.processed_raw()) / self.obj.download_speed
            return get_readable_time(seconds)
        except:
            return '-'

    def download(self):
        return self.obj

    def engine(self):
        return EngineStatus().STATUS_YT

    def __str__(self):
        return (f"YtDlpDownloadStatus: \n"
                f"GID: {self.gid}\n"
                f"Processed Bytes: {self.processed_bytes()}\n"
                f"Size: {self.size()}\n"
                f"Status: {self.status()}\n"
                f"Name: {self.name()}\n"
                f"Progress: {self.progress()}\n"
                f"Speed: {self.speed()}\n"
                f"ETA: {self.eta()}\n"
                f"Download: {self.download()}\n"
                f"Engine: {self.engine()}\n")
