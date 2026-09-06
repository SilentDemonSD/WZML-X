from time import time

from ...ext_utils.status_utils import (
    EngineStatus,
    MirrorStatus,
    get_readable_file_size,
    get_readable_time,
)


class TelegramCloneStatus:
    def __init__(self, listener, obj, gid):
        self.listener = listener
        self._obj = obj
        self._gid = gid
        self.engine = EngineStatus().STATUS_TGRAM

    @property
    def _total(self):
        return max(1, self._obj.total_units)

    @property
    def _done(self):
        return min(self._total, int(self.listener.proceed_count or 0))

    @property
    def _elapsed(self):
        return max(0.001, time() - self._obj._start)

    def gid(self):
        return self._gid

    def name(self):
        return self.listener.name

    def status(self):
        return MirrorStatus.STATUS_CLONE

    def size(self):
        return get_readable_file_size(self.listener.size or 0)

    def processed_bytes(self):
        return get_readable_file_size(self._obj.processed_bytes)

    def progress(self):
        return f"{round(self._done / self._total * 100, 2)}%"

    def speed(self):
        return f"{get_readable_file_size(self._obj.processed_bytes / self._elapsed)}/s"

    def eta(self):
        done = self._done
        if not done:
            return "-"
        left = (self._total - done) / (done / self._elapsed)
        return get_readable_time(left) if left > 0 else "0s"

    def task(self):
        return self._obj
