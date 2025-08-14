from mega import MegaApi

from ...ext_utils.status_utils import (
    MirrorStatus,
    get_readable_file_size,
    get_readable_time
)


class MegaDownloadStatus:
    def __init__(
            self,
            listener,
            obj,
            gid,
            status
        ):
        self.listener = listener
        self._obj = obj
        self._size = self.listener.size
        self._gid = gid
        self._status = status
        self.engine = f"Mega SDK v{self._eng_ver()}"

    def _eng_ver(self):
        return MegaApi("zee").getVersion()

    def name(self):
        return self.listener.name

    def progress_raw(self):
        try:
            return round(self._obj.downloaded_bytes / self._size * 100, 2)
        except:
            return 0.0

    def progress(self):
        return f"{self.progress_raw()}%"

    def status(self):
        return MirrorStatus.STATUS_DOWNLOAD

    def processed_bytes(self):
        return get_readable_file_size(self._obj.downloaded_bytes)

    def eta(self):
        try:
            seconds = (self._size - self._obj.downloaded_bytes) / \
                self._obj.speed
            return get_readable_time(seconds)
        except ZeroDivisionError:
            return "-"

    def size(self):
        return get_readable_file_size(self._size)

    def speed(self):
        return f"{get_readable_file_size(self._obj.speed)}/s"

    def gid(self):
        return self._gid

    def task(self):
        return self._obj