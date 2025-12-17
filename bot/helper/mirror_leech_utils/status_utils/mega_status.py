from ...ext_utils.status_utils import (
    EngineStatus,
    MirrorStatus,
    get_readable_file_size,
    get_readable_time,
)


class MegaDownloadStatus:
    def __init__(self, listener, obj, gid, status):
        self.listener = listener
        self._gid = gid
        self._status = status
        self._speed = 0
        self._downloaded_bytes = 0
        self._size = self.listener.size
        self.engine = EngineStatus().STATUS_MEGA

    def name(self):
        return self.listener.name

    def progress_raw(self):
        try:
            return round(self._downloaded_bytes / self._size * 100, 2)
        except ZeroDivisionError:
            return 0.0

    def progress(self):
        return f"{self.progress_raw()}%"

    def status(self):
        return MirrorStatus.STATUS_DOWNLOAD

    def processed_bytes(self):
        return get_readable_file_size(self._downloaded_bytes)

    def eta(self):
        try:
            seconds = (self._size - self._downloaded_bytes) / self._speed
            return get_readable_time(seconds)
        except ZeroDivisionError:
            return "-"

    def size(self):
        return get_readable_file_size(self._size)

    def speed(self):
        return f"{get_readable_file_size(self._speed)}/s"

    def gid(self):
        return self._gid

    def task(self):
        return self
