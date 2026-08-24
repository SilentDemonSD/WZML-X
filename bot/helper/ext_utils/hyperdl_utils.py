import os
from itertools import cycle
from asyncio import (
    FIRST_COMPLETED,
    CancelledError,
    Lock,
    create_task,
    ensure_future,
    gather,
    sleep,
    to_thread,
    wait,
)
from datetime import datetime
from mimetypes import guess_extension
from os import cpu_count
from pathlib import Path
from re import sub
from sys import argv

from aiofiles.os import makedirs
from pyrogram import StopTransmission, raw
from pyrogram.crypto.aes import ctr256_decrypt
from pyrogram.errors import (
    FileMigrate,
    FileReferenceExpired,
    FileReferenceInvalid,
    FileTokenInvalid,
    FloodPremiumWait,
    FloodWait,
    RequestTokenInvalid,
)
from pyrogram.file_id import PHOTO_TYPES, FileId, FileType
from pyrogram.session import Auth
from pyrogram.session.internals import MsgId
from pyrogram.session import Session

from ... import LOGGER
from ...core.config_manager import Config
from ...core.tg_client import TgClient
from ..telegram_helper.tg_transfer import MB, HypertgTransfer, media_of

_load_lock = Lock()


async def _pick_clients(wl, clients, count):
    keys = list(clients.keys())
    async with _load_lock:
        picked = sorted(keys, key=lambda i: wl.get(i, 0))[:count]
        for k in picked:
            wl[k] = wl.get(k, 0) + 1
    return picked


