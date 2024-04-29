#!/usr/bin/env python3
from bot.helper.ext_utils.bot_utils import EngineStatus, MirrorStatus, get_readable_file_size, get_readable_time

class GDriveStatus:
    def __init__(self, obj, size, message, gid, status, upload_details):
        self.obj = obj
        self.size = size
        self.message = message
        self.gid = gid
        self.status = status
        self.upload_details = upload_details

    def processed_bytes(self):
        return get_readable_file_size(self.obj.processed_bytes)

    def status(self):
        match self.status:
            case 'up':
                return MirrorStatus.STATUS_UPLOADING
            case 'dl':
                return MirrorStatus.STATUS_DOWNLOADING
            case _:
                return MirrorStatus.STATUS_CLONING

    def name(self):
        return self.obj.name

    def gid(self) -> str:
        return self.gid

    def progress_raw(self):
        try:
            return self.obj.processed_bytes / self.size * 100
        except:
            return 0

    def progress(self):
        return f'{round(self.progress_raw(), 2)}%'

    def speed(self):
        return f'{get_readable_file_size(self.obj.speed)}/s'

    def eta(self):
        try:
            seconds = (self.size - self.obj.processed_bytes) / self.obj.speed
            return get_readable_time(seconds)
        except:
            return '-'

    def download(self):
        return self.obj

    def engine(self):
        return EngineStatus().STATUS_GD
