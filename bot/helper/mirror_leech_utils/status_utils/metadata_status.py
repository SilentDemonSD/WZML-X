from .... import LOGGER
from ...ext_utils.status_utils import (
    get_readable_file_size,
    EngineStatus,
    MirrorStatus,
    get_readable_time,
)


class MetadataStatus:
    def __init__(self, listener, obj, gid, status=""):
        self.listener = listener
        self._obj = obj
        self._gid = gid
        self._cstatus = status
        self.engine = EngineStatus().STATUS_METADATA

    def speed(self):
        try:
            return (
                f"{get_readable_file_size(self._obj.speed_raw)}/s"
                if hasattr(self._obj, "speed_raw") and self._obj.speed_raw
                else "0 B/s"
            )
        except Exception:
            return "0 B/s"

    def processed_bytes(self):
        try:
            return (
                get_readable_file_size(self._obj.processed_bytes)
                if hasattr(self._obj, "processed_bytes") and self._obj.processed_bytes
                else "0 B"
            )
        except Exception:
            return "0 B"

    def progress(self):
        try:
            if (
                hasattr(self._obj, "progress_raw")
                and self._obj.progress_raw is not None
            ):
                return f"{round(self._obj.progress_raw, 2)}%"
            elif hasattr(self._obj, "_progress") and self._obj._progress is not None:
                return f"{round(self._obj._progress, 2)}%"
            return "0%"
        except Exception:
            return "0%"

    def gid(self):
        return self._gid

    def name(self):
        try:
            return getattr(self.listener, "subname", None) or self.listener.name
        except Exception:
            return "Processing..."

    def size(self):
        try:
            size = getattr(self.listener, "subsize", None) or self.listener.size
            return get_readable_file_size(size) if size else "Unknown"
        except Exception:
            return "Unknown"

    def eta(self):
        try:
            if (
                hasattr(self._obj, "eta_raw")
                and self._obj.eta_raw is not None
                and self._obj.eta_raw > 0
            ):
                return get_readable_time(self._obj.eta_raw)
            elif hasattr(self._obj, "_eta") and self._obj._eta != "-":
                return self._obj._eta
            return "-"
        except Exception:
            return "-"

    def status(self):
        if self._cstatus == "Convert":
            return MirrorStatus.STATUS_CONVERT
        else:
            return MirrorStatus.STATUS_METADATA

    def task(self):
        return self

    async def cancel_task(self):
        LOGGER.info(f"Cancelling {self._cstatus}: {self.listener.name}")
        self.listener.is_cancelled = True
        if (
            self.listener.subproc is not None
            and self.listener.subproc.returncode is None
        ):
            try:
                self.listener.subproc.kill()
            except Exception:
                pass
        await self.listener.on_upload_error(f"{self._cstatus} stopped by user!")
