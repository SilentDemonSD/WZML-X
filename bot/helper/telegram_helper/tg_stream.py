from asyncio import (
    FIRST_COMPLETED,
    CancelledError,
    Lock,
    Semaphore,
    ensure_future,
    gather,
    sleep,
    wait,
    wait_for,
)
from collections import OrderedDict
from dataclasses import dataclass, replace
from time import monotonic

from pyrogram import raw
from pyrogram.errors import (
    FileMigrate,
    FileReferenceExpired,
    FileReferenceInvalid,
    FloodPremiumWait,
    FloodWait,
)
from pyrogram.file_id import FileId

from ... import LOGGER
from ...core.config_manager import Config
from ...core.tg_client import TgClient
from .tg_transfer import (
    MB,
    HypertgTransfer,
    MtprotoPool,
    get_global_work_loads,
    media_of,
)

KB = 1024
MIN_ALIGN = 4 * KB
MAX_CHUNK = MB

_FID_TTL = 1800
_FID_MAX = 512
_STICKY_TTL = 300
_SESSION_IDLE = 900

_GATE = Semaphore(64)


class StreamGone(Exception):
    pass


class StreamAbort(Exception):
    pass


class NoClientAvailable(Exception):
    pass


@dataclass(frozen=True)
class StreamProfile:
    name: str
    first_chunk: int
    max_chunk: int
    window: int
    clients: int
    invoke_timeout: float
    sleep_threshold: int
    cdn: bool
    max_per_client: int
    retries: int


_PROFILE_CACHE = {}


def profile(name):
    if not _PROFILE_CACHE:
        bulk_window = max(4, min(16, int(Config.STREAM_PIPELINE or 8) * 2))
        bulk_chunk = max(MIN_ALIGN, min(MAX_CHUNK, int(Config.STREAM_CHUNK or MB)))
        for p in (
            StreamProfile(
                name="playback",
                first_chunk=32 * KB,
                max_chunk=512 * KB,
                window=4,
                clients=1,
                invoke_timeout=8.0,
                sleep_threshold=0,
                cdn=False,
                max_per_client=3,
                retries=1,
            ),
            StreamProfile(
                name="bulk",
                first_chunk=bulk_chunk,
                max_chunk=bulk_chunk,
                window=bulk_window,
                clients=4,
                invoke_timeout=15.0,
                sleep_threshold=10,
                cdn=True,
                max_per_client=2,
                retries=2,
            ),
        ):
            _PROFILE_CACHE[p.name] = p
    return _PROFILE_CACHE[name]


FULL = object()


def parse_range(header, size):
    if not header:
        return FULL
    header = header.strip()
    if not header.lower().startswith("bytes="):
        return FULL
    if size <= 0:
        return None
    spec = header[6:].split(",", 1)[0].strip()
    if spec.startswith("-"):
        try:
            n = int(spec[1:])
        except ValueError:
            return None
        if n <= 0:
            return None
        return max(0, size - n), size - 1
    first, _, last = spec.partition("-")
    try:
        start = int(first)
    except ValueError:
        return None
    if start < 0 or start >= size:
        return None
    if not last:
        return start, size - 1
    try:
        end = int(last)
    except ValueError:
        return None
    if end < start:
        return None
    return start, min(end, size - 1)


def _next_pow2(n):
    return 1 << (n - 1).bit_length() if n > 1 else 1


def plan_chunks(start, end_ex, prof):
    mx = prof.max_chunk
    pos = start - (start % MIN_ALIGN)
    out = []
    while pos < end_ex:
        c = (pos & -pos) or mx
        c = min(c, mx, max(MIN_ALIGN, _next_pow2(end_ex - pos)))
        if not out:
            c = min(c, prof.first_chunk)
        c = max(MIN_ALIGN, c)
        out.append((pos, c))
        pos += c
    return out


_fid_cache = OrderedDict()
_fid_locks = {}


async def get_fid(ci, client, chat_id, msg_id, force=False):
    key = (ci, chat_id, msg_id)
    if not force:
        hit = _fid_cache.get(key)
        if hit and monotonic() - hit[1] < _FID_TTL:
            _fid_cache.move_to_end(key)
            return hit[0]
    lk = _fid_locks.setdefault(key, Lock())
    async with lk:
        hit = _fid_cache.get(key)
        if hit and not force and monotonic() - hit[1] < _FID_TTL:
            return hit[0]
        msg = await client.get_messages(chat_id, msg_id)
        if msg is None or getattr(msg, "empty", False):
            _fid_cache.pop(key, None)
            raise StreamGone(f"msg {msg_id} missing from {chat_id}")
        media = media_of(msg)
        fid = FileId.decode(media.file_id)
        fid.file_size = getattr(media, "file_size", 0)
        fid.mime_type = getattr(media, "mime_type", "") or ""
        fid.file_name = getattr(media, "file_name", "") or ""
        fid.unique_id = getattr(media, "file_unique_id", "") or ""
        _fid_cache[key] = (fid, monotonic())
        if len(_fid_cache) > _FID_MAX:
            old, _ = _fid_cache.popitem(last=False)
            _fid_locks.pop(old, None)
        return fid