class HypertgDownload(HypertgTransfer):
    KB = 1024
    _MIN_CHUNK = 64 * KB
    _DEFAULT_PIPELINE = 32
    _MIN_PIPELINE = 4
    _MAX_PIPELINE_MULT = 4
    _LOW_WORKERS = 2
    _HIGH_WORKERS = max(8, (cpu_count() or 4) * 2)
    _MAX_RETRIES = 4

    def __init__(self, obj):
        super().__init__(obj)
        self.chunk_size = max(Config.HYPER_CHUNK or 256 * self.KB, self._MIN_CHUNK)
        self.num_parts = Config.HYPER_THREADS or max(
            self._LOW_WORKERS, min(self._HIGH_WORKERS, self.num_clients)
        )
        base_pipe = max(
            Config.HYPER_PIPELINE or self._DEFAULT_PIPELINE, self._MIN_PIPELINE
        )
        self.pipeline_depth = max(
            base_pipe // max(self.num_parts, 1), self._MIN_PIPELINE
        )
        self.message = None
        self.media = None
        self.dump_chat = None
        self.directory = None
        self.file_name = ""
        self.file_size = 0
        self.download_dir = "downloads/"
        self._ref_cache = {}
        self._cdn_info = {}
        self._cdn_sessions = {}

    def _ref_get(self, idx):
        return self._ref_cache.get(idx)

    def _ref_put(self, idx, data):
        if len(self._ref_cache) > 100:
            self._ref_cache.pop(next(iter(self._ref_cache)))
        self._ref_cache[idx] = data

    async def _fetch_ref(self, idx, client, force=False):
        if not force:
            cached = self._ref_get(idx)
            if cached is not None:
                return cached
        fid = await self._fetch_ref_try(client)
        if fid:
            self._ref_put(idx, fid)
            return fid
        LOGGER.warning(
            "HypertgDL ref ci=%d: client can't access dump_chat=%s, trying bots",
            idx,
            self.dump_chat,
        )
        for cix, cl in self.clients.items():
            if cix > 0:  # bot clients only
                fid = await self._fetch_ref_try(cl)
                if fid:
                    self._ref_put(idx, fid)
                    return fid
        raise ValueError(
            f"no file_id in msg {self.message.id} in dump_chat={self.dump_chat} (all clients failed)"
        )

    async def _fetch_ref_try(self, client):
        try:
            msg = await client.get_messages(self.dump_chat, self.message.id)
            if msg is None:
                LOGGER.warning(
                    "HypertgDL _fetch_ref_try: msg %s not found in %s",
                    self.message.id,
                    self.dump_chat,
                )
                return None
            media = self._media_of(msg)
            fid_str = media.file_id if hasattr(media, "file_id") else None
            if not fid_str:
                return None
            return FileId.decode(fid_str)
        except Exception as e:
            LOGGER.warning("HypertgDL _fetch_ref_try: %s", e)
            return None

    @staticmethod
    def _media_of(message):
        return media_of(message)

    async def _do_req(self, sess, client, location, off, csz, attempt=0):
        try:
            r = await sess.invoke(
                raw.functions.upload.GetFile(
                    precise=True,
                    cdn_supported=True,
                    location=location,
                    offset=off,
                    limit=csz,
                ),
                sleep_threshold=client.sleep_threshold,
            )
            if isinstance(r, raw.types.upload.File):
                return r.bytes
            if isinstance(r, raw.types.upload.FileCdnRedirect):
                return None, {
                    "cdn_dc": r.dc_id,
                    "file_token": r.file_token,
                    "key": r.encryption_key,
                    "iv": r.encryption_iv,
                }
            raise ValueError(f"Unexpected response type: {type(r)}")
        except FileMigrate as e:
            dc = e.value if hasattr(e, "value") else int(str(e).split()[-1])
            if attempt < 3:
                return None, dc
            raise
        except (FileReferenceExpired, FileReferenceInvalid):
            if attempt < 3:
                return None, -1
            raise
        except (ConnectionError, OSError, TimeoutError):
            if attempt < 3:
                return None, -2
            raise

    async def _get_cdn_session(self, idx, cdn_dc, client):
        key = (idx, cdn_dc)
        s = self._cdn_sessions.get(key)
        if s and s.is_started.is_set():
            return s
        tm = await client.storage.test_mode()
        ak = await Auth(client, cdn_dc, tm).create()
        s = Session(client, cdn_dc, ak, tm, is_media=True, is_cdn=True)
        await s.start()
        self._cdn_sessions[key] = s
        return s

    async def _cdnpull(self, idx, cdn_info, off, csz):
        client = self.clients[idx]
        cdn_dc = cdn_info["cdn_dc"]
        file_token = cdn_info["file_token"]
        enc_key = cdn_info["key"]
        enc_iv = cdn_info["iv"]
        sess = await self._get_cdn_session(idx, cdn_dc, client)

        for attempt in range(3):
            try:
                r = await sess.invoke(
                    raw.functions.upload.GetCdnFile(
                        file_token=file_token,
                        offset=off,
                        limit=csz,
                    ),
                    sleep_threshold=client.sleep_threshold,
                )
                if isinstance(r, raw.types.upload.CdnFile):
                    chunk = r.bytes
                    iv_mod = bytearray(enc_iv[:-4] + (off // 16).to_bytes(4, "big"))
                    return ctr256_decrypt(chunk, enc_key, iv_mod)
                if isinstance(r, raw.types.upload.CdnFileReuploadNeeded):
                    try:
                        await client.invoke(
                            raw.functions.upload.ReuploadCdnFile(
                                file_token=file_token,
                                request_token=r.request_token,
                            )
                        )
                    except Exception:
                        pass
                    await sleep(1)
                    continue
                raise ValueError(f"Unexpected CDN response: {type(r)}")
            except (FloodWait, FloodPremiumWait) as e:
                val = e.value if hasattr(e, "value") else 5
                LOGGER.warning(f"HypertgDL CDN flood {val}s dc={cdn_dc}")
                await sleep(val + 1)
            except FileTokenInvalid:
                LOGGER.warning(
                    f"HypertgDL CDN FileTokenInvalid dc={cdn_dc} — fallback to non-CDN"
                )
                self._cdn_info.pop(idx, None)
                return None
            except RequestTokenInvalid:
                LOGGER.warning(
                    f"HypertgDL CDN RequestTokenInvalid dc={cdn_dc} — fallback to non-CDN"
                )
                self._cdn_info.pop(idx, None)
                return None
            except (ConnectionError, OSError, TimeoutError) as e:
                LOGGER.warning(f"HypertgDL CDN {type(e).__name__}: {e} dc={cdn_dc}")
                if attempt < 2:
                    try:
                        await sess.stop()
                    except Exception:
                        pass
                    self._cdn_sessions.pop((idx, cdn_dc), None)
                    sess = await self._get_cdn_session(idx, cdn_dc, client)
                    await sleep(1)
        return None

    async def _pipeline_fetch(self, idx, location, start, end, fid, csz, fd):
        cname = self.clients[idx].me.username
        sess = await self._get_session(idx, fid.dc_id)
        loc = location
        first_off = start - (start % csz)
        first_trim = start - first_off
        last_byte = end - 1
        window = self.pipeline_depth
        min_win = self._MIN_PIPELINE
        max_win = window * self._MAX_PIPELINE_MULT
        inflight = set()
        _inflight_offsets = {}
        cur = first_off
        seq = 0
        ok_count = 0
        flood_count = 0
        timeout_count = 0
        pipe_timeouts = 0
        bot_down = False

        async def _write(roff, chunk):
            if roff == first_off and roff + csz >= end:
                chunk = chunk[first_trim : last_byte - roff + 1]
                await self._pwrite(fd, chunk, start)
            elif roff == first_off:
                chunk = chunk[first_trim:]
                await self._pwrite(fd, chunk, start)
            elif roff + csz > end:
                chunk = chunk[: end - roff]
                await self._pwrite(fd, chunk, roff)
            else:
                await self._pwrite(fd, chunk, roff)
            self._obj._processed_bytes += len(chunk)

        async def _req(off, s):
            nonlocal \
                window, \
                ok_count, \
                flood_count, \
                timeout_count, \
                sess, \
                loc, \
                pipe_timeouts, \
                bot_down
            if bot_down:
                return s, off, b""
            my_sess = sess
            my_loc = loc
            max_attempts = 1
            for attempt in range(max_attempts):
                try:
                    cdn = self._cdn_info.get(idx)
                    if cdn:
                        chunk = await self._cdnpull(idx, cdn, off, csz)
                        if chunk is not None:
                            return s, off, chunk
                    result = await self._do_req(
                        my_sess, self.clients[idx], my_loc, off, csz, attempt
                    )
                    if isinstance(result, tuple):
                        _, dc_or_ref = result
                        if isinstance(dc_or_ref, dict):
                            self._cdn_info[idx] = dc_or_ref
                            chunk = await self._cdnpull(idx, dc_or_ref, off, csz)
                            if chunk is not None:
                                return s, off, chunk
                            self._cdn_info.pop(idx, None)
                            await sleep(attempt + 1)
                            continue
                        if dc_or_ref == -1:
                            fid_new = await self._fetch_ref(
                                idx, self.clients[idx], force=True
                            )
                            my_loc = self._location(fid_new)
                            await sleep(attempt + 1)
                            continue
                        if dc_or_ref == -2:
                            if bot_down:
                                return s, off, b""
                            pipe_timeouts += 1
                            window = max(min_win, window - 1)
                            if pipe_timeouts >= 3:
                                bot_down = True
                                return s, off, b""
                            await sleep(min(3, pipe_timeouts))
                            continue
                        my_sess = await self._get_session(idx, dc_or_ref, force=True)
                        sess = my_sess
                        await sleep(attempt + 1)
                        continue
                    timeout_count = 0
                    return s, off, result
                except (FloodWait, FloodPremiumWait) as e:
                    flood_count += 1
                    val = e.value if hasattr(e, "value") else 5
                    if val > 10 or flood_count >= 3:
                        window = max(min_win, window - max(1, window // 4))
                        ok_count = 0
                        flood_count = 0
                        LOGGER.warning(
                            f"HypertgDL flood window={window} "
                            f"val={val}s client={cname} off={off}"
                        )
                    await sleep(val + 1)
                except CancelledError:
                    raise
                except (ConnectionError, OSError, TimeoutError):
                    pipe_timeouts += 1
                    window = max(min_win, window - 1)
                    if pipe_timeouts >= 3:
                        bot_down = True
                        return s, off, b""
                    await sleep(min(3, pipe_timeouts))
                    continue
            timeout_count += 1
            if timeout_count >= 3:
                window = max(min_win, window - max(1, window // 4))
                timeout_count = 0
                ok_count = 0
            return s, off, b""

        write_tasks = set()
        failed_offsets = set()
        write_errors = 0
        max_writes = max(max_win, min_win)

        def _reap_writes():
            nonlocal write_errors
            for t in [t for t in write_tasks if t.done()]:
                write_tasks.discard(t)
                if not t.cancelled() and t.exception() is not None:
                    write_errors += 1

        async def _queue_write(roff, chunk):
            write_tasks.add(create_task(_write(roff, chunk)))
            _reap_writes()
            while len(write_tasks) >= max_writes:
                await wait(write_tasks, return_when=FIRST_COMPLETED)
                _reap_writes()

        try:
            while cur <= last_byte or inflight:
                if bot_down:
                    while inflight:
                        done_set, inflight = await wait(
                            inflight, return_when=FIRST_COMPLETED
                        )
                        for f in done_set:
                            known = _inflight_offsets.pop(f, None)
                            try:
                                s, roff, chunk = f.result()
                                if not chunk:
                                    failed_offsets.add(roff)
                                    continue
                                await _queue_write(roff, chunk)
                            except CancelledError:
                                raise
                            except Exception:
                                if known is not None:
                                    failed_offsets.add(known)
                    c = cur
                    while c <= last_byte:
                        failed_offsets.add(c)
                        c += csz
                    break
                while len(inflight) < window and cur <= last_byte:
                    if self._cancel.is_set():
                        raise CancelledError
                    f = ensure_future(_req(cur, seq))
                    _inflight_offsets[f] = cur
                    inflight.add(f)
                    cur += csz
                    seq += 1
                if not inflight:
                    break
                done_set, inflight = await wait(inflight, return_when=FIRST_COMPLETED)
                for f in done_set:
                    _inflight_offsets.pop(f, None)
                    s, roff, chunk = f.result()
                    if not chunk:
                        failed_offsets.add(roff)
                        continue
                    ok_count += 1
                    if ok_count >= window:
                        window = min(window + 2, max_win)
                        ok_count = 0
                    await _queue_write(roff, chunk)
        except CancelledError:
            raise
        except Exception as e:
            if isinstance(e, (FloodWait, FloodPremiumWait)):
                window = max(min_win, window // 2)
                ok_count = 0
            LOGGER.error(f"HypertgDL pipeline fail client={cname}: {e}")
            raise
        finally:
            for f in inflight:
                if not f.done():
                    f.cancel()
            inflight.clear()
            _inflight_offsets.clear()
            if write_tasks:
                write_results = await gather(*write_tasks, return_exceptions=True)
                write_errors += sum(
                    1 for r in write_results if isinstance(r, BaseException)
                )
                write_tasks.clear()
            if write_errors:
                LOGGER.warning(
                    f"HypertgDL {write_errors} write tasks failed client={cname}"
                )
        return failed_offsets

    async def _part(self, start, end, final_path, ci, fid, csz):
        cname = self.clients[ci].me.username
        fd = await to_thread(os.open, final_path, os.O_WRONLY)
        try:
            failed_offsets = await self._pipeline_fetch(
                ci, self._location(fid), start, end, fid, csz, fd
            )
        except Exception as e:
            first_off = start - (start % csz)
            failed_offsets = set(range(first_off, end, csz))
            LOGGER.error(f"HypertgDL part fail ci={ci} client={cname}: {e}")
            e.failed_offsets = failed_offsets
            raise
        finally:
            await to_thread(os.close, fd)
        return failed_offsets

    @staticmethod
    async def _pwrite(fd, data, offset):
        view = memoryview(data)
        total = len(view)
        written = 0
        while written < total:
            n = await to_thread(os.pwrite, fd, view[written:], offset + written)
            if n == 0:
                raise OSError(f"pwrite returned 0 at offset {offset + written}")
            written += n

    async def _retry_failed_offsets(
        self,
        all_failed_offsets,
        bad_bots,
        ranges,
        assigns,
        fid_map,
        final,
        cidx=None,
    ):
        pool = cidx or list(self.clients.keys())
        retry_round = 0
        all_bad_mode = False
        while all_failed_offsets:
            retry_round += 1
            await sleep(1)

            good_bots = sorted(
                [i for i in pool if i not in bad_bots],
                key=lambda i: self.work_loads.get(i, 0),
            )
            if not good_bots:
                fallback = max(bad_bots)
                LOGGER.warning(
                    f"HypertgDL retry: all bots bad, "
                    f"falling back to {self.clients[fallback].me.username}"
                )
                good_bots = [fallback]
                all_bad_mode = True

            if retry_round > self._MAX_RETRIES and not all_bad_mode:
                break
            if all_bad_mode and retry_round > self._MAX_RETRIES + 2:
                LOGGER.warning(
                    f"HypertgDL retry: {len(all_failed_offsets)} offsets still failed "
                    f"after all_bad_mode rounds, giving up"
                )
                break

            range_buckets = {i: [] for i in range(len(ranges))}
            for off in all_failed_offsets:
                for i, (s, e) in enumerate(ranges):
                    if s <= off < e:
                        range_buckets[i].append(off)
                        break
                else:
                    LOGGER.error(f"HypertgDL retry: offset {off} outside all ranges")
                    range_buckets[0].append(off)

            LOGGER.warning(
                f"HypertgDL retry round {retry_round}: "
                f"{len(all_failed_offsets)} failed offsets"
                f"{' (bad bots: ' + str(bad_bots) + ')' if bad_bots else ''}"
            )

            sorted_buckets = sorted(
                [(i, offs) for i, offs in range_buckets.items() if offs],
                key=lambda x: x[0],
            )
            good_bot_cycle = cycle(good_bots) if good_bots else None
            bot_task_map = []
            still_failed = set()
            for i, bucket in sorted_buckets:
                bot_idx = assigns[i]
                if bot_idx in bad_bots:
                    if not good_bot_cycle:
                        still_failed |= set(bucket)
                        continue
                    bot_idx = next(good_bot_cycle)

                if bot_idx not in fid_map:
                    try:
                        fid_map[bot_idx] = await self._fetch_ref(
                            bot_idx, self.clients[bot_idx]
                        )
                    except Exception:
                        bad_bots.add(bot_idx)
                        still_failed |= set(bucket)
                        continue
                retry_start = min(bucket)
                retry_end = min(max(bucket) + self.chunk_size, self.file_size)
                task = create_task(
                    self._part(
                        retry_start,
                        retry_end,
                        final,
                        bot_idx,
                        fid_map[bot_idx],
                        self.chunk_size,
                    )
                )
                bot_task_map.append((bot_idx, bucket, task))

            if not bot_task_map:
                LOGGER.error("HypertgDL retry: no bots available for retry")
                break

            retry_results = await gather(
                *[t for _, _, t in bot_task_map], return_exceptions=True
            )
            for (bot_idx, bucket, _), r in zip(bot_task_map, retry_results):
                if isinstance(r, BaseException):
                    LOGGER.error(
                        f"HypertgDL retry ci={bot_idx} "
                        f"client={self.clients[bot_idx].me.username} "
                        f"failed: {r}"
                    )
                    if hasattr(r, "failed_offsets") and r.failed_offsets:
                        still_failed |= r.failed_offsets
                    else:
                        still_failed |= set(bucket)
                    bad_bots.add(bot_idx)
                elif isinstance(r, set) and r:
                    still_failed |= r
                    bad_bots.add(bot_idx)
            all_failed_offsets = still_failed

        if all_failed_offsets:
            n_bad = len(bad_bots)
            bad_detail = (
                f" ({n_bad} bot{'s' if n_bad != 1 else ''} exhausted)" if n_bad else ""
            )
            LOGGER.error(
                f"HypertgDL {len(all_failed_offsets)} offsets still failed "
                f"after {self._MAX_RETRIES} retry rounds — file may be incomplete"
                f"{bad_detail}"
            )

        return all_failed_offsets, bad_bots

    async def handle_download(self):
        self._cancel.clear()
        self._obj._processed_bytes = 0
        await makedirs(self.directory, exist_ok=True)
        final = os.path.abspath(
            sub("\\\\", "/", os.path.join(self.directory, self.file_name))
        )

        mode = getattr(self._listener, "transmission_mode", "bot")
        bot_clients = {k: v for k, v in self.clients.items() if k > 0}
        user_clients = {k: v for k, v in self.clients.items() if k < 0}

        if mode == "bot":
            use_clients = bot_clients
        elif mode == "user":
            use_clients = user_clients
        else:
            use_clients = self.clients

        if not use_clients:
            LOGGER.error(f"HypertgDL no clients for mode {mode}")
            return None

        use_count = min(self.num_parts, len(use_clients))

        if mode == "both" and bot_clients and user_clients:
            n_bot = min(len(bot_clients), max(1, use_count // 2))
            n_user = min(len(user_clients), use_count - n_bot)
            cidx = await _pick_clients(self.work_loads, bot_clients, n_bot)
            cidx.extend(await _pick_clients(self.work_loads, user_clients, n_user))
        else:
            cidx = await _pick_clients(self.work_loads, use_clients, use_count)

        n_use = len(cidx)
        min_part = 1 * MB
        n_parts = (
            min(n_use, max(1, self.file_size // min_part))
            if self.file_size >= min_part
            else 1
        )
        psz = self.file_size // n_parts if n_parts > 0 else self.file_size
        ranges = [(i * psz, min((i + 1) * psz, self.file_size)) for i in range(n_parts)]
        assigns = [cidx[i % n_use] for i in range(n_parts)]

        unique_clients = set(assigns)
        fid_map = {}
        try:
            for ci in unique_clients:
                fid_map[ci] = await self._fetch_ref(ci, self.clients[ci])
        except Exception as e:
            LOGGER.error(f"HypertgDL ref fail: {e}")
            return None

        first_fid = fid_map[assigns[0]]
        try:
            await self._warmup(unique_clients, first_fid.dc_id)
        except Exception as e:
            LOGGER.warning(f"HypertgDL warmup err: {e}")

        self._tasks = []
        try:
            fd = await to_thread(os.open, final, os.O_WRONLY | os.O_CREAT)
            try:
                await to_thread(os.ftruncate, fd, self.file_size)
            finally:
                await to_thread(os.close, fd)

            all_failed_offsets = set()
            for i, (s, e) in enumerate(ranges):
                self._tasks.append(
                    create_task(
                        self._part(
                            s,
                            e,
                            final,
                            assigns[i],
                            fid_map[assigns[i]],
                            self.chunk_size,
                        )
                    )
                )

            results = await gather(*self._tasks, return_exceptions=True)
            bad_bots = set()
            for i, r in enumerate(results):
                if isinstance(r, BaseException):
                    LOGGER.error(f"HypertgDL part {i} failed: {r}")
                    bad_bots.add(assigns[i])
                    if hasattr(r, "failed_offsets") and r.failed_offsets:
                        all_failed_offsets.update(r.failed_offsets)
                    else:
                        s, e = ranges[i]
                        LOGGER.warning(
                            f"HypertgDL part {i} missing failed_offsets — "
                            f"retrying full range {s}-{e}"
                        )
                        all_failed_offsets.update(range(s, e, self.chunk_size))
                elif isinstance(r, set) and r:
                    all_failed_offsets.update(r)
                    bad_bots.add(assigns[i])
            all_failed_offsets, bad_bots = await self._retry_failed_offsets(
                all_failed_offsets,
                bad_bots,
                ranges,
                assigns,
                fid_map,
                final,
                cidx=cidx,
            )

            return final
        except FloodWait:
            raise
        except (CancelledError, StopTransmission):
            return None
        except Exception as e:
            LOGGER.error(f"HypertgDL: {e}")
            return None
        finally:
            self._cancel.set()
            for t in self._tasks:
                if not t.done():
                    t.cancel()
            if self._tasks:
                await gather(*self._tasks, return_exceptions=True)
            async with _load_lock:
                for k in cidx:
                    self.work_loads[k] = max(0, self.work_loads.get(k, 0) - 1)
            for s in self._cdn_sessions.values():
                try:
                    if s.is_started.is_set():
                        await s.stop()
                except Exception:
                    pass
            self._cdn_sessions.clear()
            self._cdn_info.clear()
            await self._close_all()

    async def download_media(self, message, file_name="downloads/", dump_chat=None):
        try:
            if dump_chat and not isinstance(dump_chat, int):
                try:
                    dump_chat = int(dump_chat)
                except (ValueError, TypeError):
                    dump_chat = None
            if dump_chat and dump_chat == message.chat.id:
                dump_chat = None
            if dump_chat:
                try:
                    self.message = await TgClient.bot.copy_message(
                        chat_id=dump_chat,
                        from_chat_id=message.chat.id,
                        message_id=message.id,
                        disable_notification=True,
                    )
                except Exception as e:
                    LOGGER.warning(
                        f"HypertgDL copy fail: {e} (from={message.chat.id} to={dump_chat})"
                    )
                    raise RuntimeError(f"Cannot copy to dump chat: {e}") from e
            self.dump_chat = dump_chat or message.chat.id
            self.message = self.message or message
            self.media = self._media_of(self.message)
            media = self.media
            fid_str = media if isinstance(media, str) else media.file_id
            fid_obj = FileId.decode(fid_str)
            ftype = fid_obj.file_type
            mname = media.file_name if hasattr(media, "file_name") else ""
            self.file_size = media.file_size if hasattr(media, "file_size") else 0
            mime = media.mime_type if hasattr(media, "mime_type") else "image/jpeg"
            dt = media.date if hasattr(media, "date") else None
            self.directory, self.file_name = os.path.split(file_name)
            self.file_name = self.file_name or mname or ""
            if not os.path.isabs(self.file_name):
                self.directory = Path(argv[0]).parent / (
                    self.directory or self.download_dir
                )
            if not self.file_name:
                ext = self._ext(ftype, mime)
                self.file_name = (
                    f"{FileType(ftype).name.lower()}_"
                    f"{(dt or datetime.now()).strftime('%Y-%m-%d_%H-%M-%S')}_"
                    f"{MsgId()}{ext}"
                )
            return await self.handle_download()
        except Exception as e:
            LOGGER.error(f"HypertgDL download_media: {e}")
            raise

    @staticmethod
    def _ext(ft, mime):
        if ft in PHOTO_TYPES:
            return ".jpg"
        if mime:
            e = guess_extension(mime)
            if e:
                return e
        return {
            FileType.VOICE: ".ogg",
            FileType.VIDEO: ".mp4",
            FileType.ANIMATION: ".mp4",
            FileType.VIDEO_NOTE: ".mp4",
            FileType.AUDIO: ".mp3",
            FileType.STICKER: ".webp",
        }.get(ft, ".bin")
