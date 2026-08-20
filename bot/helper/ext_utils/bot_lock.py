from asyncio import Lock, Semaphore
from os import sched_getaffinity
from pathlib import Path

from ...core.config_manager import Config


def _read_cgroup_file(path):
    try:
        return Path(path).read_text().strip()
    except OSError:
        return None


def _get_cgroup_cpu():
    quota = _read_cgroup_file("/sys/fs/cgroup/cpu.max")
    if quota and quota != "max":
        try:
            parts = quota.split()
            if len(parts) == 2:
                period = int(parts[1])
                if period > 0:
                    return int(parts[0]) / period
        except (ValueError, TypeError):
            pass
    quota = _read_cgroup_file("/sys/fs/cgroup/cpu/cpu.cfs_quota_us")
    period = _read_cgroup_file("/sys/fs/cgroup/cpu/cpu.cfs_period_us")
    if quota and period:
        try:
            quota, period = int(quota), int(period)
            if quota > 0 and period > 0:
                return quota / period
        except (ValueError, TypeError):
            pass
    return None


def _get_cgroup_ram():
    limit = _read_cgroup_file("/sys/fs/cgroup/memory.max")
    if limit and limit != "max":
        try:
            return int(limit)
        except (ValueError, TypeError):
            pass
    limit = _read_cgroup_file("/sys/fs/cgroup/memory/memory.limit_in_bytes")
    if limit:
        try:
            limit = int(limit)
            if limit < 2**62:
                return limit
        except (ValueError, TypeError):
            pass
    return None


def get_system_resources():
    cgroup_cpu = _get_cgroup_cpu()
    if cgroup_cpu and cgroup_cpu > 0:
        cpu_count = max(1, round(cgroup_cpu))
    else:
        cpu_count = max(1, len(sched_getaffinity(0)))

    cgroup_ram = _get_cgroup_ram()
    if cgroup_ram and cgroup_ram > 0:
        ram_mb = cgroup_ram // (1024 * 1024)
    else:
        try:
            from psutil import virtual_memory

            ram_mb = virtual_memory().total // (1024 * 1024)
        except ImportError:
            ram_mb = 512

    is_low_end = cpu_count <= 2 or ram_mb <= 1536

    return {
        "cpu_count": cpu_count,
        "ram_mb": ram_mb,
        "is_low_end": is_low_end,
    }


_system_resources = None


def get_system_resources_cached():
    global _system_resources
    if _system_resources is None:
        _system_resources = get_system_resources()
    return _system_resources


class SmartLock:
    def __init__(self, pause_targets=None, max_slots=None):
        self._lock = Lock()
        self._semaphore = Semaphore(1)
        self._pause_targets = pause_targets or []
        self._fixed_max = max_slots
        self._active = 0
        self._throttled = False

    @property
    def throttled(self):
        val = Config.THROTTLE_SERVICES
        if val == "always":
            return True
        if val == "never":
            return False
        return get_system_resources_cached()["is_low_end"]

    def _get_max_slots(self):
        if self._fixed_max is not None:
            return self._fixed_max
        res = get_system_resources_cached()
        if res["is_low_end"]:
            return 1
        return min(res["cpu_count"] // 2, 3)

    @property
    def active(self):
        return self._active

    @property
    def max_slots(self):
        return self._get_max_slots()

    async def acquire(self):
        await self._semaphore.acquire()
        async with self._lock:
            self._active += 1
            self._throttled = self.throttled
            at_capacity = self._active >= self._get_max_slots()
            if self._throttled and at_capacity and self._pause_targets:
                await self._pause(self._pause_targets)

    async def release(self):
        async with self._lock:
            if self._active == 0:
                return
            should_resume = (
                self._throttled
                and self._active >= self._get_max_slots()
                and self._pause_targets
            )
            if should_resume:
                await self._resume(self._pause_targets)
            self._active = max(0, self._active - 1)
            self._throttled = False
        self._semaphore.release()

    async def __aenter__(self):
        await self.acquire()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.release()
        return False

    async def _pause(self, targets):
        for t in targets:
            try:
                if t == "nzb" and not Config.DISABLE_NZB:
                    from ... import sabnzbd_client

                    if sabnzbd_client.LOGGED_IN:
                        await sabnzbd_client.pause_all()
                elif t == "jd" and not Config.DISABLE_JD:
                    from ...core.jdownloader_booter import jdownloader

                    if jdownloader.is_connected:
                        await jdownloader.device.downloadcontroller.stop_downloads()
            except (ConnectionError, TimeoutError, OSError):
                pass

    async def _resume(self, targets):
        for t in targets:
            try:
                if t == "nzb" and not Config.DISABLE_NZB:
                    from ... import sabnzbd_client

                    if sabnzbd_client.LOGGED_IN:
                        await sabnzbd_client.resume_all()
                elif t == "jd" and not Config.DISABLE_JD:
                    from ...core.jdownloader_booter import jdownloader

                    if jdownloader.is_connected:
                        await jdownloader.device.downloadcontroller.start_downloads()
            except (ConnectionError, TimeoutError, OSError):
                pass


ff_lock = SmartLock(pause_targets=["nzb", "jd"], max_slots=1)
sab_par2_lock = SmartLock(pause_targets=["jd"])
jd_heavy_lock = SmartLock(pause_targets=["nzb"])