def purge_fid(chat_id, msg_id):
    for k in [k for k in _fid_cache if k[1] == chat_id and k[2] == msg_id]:
        _fid_cache.pop(k, None)
        _fid_locks.pop(k, None)


_BG = set()


def _drain_in_background(inflight, timeout):
    if not inflight:
        return
    futs = list(inflight)
    inflight.clear()

    async def _drain():
        try:
            await wait_for(gather(*futs, return_exceptions=True), timeout=timeout + 5)
        except Exception:
            pass

    t = ensure_future(_drain())
    _BG.add(t)
    t.add_done_callback(_BG.discard)


class StreamPool:
    def __init__(self):
        self._pool = None
        self._clients = {}
        self._cooldown = {}
        self._sticky = {}
        self._lock = Lock()
        self._touched = {}

    def resolve(self):
        if TgClient.stream_bots:
            return dict(TgClient.stream_bots), TgClient.stream_loads, True
        return dict(TgClient.helper_bots), get_global_work_loads(), False

    def ensure_pool(self, clients):
        if self._pool is None or self._clients.keys() != clients.keys():
            self._pool = MtprotoPool(clients)
            self._clients = clients
        return self._pool

    async def acquire(self, prof, n=1, sticky_key=None):
        clients, loads, _ = self.resolve()
        if not clients:
            raise NoClientAvailable("no stream or helper bots are running")
        self.ensure_pool(clients)
        now = monotonic()
        async with self._lock:
            if sticky_key is not None:
                got = self._sticky.get(sticky_key)
                if (
                    got
                    and got[1] > now
                    and got[0] in clients
                    and self._cooldown.get(got[0], 0) < now
                    and loads.get(got[0], 0) < prof.max_per_client
                ):
                    loads[got[0]] = loads.get(got[0], 0) + 1
                    self._sticky[sticky_key] = (got[0], now + _STICKY_TTL)
                    return [got[0]]
            cand = [
                i
                for i in clients
                if i > 0
                and self._cooldown.get(i, 0) < now
                and loads.get(i, 0) < prof.max_per_client
            ]
            if not cand:
                raise NoClientAvailable("all clients busy or cooling down")
            cand.sort(key=lambda i: loads.get(i, 0))
            picked = cand[: max(1, min(n, len(cand)))]
            for i in picked:
                loads[i] = loads.get(i, 0) + 1
            if sticky_key is not None:
                self._sticky[sticky_key] = (picked[0], now + _STICKY_TTL)
            return picked

    async def release(self, idxs):
        _, loads, _ = self.resolve()
        async with self._lock:
            for i in idxs:
                loads[i] = max(0, loads.get(i, 0) - 1)

    def cool(self, ci, seconds):
        self._cooldown[ci] = monotonic() + seconds

    def client(self, ci):
        return self._clients.get(ci)

    async def session(self, ci, dc_id, force=False):
        if force:
            await self._pool.drop_session(ci, dc_id)
        self._touched[(ci, dc_id)] = monotonic()
        return await self._pool.get_session(ci, dc_id, is_media=True)

    async def drop(self, ci, dc_id):
        self._touched.pop((ci, dc_id), None)
        if self._pool:
            await self._pool.drop_session(ci, dc_id)

    async def reap_idle(self):
        if not self._pool:
            return
        now = monotonic()
        for (ci, dc), seen in list(self._touched.items()):
            if now - seen > _SESSION_IDLE:
                self._touched.pop((ci, dc), None)
                await self._pool.drop_session(ci, dc)

    async def stop(self):
        if self._pool:
            await self._pool.stop()
        self._touched.clear()
        self._sticky.clear()


POOL = StreamPool()


