from asyncio import gather
from collections import defaultdict

from .... import LOGGER, sabnzbd_client
from ...ext_utils.status_utils import (
    MirrorStatus,
    EngineStatus,
    get_readable_file_size,
    get_readable_time,
    time_to_seconds,
)
from ...listeners.nzb_listener import _remove_job


async def get_download(nzo_id, old_info=None):
    if old_info is None:
        old_info = defaultdict(lambda: "")
    try:
        queue = await sabnzbd_client.get_downloads(nzo_ids=nzo_id)
        if res := queue["queue"]["slots"]:
            slot = res[0]
            if msg := slot["labels"]:
                filtered_msgs = []
                for m in msg:
                    if "apikey=" in m or "Trying to fetch NZB from" in m:
                        if "getnzb/api/" in m:
                            nzb_id = m.split("getnzb/api/")[1].split("?")[0]
                            filtered_msgs.append(f"Fetching NZB ID: {nzb_id}")
                        else:
                            filtered_msgs.append("Fetching NZB...")
                    else:
                        filtered_msgs.append(m)
                if filtered_msgs:
                    LOGGER.warning(" | ".join(filtered_msgs))
            return slot
        else:
            history = await sabnzbd_client.get_history(nzo_ids=nzo_id)
            if res := history["history"]["slots"]:
                slot = res[0]
                if slot["status"] == "Verifying":
                    parts = slot["action_line"].split("Verifying: ")[-1].split("/")
                    if len(parts) > 1:
                        percentage = round(
                            (int(float(parts[0])) / int(float(parts[1]))) * 100, 2
                        )
                        old_info["percentage"] = percentage
                elif slot["status"] == "Repairing":
                    action = slot["action_line"].split("Repairing: ")[-1].split()
                    if len(action) > 2:
                        old_info["percentage"] = action[0].strip("%")
                        old_info["timeleft"] = action[2]
                elif slot["status"] == "Extracting":
                    if "Unpacking" in slot["action_line"]:
                        action = slot["action_line"].split("Unpacking: ")[-1].split()
                    else:
                        action = (
                            slot["action_line"].split("Direct Unpack: ")[-1].split()
                        )
                    if len(action) > 2:
                        parts = action[0].split("/")
                        if len(parts) > 1:
                            old_info["percentage"] = round(
                                (int(float(parts[0])) / int(float(parts[1]))) * 100, 2
                            )
                            old_info["timeleft"] = action[2]
                old_info["status"] = slot["status"]
        return old_info
    except Exception as e:
        LOGGER.error(f"{e}: Sabnzbd, while getting job info. ID: {nzo_id}")
        return old_info


class SabnzbdStatus:
    def __init__(self, listener, gid, queued=False):
        self.queued = queued
        self.listener = listener
        self._gid = gid
        self._info = defaultdict(lambda: "")
        self.engine = EngineStatus().STATUS_SABNZBD
        if hasattr(listener, "nzb_id") and listener.nzb_id:
            self._display_name = f"NZB ID: {listener.nzb_id}"
        else:
            self._display_name = None

    async def update(self):
        self._info = await get_download(self._gid, self._info)

    def progress(self):
        return f"{self._info.get('percentage', '0')}%"

    def processed_raw(self):
        return (
            float(self._info.get("mb", "0")) - float(self._info.get("mbleft", "0"))
        ) * 1048576

    def processed_bytes(self):
        return get_readable_file_size(self.processed_raw())

    def speed_raw(self):
        if self._info.get("mb", "0") == self._info.get("mbleft", "0"):
            return 0
        try:
            return int(float(self._info.get("mbleft", "0")) * 1048576) / self.eta_raw()
        except Exception:
            return 0

    def speed(self):
        return f"{get_readable_file_size(self.speed_raw())}/s"

    def name(self):
        filename = self._info.get("filename", "")
        if self._display_name and (not filename or "Trying to fetch" in filename):
            return self._display_name
        if filename and "apikey=" in filename:
            if "getnzb/api/" in filename:
                nzb_id = filename.split("getnzb/api/")[1].split("?")[0]
                return f"NZB ID: {nzb_id}"
            return "Fetching NZB..."
        return filename or self._display_name or "Fetching NZB..."

    def size(self):
        return self._info.get("size", 0)

    def eta_raw(self):
        return int(time_to_seconds(self._info.get("timeleft", "0")))

    def eta(self):
        return get_readable_time(self.eta_raw())

    async def status(self):
        await self.update()
        if self._info.get("mb", "0") == self._info.get("mbleft", "0"):
            return MirrorStatus.STATUS_QUEUEDL
        state = self._info.get("status")
        if state == "Paused" and self.queued:
            return MirrorStatus.STATUS_QUEUEDL
        elif state in [
            "QuickCheck",
            "Verifying",
            "Repairing",
            "Fetching",
            "Moving",
            "Extracting",
        ]:
            return state
        else:
            return MirrorStatus.STATUS_DOWNLOAD

    def task(self):
        return self

    def gid(self):
        return self._gid

    async def cancel_task(self):
        self.listener.is_cancelled = True
        await self.update()
        LOGGER.info(f"Cancelling Download: {self.name()}")
        await gather(
            self.listener.on_download_error("Stopped by user!"),
            _remove_job(self._gid, self.listener.mid),
        )
