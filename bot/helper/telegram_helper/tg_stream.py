from asyncio import (
    FIRST_COMPLETED,
    CancelledError,
    Lock,
    Semaphore,
    ensure_future,
    gather,
    get_running_loop,
    shield,
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

_GATE = None
_inflight_chunks = {}


def _swallow(fut):
    if not fut.cancelled():
        fut.exception()


def gate():
    global _GATE
    if _GATE is None:
        _GATE = Semaphore(max(8, int(getattr(Config, "STREAM_GATE", 0) or 96)))
    return _GATE


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
                max_per_client=max(1, int(Config.STREAM_PER_CLIENT or 6)),
                retries=2,
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
            StreamProfile(
                name="probe",
                first_chunk=bulk_chunk,
                max_chunk=bulk_chunk,
                window=max(2, bulk_window // 2),
                clients=1,
                invoke_timeout=15.0,
                sleep_threshold=10,
                cdn=True,
                max_per_client=2,
                retries=1,
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
            _fid_locks.pop(key, None)
            raise StreamGone(f"msg {msg_id} missing from {chat_id}")
        try:
            fid = _fid_of(msg)
        except ValueError:
            _fid_cache.pop(key, None)
            _fid_locks.pop(key, None)
            raise StreamGone(f"msg {msg_id} carries no media") from None
        _fid_cache[key] = (fid, monotonic())
        _evict_fids()
        return fid


def _fid_of(msg):
    media = media_of(msg)
    fid = FileId.decode(media.file_id)
    fid.file_size = getattr(media, "file_size", 0)
    fid.mime_type = getattr(media, "mime_type", "") or ""
    fid.file_name = getattr(media, "file_name", "") or ""
    fid.unique_id = getattr(media, "file_unique_id", "") or ""
    return fid


def _evict_fids():
    while len(_fid_cache) > _FID_MAX:
        old, _ = _fid_cache.popitem(last=False)
        _fid_locks.pop(old, None)
    if len(_fid_locks) > _FID_MAX * 2:
        for key in [k for k in _fid_locks if k not in _fid_cache]:
            _fid_locks.pop(key, None)


_PREFETCH_BLOCK = 100


async def _prime(ci, client, chat_id, msg_ids):
    want = []
    now = monotonic()
    for mid in msg_ids:
        hit = _fid_cache.get((ci, chat_id, mid))
        if hit and now - hit[1] < _FID_TTL:
            continue
        want.append(mid)
    if len(want) < 2:
        return
    for at in range(0, len(want), _PREFETCH_BLOCK):
        block = want[at : at + _PREFETCH_BLOCK]
        try:
            msgs = await client.get_messages(chat_id, block)
        except Exception as e:
            LOGGER.debug(f"fid prefetch failed for {chat_id}: {e}")
            return
        if not isinstance(msgs, list):
            msgs = [msgs]
        stamp = monotonic()
        for msg in msgs:
            if msg is None or getattr(msg, "empty", False):
                continue
            try:
                fid = _fid_of(msg)
            except ValueError:
                continue
            _fid_cache[(ci, chat_id, int(msg.id))] = (fid, stamp)
    _evict_fids()


async def prefetch(pairs):
    clients, _, _ = POOL.resolve()
    if not clients:
        return
    POOL.ensure_pool(clients)
    ci = next(iter(clients))
    client = clients[ci]
    groups = {}
    for cid, mid in pairs:
        groups.setdefault(int(cid), set()).add(int(mid))
    for cid, mids in groups.items():
        await _prime(ci, client, cid, sorted(mids))


def purge_fid(chat_id, msg_id):
    for k in [k for k in _fid_cache if k[1] == chat_id and k[2] == msg_id]:
        _fid_cache.pop(k, None)
        _fid_locks.pop(k, None)


_BG = set()


def _background(coro):
    task = ensure_future(coro)
    _BG.add(task)
    task.add_done_callback(_BG.discard)
    return task


def _retire(pool):
    async def _shut():
        try:
            await pool.stop()
        except Exception as e:
            LOGGER.warning(f"stream session pool retire: {e}")

    _background(_shut())


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

    _background(_drain())


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
            old = self._pool
            self._pool = MtprotoPool(clients)
            self._clients = clients
            self._touched.clear()
            if old is not None:
                _retire(old)
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
                    return [got[0]], loads
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
            return picked, loads

    async def release(self, booked):
        async with self._lock:
            for ci, loads in booked:
                loads[ci] = max(0, loads.get(ci, 0) - 1)

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
        self._book = []
        self._loc = {}
        self._dc = {}
        self._dead = False
        self._released = False

    async def open(self):
        key = (self.chat_id, self.msg_id, self.viewer) if self.viewer else None
        picked, loads = await POOL.acquire(
            self.prof, self.prof.clients, sticky_key=key
        )
        self._idxs = picked
        self._book = [(ci, loads) for ci in picked]
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
            await shield(self._release())
            raise
        if not self.size:
            await shield(self._release())
            raise StreamGone("media has no size")
        return self

    async def _release(self):
        if self._released:
            return
        self._released = True
        if self._book:
            booked, self._book = self._book, []
            await POOL.release(booked)

    async def _refresh_loc(self, ci, seen_gen):
        cur_gen, _ = self._loc[ci]
        if cur_gen != seen_gen:
            return
        fid = await get_fid(ci, POOL.client(ci), self.chat_id, self.msg_id, force=True)
        self._dc[ci] = fid.dc_id
        self._loc[ci] = (cur_gen + 1, HypertgTransfer._location(fid))

    async def _fetch(self, ci, off, lim):
        key = (self.chat_id, self.msg_id, off, lim)
        shared = _inflight_chunks.get(key)
        if shared is not None:
            try:
                return await shield(shared)
            except CancelledError:
                if not shared.cancelled():
                    raise
            except Exception:
                pass
        fut = get_running_loop().create_future()
        fut.add_done_callback(_swallow)
        _inflight_chunks[key] = fut
        try:
            data = await self._pull(ci, off, lim)
            if not fut.done():
                fut.set_result(data)
            return data
        except CancelledError:
            if not fut.done():
                fut.cancel()
            raise
        except BaseException as e:
            if not fut.done():
                fut.set_exception(e)
            raise
        finally:
            if _inflight_chunks.get(key) is fut:
                del _inflight_chunks[key]
            if not fut.done():
                fut.cancel()

    async def _swap_client(self, ci):
        try:
            picked, loads = await POOL.acquire(self.prof, 1)
        except NoClientAvailable:
            return None
        new = picked[0]
        if new == ci:
            await POOL.release([(new, loads)])
            return None
        try:
            fid = await get_fid(new, POOL.client(new), self.chat_id, self.msg_id)
        except Exception:
            await POOL.release([(new, loads)])
            return None
        self._loc[new] = (0, HypertgTransfer._location(fid))
        self._dc[new] = fid.dc_id
        self._idxs = [new if x == ci else x for x in self._idxs]
        held = [b for b in self._book if b[0] == ci][:1]
        self._book = [b for b in self._book if b[0] != ci]
        self._book.append((new, loads))
        if held:
            await POOL.release(held)
        LOGGER.info(f"HypertgStream failed over from client {ci} to {new}")
        return new

    async def _pull(self, ci, off, lim):
        refreshes = 0
        attempt = 0
        while True:
            if self._dead:
                return b""
            gen, loc = self._loc[ci]
            try:
                async with gate():
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
                if self._dead:
                    raise StreamAbort("stream closed") from None
                POOL.cool(ci, e.value)
                if e.value > 5:
                    nxt = await self._swap_client(ci)
                    if nxt is not None:
                        ci = nxt
                        continue
                if e.value > 30:
                    raise StreamAbort(f"flood wait {e.value}s on client {ci}") from None
                await sleep(e.value + 1)
            except (ConnectionError, OSError, TimeoutError):
                attempt += 1
                await POOL.drop(ci, self._dc[ci])
                if attempt > self.prof.retries:
                    POOL.cool(ci, 30)
                    nxt = await self._swap_client(ci)
                    if nxt is None:
                        raise StreamAbort(f"client {ci} unreachable") from None
                    ci = nxt
                    attempt = 0

    async def iter_range(self, start, end_incl):
        end_ex = end_incl + 1
        plan = plan_chunks(start, end_ex, self.prof)
        window = self.prof.window
        wmax = window * 3
        streak = 0
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
                streak += 1
                if streak >= window and window < wmax:
                    window += 1
                    streak = 0
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
            await shield(self._release())


_REAP_EVERY = 300
_reaper = None


async def _reap_loop():
    while True:
        await sleep(_REAP_EVERY)
        try:
            await POOL.reap_idle()
        except CancelledError:
            raise
        except Exception as e:
            LOGGER.warning(f"idle session reaper: {e}")


def start_reaper():
    global _reaper
    if _reaper is None or _reaper.done():
        _reaper = ensure_future(_reap_loop())
    return _reaper


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


_POSTER_MAX = 8 * 1024 * 1024


async def poster_bytes(chat_id, msg_id):
    clients, _, _ = POOL.resolve()
    if not clients:
        raise NoClientAvailable("no stream or helper bots are running")
    ci = next(iter(clients))
    client = clients[ci]
    msg = await client.get_messages(chat_id, msg_id)
    if msg is None or getattr(msg, "empty", False):
        raise StreamGone(f"msg {msg_id} missing from {chat_id}")
    media = media_of(msg)
    mime = getattr(media, "mime_type", None)
    if mime is None or mime.startswith("image/"):
        target = media
    else:
        thumbs = getattr(media, "thumbs", None)
        if not thumbs:
            raise StreamGone(f"msg {msg_id} carries no artwork")
        target = max(thumbs, key=lambda t: getattr(t, "file_size", 0) or 0)
    if (getattr(target, "file_size", 0) or 0) > _POSTER_MAX:
        raise StreamGone(f"msg {msg_id} artwork is too large")
    buf = await client.download_media(target, in_memory=True)
    if buf is None:
        raise StreamGone(f"msg {msg_id} artwork could not be read")
    data = buf.getvalue() if hasattr(buf, "getvalue") else bytes(buf)
    if not data:
        raise StreamGone(f"msg {msg_id} artwork is empty")
    return data


async def shutdown():
    global _reaper
    if _reaper is not None:
        _reaper.cancel()
        await gather(_reaper, return_exceptions=True)
        _reaper = None
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