class HypertgStream:
    def __init__(self, chat_id, msg_id, prof, viewer=None):
        self.chat_id = chat_id
        self.msg_id = msg_id
        self.prof = prof
        self.viewer = viewer
        self.fid = None
        self.size = 0
        self.name = ""
        self.mime = ""
        self.unique_id = ""
        self._idxs = []
        self._loc = {}
        self._dc = {}
        self._dead = False
        self._released = False

    async def open(self):
        key = (self.chat_id, self.msg_id, self.viewer) if self.viewer else None
        self._idxs = await POOL.acquire(self.prof, self.prof.clients, sticky_key=key)
        try:
            for ci in self._idxs:
                fid = await get_fid(ci, POOL.client(ci), self.chat_id, self.msg_id)
                self._loc[ci] = (0, HypertgTransfer._location(fid))
                self._dc[ci] = fid.dc_id
                if self.fid is None:
                    self.fid = fid
                    self.size = int(getattr(fid, "file_size", 0) or 0)
                    self.mime = getattr(fid, "mime_type", "") or ""
                    self.name = getattr(fid, "file_name", "") or ""
                    self.unique_id = getattr(fid, "unique_id", "") or ""
        except BaseException:
            await self._release()
            raise
        if not self.size:
            await self._release()
            raise StreamGone("media has no size")
        return self

    async def _release(self):
        if self._released:
            return
        self._released = True
        if self._idxs:
            await POOL.release(self._idxs)

    async def _refresh_loc(self, ci, seen_gen):
        cur_gen, _ = self._loc[ci]
        if cur_gen != seen_gen:
            return
        fid = await get_fid(ci, POOL.client(ci), self.chat_id, self.msg_id, force=True)
        self._dc[ci] = fid.dc_id
        self._loc[ci] = (cur_gen + 1, HypertgTransfer._location(fid))

    async def _fetch(self, ci, off, lim):
        refreshes = 0
        attempt = 0
        while True:
            if self._dead:
                return b""
            gen, loc = self._loc[ci]
            try:
                async with _GATE:
                    sess = await POOL.session(ci, self._dc[ci])
                    r = await sess.invoke(
                        raw.functions.upload.GetFile(
                            precise=True,
                            cdn_supported=self.prof.cdn,
                            location=loc,
                            offset=off,
                            limit=lim,
                        ),
                        timeout=self.prof.invoke_timeout,
                        sleep_threshold=self.prof.sleep_threshold,
                    )
                if isinstance(r, raw.types.upload.File):
                    return r.bytes
                if isinstance(r, raw.types.upload.FileCdnRedirect):
                    self.prof = replace(self.prof, cdn=False)
                    continue
                raise StreamAbort(f"unexpected GetFile response {type(r)}")
            except (FileReferenceExpired, FileReferenceInvalid):
                if refreshes >= 2:
                    raise StreamAbort("file reference kept expiring") from None
                refreshes += 1
                await self._refresh_loc(ci, gen)
            except FileMigrate as e:
                await POOL.drop(ci, self._dc[ci])
                self._dc[ci] = e.value
            except (FloodWait, FloodPremiumWait) as e:
                if e.value > 30 or self._dead:
                    POOL.cool(ci, e.value)
                    raise StreamAbort(f"flood wait {e.value}s on client {ci}") from None
                await sleep(e.value + 1)
            except (ConnectionError, OSError, TimeoutError):
                attempt += 1
                if attempt > self.prof.retries:
                    POOL.cool(ci, 30)
                    raise StreamAbort(f"client {ci} unreachable") from None
                await POOL.drop(ci, self._dc[ci])

    async def iter_range(self, start, end_incl):
        end_ex = end_incl + 1
        plan = plan_chunks(start, end_ex, self.prof)
        window = self.prof.window
        inflight = {}
        ready = {}
        nxt = launch = sent = 0
        try:
            while nxt < len(plan):
                while (len(inflight) + len(ready)) < window and launch < len(plan):
                    off, lim = plan[launch]
                    ci = self._idxs[launch % len(self._idxs)]
                    inflight[ensure_future(self._fetch(ci, off, lim))] = launch
                    launch += 1
                while nxt not in ready:
                    if not inflight:
                        raise StreamAbort("pipeline stalled with no work in flight")
                    done, _ = await wait(set(inflight), return_when=FIRST_COMPLETED)
                    for f in done:
                        ready[inflight.pop(f)] = f.result()
                data = ready.pop(nxt)
                off, lim = plan[nxt]
                nxt += 1
                lo = max(start, off) - off
                hi = min(end_ex, off + lim) - off
                if len(data) < hi:
                    LOGGER.error(
                        f"HypertgStream short read at {off}: got {len(data)} want {hi}"
                    )
                    hi = len(data)
                    if hi <= lo:
                        break
                piece = data if (lo == 0 and hi == len(data)) else data[lo:hi]
                del data
                if piece:
                    sent += len(piece)
                    yield piece
                if hi < min(lim, end_ex - off):
                    break
            if sent != end_ex - start:
                LOGGER.error(
                    f"HypertgStream length mismatch sent={sent} want={end_ex - start}"
                )
        finally:
            self._dead = True
            _drain_in_background(inflight, self.prof.invoke_timeout)
            ready.clear()
            await self._release()


async def open_stream(chat_id, msg_id, kind, viewer=None):
    return await HypertgStream(chat_id, msg_id, profile(kind), viewer=viewer).open()


async def probe(chat_id, msg_id):
    clients, _, _ = POOL.resolve()
    if not clients:
        raise NoClientAvailable("no stream or helper bots are running")
    POOL.ensure_pool(clients)
    ci = next(iter(clients))
    fid = await get_fid(ci, clients[ci], chat_id, msg_id)
    return {
        "name": getattr(fid, "file_name", "") or "",
        "size": int(getattr(fid, "file_size", 0) or 0),
        "mime": getattr(fid, "mime_type", "") or "",
        "unique_id": getattr(fid, "unique_id", "") or "",
    }


async def shutdown():
    pending = [t for t in _BG if not t.done()]
    for t in pending:
        t.cancel()
    if pending:
        await gather(*pending, return_exceptions=True)
    try:
        await POOL.stop()
    except CancelledError:
        raise
    except Exception as e:
        LOGGER.warning(f"HypertgStream shutdown: {e}")
