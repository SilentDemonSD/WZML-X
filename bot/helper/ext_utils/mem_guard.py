import gc
import linecache
import tracemalloc
from asyncio import Condition, sleep
from time import time

from ... import LOGGER
from ...core.config_manager import Config
from .bot_lock import get_system_resources_cached

MB = 1024 * 1024
_MIN_BUDGET = 48 * MB
_MAX_BUDGET = 512 * MB
_SAMPLE_SECONDS = 20
_HISTORY = 90


def rss_bytes():
    try:
        from psutil import Process

        return Process().memory_info().rss
    except Exception:
        return 0


def available_bytes():
    try:
        from psutil import virtual_memory

        return virtual_memory().available
    except Exception:
        return 0


def limit_bytes():
    return get_system_resources_cached()["ram_mb"] * MB


def readable(size):
    size = float(size or 0)
    for unit in ("B", "KiB", "MiB", "GiB"):
        if abs(size) < 1024 or unit == "GiB":
            return f"{size:.1f} {unit}" if unit != "B" else f"{int(size)} B"
        size /= 1024
    return f"{size:.1f} GiB"


class Budget:
    def __init__(self):
        self._used = 0
        self._peak = 0
        self._waits = 0
        self._cond = Condition()
        self._limit = None

    @property
    def limit(self):
        if self._limit is None:
            configured = (Config.MEM_BUDGET or 0) * MB
            if configured > 0:
                self._limit = configured
            else:
                share = int(limit_bytes() * 0.15)
                self._limit = max(_MIN_BUDGET, min(_MAX_BUDGET, share))
        return self._limit

    @property
    def used(self):
        return self._used

    @property
    def peak(self):
        return self._peak

    @property
    def waits(self):
        return self._waits

    def resize(self, value):
        self._limit = max(1, int(value))

    async def reserve(self, size):
        size = max(0, int(size))
        if size <= 0:
            return 0
        cap = max(self.limit, size)
        async with self._cond:
            waited = False
            while self._used + size > cap:
                waited = True
                await self._cond.wait()
            if waited:
                self._waits += 1
            self._used += size
            self._peak = max(self._peak, self._used)
        return size

    async def release(self, size):
        size = max(0, int(size))
        if size <= 0:
            return
        async with self._cond:
            self._used = max(0, self._used - size)
            self._cond.notify_all()

    def stats(self):
        return {
            "limit": self.limit,
            "used": self._used,
            "peak": self._peak,
            "waits": self._waits,
        }


budget = Budget()
_caches = {}


def register_cache(name, size_fn, trim_fn=None):
    _caches[name] = (size_fn, trim_fn)


def cache_sizes():
    out = {}
    for name, (size_fn, _) in _caches.items():
        try:
            out[name] = int(size_fn() or 0)
        except Exception:
            out[name] = 0
    return out


def trim_caches(aggressive=False):
    freed = 0
    for name, (size_fn, trim_fn) in _caches.items():
        if trim_fn is None:
            continue
        try:
            before = int(size_fn() or 0)
            trim_fn(aggressive)
            freed += max(0, before - int(size_fn() or 0))
        except Exception as err:
            LOGGER.error(f"cache {name} trim failed: {err}")
    return freed


class Profiler:
    def __init__(self):
        self.started_at = 0.0

    @property
    def running(self):
        return tracemalloc.is_tracing()

    def start(self, frames=12):
        if self.running:
            return False
        tracemalloc.start(frames)
        self.started_at = time()
        LOGGER.info("memory profiler started")
        return True

    def stop(self):
        if not self.running:
            return False
        tracemalloc.stop()
        self.started_at = 0.0
        LOGGER.info("memory profiler stopped")
        return True

    def top(self, count=12):
        if not self.running:
            return []
        snapshot = tracemalloc.take_snapshot().filter_traces(
            (
                tracemalloc.Filter(False, tracemalloc.__file__),
                tracemalloc.Filter(False, linecache.__file__),
                tracemalloc.Filter(False, "<frozen importlib._bootstrap>"),
            )
        )
        rows = []
        for stat in snapshot.statistics("lineno")[:count]:
            frame = stat.traceback[0]
            where = frame.filename
            for marker in ("/bot/", "\\bot\\", "site-packages/", "site-packages\\"):
                if marker in where:
                    where = where.split(marker, 1)[1]
                    break
            rows.append(
                {
                    "where": f"{where}:{frame.lineno}",
                    "size": stat.size,
                    "count": stat.count,
                }
            )
        return rows


profiler = Profiler()


class Monitor:
    def __init__(self):
        self.samples = []
        self.peak = 0
        self.trims = 0
        self.last = 0
        self._task = None

    def sample(self):
        now = rss_bytes()
        self.last = now
        self.peak = max(self.peak, now)
        self.samples.append((int(time()), now))
        if len(self.samples) > _HISTORY:
            del self.samples[: len(self.samples) - _HISTORY]
        return now

    def pressure(self):
        cap = limit_bytes()
        if cap <= 0:
            return 0.0
        return min(1.0, self.last / cap)

    async def _loop(self):
        while True:
            try:
                await sleep(_SAMPLE_SECONDS)
                used = self.sample()
                ratio = self.pressure()
                if ratio >= 0.85:
                    freed = trim_caches(aggressive=True)
                    collected = gc.collect()
                    self.trims += 1
                    after = self.sample()
                    LOGGER.warning(
                        f"memory at {ratio * 100:.0f}% of "
                        f"{readable(limit_bytes())} ({readable(used)}); "
                        f"trimmed {readable(freed)}, gc freed {collected} objects, "
                        f"now {readable(after)}"
                    )
                    if profiler.running:
                        for row in profiler.top(5):
                            LOGGER.warning(
                                f"  {row['where']} {readable(row['size'])} "
                                f"in {row['count']} blocks"
                            )
                elif ratio >= 0.7:
                    trim_caches(aggressive=False)
            except Exception as err:
                LOGGER.error(f"memory monitor: {err}")

    def start(self):
        if self._task is not None:
            return
        from ... import bot_loop

        self.sample()
        self._task = bot_loop.create_task(self._loop())
        LOGGER.info(
            f"Memory monitor on: {readable(self.last)} used of "
            f"{readable(limit_bytes())}, transfer budget {readable(budget.limit)}"
        )

    def stop(self):
        if self._task is not None:
            self._task.cancel()
            self._task = None


monitor = Monitor()


def snapshot():
    used = monitor.sample()
    cap = limit_bytes()
    caches = cache_sizes()
    return {
        "rss": used,
        "limit": cap,
        "available": available_bytes(),
        "peak": monitor.peak,
        "pressure": monitor.pressure(),
        "budget": budget.stats(),
        "caches": caches,
        "cache_total": sum(caches.values()),
        "gc": {
            "objects": len(gc.get_objects()) if Config.MEM_DEEP_STATS else 0,
            "counts": gc.get_count(),
        },
        "trims": monitor.trims,
        "profiling": profiler.running,
    }
