from asyncio import (
    CancelledError,
    create_subprocess_exec,
    ensure_future,
    get_running_loop,
    shield,
    wait_for,
)
from collections import OrderedDict
from json import loads
from os import getenv
from re import compile as re_compile
from subprocess import PIPE
from time import monotonic, time
from urllib.parse import quote

from aiohttp import web

from .. import LOGGER, bot_loop
from .cpu import service_cores
from .config_manager import BinConfig
from ..helper.ext_utils.db_handler import database
from ..helper.ext_utils.mem_guard import register_cache
from ..helper.ext_utils.split_parts import split_trims
from ..helper.telegram_helper.tg_stream import (
    FULL,
    NoClientAvailable,
    StreamAbort,
    StreamGone,
    open_stream,
    parse_range,
    poster_bytes,
    prefetch,
    probe,
    purge_fid,
    shutdown,
    start_reaper,
)

_TOKEN_RE = re_compile(r"^[A-Za-z0-9_-]{4,32}$")
_PLAYABLE = ("video/", "audio/")
_runner = None

_PROBE_BYTES = 6 * 1024 * 1024
_PROBE_TIMEOUT = 45
_PROBE_KEEP = 128
_probe_cache = OrderedDict()

_LIST_KEEP = 64
_list_cache = OrderedDict()

_MERGE_KEEP = 64
_merge_cache = OrderedDict()

_PARTIAL_TTL = 60
_body_inflight = {}

_POSTER_KEEP = 256
_POSTER_MISS_TTL = 300
_poster_cache = OrderedDict()

_VTT_TOTAL_MAX = 48 * 1024 * 1024
_VTT_ENTRY_MAX = 6 * 1024 * 1024
_vtt_cache = OrderedDict()
_vtt_bytes = 0


def _cache_bytes():
    total = _vtt_bytes
    for value in _poster_cache.values():
        body = value[0] if isinstance(value, tuple) else value
        total += len(body) if isinstance(body, (bytes, bytearray)) else 0
    return total


def _cache_trim(aggressive=False):
    global _vtt_bytes
    if aggressive:
        _vtt_cache.clear()
        _vtt_bytes = 0
        _poster_cache.clear()
        _list_cache.clear()
        _merge_cache.clear()
        _probe_cache.clear()
        return
    keep = max(1, len(_vtt_cache) // 2)
    while len(_vtt_cache) > keep:
        _, dropped = _vtt_cache.popitem(last=False)
        body = dropped[0] if isinstance(dropped, tuple) else dropped
        _vtt_bytes -= len(body) if isinstance(body, (bytes, bytearray)) else 0
    _vtt_bytes = max(0, _vtt_bytes)
    keep = max(1, len(_poster_cache) // 2)
    while len(_poster_cache) > keep:
        _poster_cache.popitem(last=False)
    keep = max(1, len(_probe_cache) // 2)
    while len(_probe_cache) > keep:
        _probe_cache.popitem(last=False)


register_cache("stream", _cache_bytes, _cache_trim)
_vtt_inflight = {}
_LANG = {
    "eng": "English", "jpn": "Japanese", "spa": "Spanish", "fre": "French",
    "fra": "French", "ger": "German", "deu": "German", "ita": "Italian",
    "por": "Portuguese", "rus": "Russian", "hin": "Hindi", "tam": "Tamil",
    "tel": "Telugu", "ben": "Bengali", "kor": "Korean", "chi": "Chinese",
    "zho": "Chinese", "ara": "Arabic", "tur": "Turkish", "pol": "Polish",
    "dut": "Dutch", "nld": "Dutch", "swe": "Swedish", "tha": "Thai",
    "vie": "Vietnamese", "ind": "Indonesian", "mal": "Malayalam",
    "kan": "Kannada", "mar": "Marathi", "urd": "Urdu", "fil": "Filipino",
}


def _title(stream, n):
    tags = stream.get("tags") or {}
    name = tags.get("title") or ""
    lang = (tags.get("language") or "").lower()
    pretty = _LANG.get(lang, lang.upper() if lang and lang != "und" else "")
    codec = (stream.get("codec_name") or "").upper()
    ch = stream.get("channels")
    bits = [b for b in (name, pretty) if b]
    label = " · ".join(dict.fromkeys(bits)) if bits else "Track %d" % (n + 1)
    extra = []
    if codec:
        extra.append(codec)
    if ch == 6:
        extra.append("5.1")
    elif ch == 8:
        extra.append("7.1")
    elif ch == 2:
        extra.append("Stereo")
    if stream.get("disposition", {}).get("forced"):
        extra.append("Forced")
    if extra:
        label += "  (" + ", ".join(extra) + ")"
    return label


async def _prefix(cid, mid, size):
    st = await open_stream(cid, mid, "probe")
    end = min(size, _PROBE_BYTES) - 1
    gen = st.iter_range(0, end)
    buf = bytearray()
    try:
        async for chunk in gen:
            buf.extend(chunk)
    finally:
        await gen.aclose()
    return bytes(buf)


async def _probe(cid, mid):
    key = (cid, mid)
    if key in _probe_cache:
        _probe_cache.move_to_end(key)
        return _probe_cache[key]
    return await _once(("probe", cid, mid), lambda: _build_probe(cid, mid))


def _reap_proc(proc):
    if proc.returncode is not None:
        return
    try:
        proc.kill()
    except Exception:
        return
    ensure_future(_wait_quietly(proc))


async def _wait_quietly(proc):
    try:
        await wait_for(proc.wait(), timeout=10)
    except Exception:
        pass


async def _build_probe(cid, mid):
    key = (cid, mid)
    if key in _probe_cache:
        _probe_cache.move_to_end(key)
        return _probe_cache[key]
    info = await probe(cid, mid)
    raw = await _prefix(cid, mid, info["size"] or _PROBE_BYTES)
    proc = await create_subprocess_exec(
        *_nice(["ffprobe", "-hide_banner", "-loglevel", "error",
                "-print_format", "json", "-show_streams", "-"]),
        stdin=PIPE, stdout=PIPE, stderr=PIPE,
    )
    try:
        try:
            out, _ = await wait_for(proc.communicate(raw), timeout=_PROBE_TIMEOUT)
        except Exception:
            out = b""
    finally:
        _reap_proc(proc)
    streams = []
    try:
        streams = loads(out)["streams"]
    except Exception:
        streams = []
    audio, subtitle = [], []
    for st_ in streams:
        kind = st_.get("codec_type")
        if kind == "audio":
            audio.append(
                {
                    "index": len(audio),
                    "title": _title(st_, len(audio)),
                    "codec": (st_.get("codec_name") or "").lower(),
                }
            )
        elif kind == "subtitle":
            codec = (st_.get("codec_name") or "").lower()
            if codec in ("dvd_subtitle", "hdmv_pgs_subtitle", "dvb_subtitle"):
                continue
            subtitle.append(
                {"index": len(subtitle), "title": _title(st_, len(subtitle))}
            )
    result = {"audio": audio, "subtitle": subtitle}
    _probe_cache[key] = result
    while len(_probe_cache) > _PROBE_KEEP:
        _probe_cache.popitem(last=False)
    return result


def purge_probe(cid, mid):
    _probe_cache.pop((cid, mid), None)


def _gone(cid, mid):
    purge_fid(cid, mid)
    purge_probe(cid, mid)


def _cached(store, token):
    hit = store.get(token)
    if hit is None:
        return None
    body, until = hit
    if until is not None and monotonic() >= until:
        store.pop(token, None)
        return None
    store.move_to_end(token)
    return body


def _keep(store, token, body, limit, fresh):
    store[token] = (body, None if fresh else monotonic() + _PARTIAL_TTL)
    store.move_to_end(token)
    while len(store) > limit:
        store.popitem(last=False)


async def _once(key, build):
    pending = _body_inflight.get(key)
    if pending is not None:
        try:
            return await shield(pending)
        except CancelledError:
            if not pending.cancelled():
                raise
        except Exception:
            pass
    fut = get_running_loop().create_future()
    fut.add_done_callback(lambda f: None if f.cancelled() else f.exception())
    _body_inflight[key] = fut
    try:
        body = await build()
        if not fut.done():
            fut.set_result(body)
        return body
    except CancelledError:
        if not fut.done():
            fut.cancel()
        raise
    except BaseException as e:
        if not fut.done():
            fut.set_exception(e)
        raise
    finally:
        if _body_inflight.get(key) is fut:
            del _body_inflight[key]
        if not fut.done():
            fut.cancel()


async def _locate(tokens):
    found = await database.get_streams(tokens)
    pairs = [found[tok] for tok in tokens if tok in found]
    if len(pairs) > 1:
        try:
            await prefetch(pairs)
        except Exception as e:
            LOGGER.debug(f"metadata prefetch failed: {e}")
    return found


def stream_port():
    return int(getenv("STREAM_PORT", "") or 8091)


async def _resolve(request):
    token = request.match_info.get("token", "")
    if not _TOKEN_RE.match(token):
        raise web.HTTPNotFound(text="unknown link")
    found = await database.get_stream(token)
    if not found:
        raise web.HTTPNotFound(text="unknown link")
    return token, found[0], found[1], found[2] if len(found) > 2 else None


def _disposition(name, inline):
    kind = "inline" if inline else "attachment"
    if not name:
        return kind
    return f"{kind}; filename*=UTF-8''{quote(name, safe='')}"


async def _neighbours(token):
    nav = await database.get_stream_nav(token)
    if not nav:
        return None
    doc = await database.get_playlist(nav[0])
    if not doc or doc.get("merged"):
        return None
    items = doc["items"]
    if not items:
        return None
    idx = items.index(token) if token in items else nav[1]
    if idx < 0 or idx >= len(items):
        return None
    out = {
        "token": nav[0],
        "name": doc["name"] or "Playlist",
        "index": idx + 1,
        "total": len(items),
        "prev": None,
        "next": None,
    }
    around = [
        items[at] for at in (idx - 1, idx + 1) if 0 <= at < len(items)
    ]
    found = await _locate(around) if around else {}
    for key, at in (("prev", idx - 1), ("next", idx + 1)):
        if at < 0 or at >= len(items):
            continue
        tok = items[at]
        where = found.get(tok)
        if not where:
            continue
        try:
            info = await probe(where[0], where[1])
        except Exception as e:
            LOGGER.debug(f"neighbour probe failed for {tok}: {e}")
            continue
        out[key] = {"token": tok, "name": info.get("name") or "Untitled"}
    return out


async def _meta(request):
    token = request.match_info.get("token", "")
    if not _TOKEN_RE.match(token):
        raise web.HTTPNotFound(text="unknown link")
    found = await database.get_stream(token)
    if not found:
        try:
            body = await _merge_body(token)
        except NoClientAvailable as e:
            raise web.HTTPServiceUnavailable(text=str(e)) from None
        if not body:
            raise web.HTTPNotFound(text="unknown link")
        return web.json_response(
            {
                "name": body["name"],
                "size": body["size"],
                "mime": body["mime"],
                "unique_id": "",
                "playable": True,
                "duration": body["duration"],
                "merge": body,
            }
        )
    cid, mid = found[0], found[1]
    try:
        info = await probe(cid, mid)
    except StreamGone:
        _gone(cid, mid)
        raise web.HTTPNotFound(text="file is gone") from None
    except NoClientAvailable as e:
        raise web.HTTPServiceUnavailable(text=str(e)) from None
    mime = info["mime"]
    info["playable"] = mime.startswith(_PLAYABLE)
    try:
        nav = await _neighbours(token)
    except Exception as e:
        LOGGER.debug(f"playlist nav unavailable for {token}: {e}")
        nav = None
    if nav:
        info["playlist"] = nav
    return web.json_response(info)


def _shelf(exp):
    if not exp:
        return "private, max-age=86400, immutable"
    left = int(exp - time())
    if left <= 0:
        return "no-store"
    return f"private, max-age={min(86400, left)}, must-revalidate"


def _etag_hit(header, tag):
    if not header or not tag:
        return False
    for part in header.split(","):
        part = part.strip()
        if part == "*":
            return True
        if part.startswith("W/"):
            part = part[2:]
        if part == tag:
            return True
    return False


async def _serve(request, kind):
    _, cid, mid, exp = await _resolve(request)
    inline = kind == "playback"
    shelf = _shelf(exp)

    viewer = request.headers.get("X-Viewer") or request.remote
    inm = request.headers.get("If-None-Match")

    if inm and not request.headers.get("Range"):
        try:
            info = await probe(cid, mid)
        except StreamGone:
            _gone(cid, mid)
            raise web.HTTPNotFound(text="file is gone") from None
        except NoClientAvailable as e:
            raise web.HTTPServiceUnavailable(text=str(e)) from None
        tag = f'"{info["unique_id"]}"'
        if info["unique_id"] and _etag_hit(inm, tag):
            return web.Response(
                status=304,
                headers={
                    "ETag": tag,
                    "Cache-Control": shelf,
                    "Accept-Ranges": "bytes",
                },
            )

    if request.method == "HEAD":
        try:
            info = await probe(cid, mid)
        except StreamGone:
            _gone(cid, mid)
            raise web.HTTPNotFound(text="file is gone") from None
        except NoClientAvailable as e:
            raise web.HTTPServiceUnavailable(text=str(e)) from None
        return web.Response(
            status=200,
            headers={
                "Content-Length": str(info["size"]),
                "Content-Type": info["mime"] or "application/octet-stream",
                "Accept-Ranges": "bytes",
                "Content-Disposition": _disposition(info["name"], inline),
                "Cache-Control": shelf,
                "ETag": f'"{info["unique_id"]}"',
            },
        )

    try:
        st = await open_stream(cid, mid, kind, viewer=viewer)
    except StreamGone:
        _gone(cid, mid)
        raise web.HTTPNotFound(text="file is gone") from None
    except NoClientAvailable as e:
        raise web.HTTPServiceUnavailable(text=str(e), headers={"Retry-After": "10"})
    except StreamAbort as e:
        raise web.HTTPBadGateway(text=str(e)) from None

    rng = parse_range(request.headers.get("Range"), st.size)
    if rng is None:
        await st._release()
        return web.Response(
            status=416,
            headers={
                "Content-Range": f"bytes */{st.size}",
                "Accept-Ranges": "bytes",
                "Content-Length": "0",
            },
        )
    partial = rng is not FULL
    start, end = rng if partial else (0, st.size - 1)

    headers = {
        "Content-Type": st.mime or "application/octet-stream",
        "Content-Length": str(end - start + 1),
        "Accept-Ranges": "bytes",
        "Content-Disposition": _disposition(st.name, inline),
        "Cache-Control": shelf,
    }
    if st.unique_id:
        headers["ETag"] = f'"{st.unique_id}"'
    if partial:
        headers["Content-Range"] = f"bytes {start}-{end}/{st.size}"

    resp = web.StreamResponse(status=206 if partial else 200, headers=headers)
    resp.enable_compression(False)
    try:
        await resp.prepare(request)
    except BaseException:
        await shield(st._release())
        raise

    gen = st.iter_range(start, end)
    try:
        async for piece in gen:
            await resp.write(piece)
        await resp.write_eof()
    except (ConnectionResetError, ConnectionError, CancelledError):
        LOGGER.debug(f"stream aborted by client: {cid}/{mid}")
    except StreamGone:
        _gone(cid, mid)
    except StreamAbort as e:
        LOGGER.error(f"stream failed {cid}/{mid}: {e}")
    finally:
        await gen.aclose()
    return resp


async def _stream(request):
    return await _serve(request, "playback")


async def _dl(request):
    return await _serve(request, "bulk")


async def _drain_stderr(proc, what):
    try:
        buf = await proc.stderr.read()
    except Exception:
        return
    msg = buf.decode("utf-8", "replace").strip()
    if msg:
        LOGGER.error(f"{what}: {msg[-600:]}")


def _nice(args):
    svc_cores = service_cores()
    if svc_cores:
        return ["taskset", "-c", svc_cores] + args
    return args


async def _spawn_ffmpeg(args, what):
    args = _nice(args)
    try:
        proc = await create_subprocess_exec(
            *args, stdin=PIPE, stdout=PIPE, stderr=PIPE
        )
    except FileNotFoundError:
        LOGGER.error(f"{what} failed: {BinConfig.FFMPEG_NAME} not found on PATH")
        raise web.HTTPServiceUnavailable(
            text=f"{BinConfig.FFMPEG_NAME} is not installed"
        ) from None
    ensure_future(_drain_stderr(proc, what))
    return proc


async def _tracks(request):
    _, cid, mid, _exp = await _resolve(request)
    try:
        return web.json_response(
            await _probe(cid, mid),
            headers={
                "Cache-Control": "private, max-age=3600",
                "ETag": f'"tracks-{cid}-{mid}"',
            },
        )
    except StreamGone:
        _gone(cid, mid)
        purge_vtt(cid, mid)
        raise web.HTTPNotFound(text="file is gone") from None
    except NoClientAvailable as e:
        raise web.HTTPServiceUnavailable(text=str(e)) from None
    except Exception as e:
        LOGGER.error(f"track probe failed for {cid}/{mid}: {e}")
        return web.json_response({"audio": [], "subtitle": []})


async def _pump(st, resp, start, end):
    gen = st.iter_range(start, end)
    try:
        async for piece in gen:
            await resp.write(piece)
    finally:
        await gen.aclose()


def _vtt_keep(key, data):
    global _vtt_bytes
    if not data or len(data) > _VTT_ENTRY_MAX:
        return
    old = _vtt_cache.pop(key, None)
    if old is not None:
        _vtt_bytes -= len(old)
    _vtt_cache[key] = data
    _vtt_bytes += len(data)
    while _vtt_bytes > _VTT_TOTAL_MAX and _vtt_cache:
        _, dropped = _vtt_cache.popitem(last=False)
        _vtt_bytes -= len(dropped)


def _vtt_reply(request, key, data):
    tag = f'"{key[0]}-{key[1]}-{key[2]}-{len(data)}"'
    if request.headers.get("If-None-Match") == tag:
        return web.Response(
            status=304,
            headers={
                "ETag": tag,
                "Cache-Control": "private, max-age=86400",
                "Access-Control-Allow-Origin": "*",
            },
        )
    return web.Response(
        body=data,
        headers={
            "Content-Type": "text/vtt; charset=utf-8",
            "ETag": tag,
            "Cache-Control": "private, max-age=86400",
            "Access-Control-Allow-Origin": "*",
        },
    )


async def _playlist_body(token):
    doc = await database.get_playlist(token)
    if not doc:
        _list_cache.pop(token, None)
        _poster_cache.pop(token, None)
        return None
    hit = _cached(_list_cache, token)
    if hit is not None:
        return hit
    return await _once(("list", token), lambda: _build_playlist(token, doc))


async def _build_playlist(token, doc):
    hit = _cached(_list_cache, token)
    if hit is not None:
        return hit
    found = await _locate(doc["items"])
    items = []
    whole = True
    for tok in doc["items"]:
        where = found.get(tok)
        if not where:
            whole = False
            continue
        try:
            info = await probe(where[0], where[1])
        except StreamGone:
            _gone(where[0], where[1])
            whole = False
            continue
        except NoClientAvailable:
            raise
        except Exception as e:
            LOGGER.error(f"playlist probe failed for {tok}: {e}")
            whole = False
            continue
        mime = info.get("mime") or ""
        items.append(
            {
                "token": tok,
                "name": info.get("name") or "Untitled",
                "size": info.get("size") or 0,
                "mime": mime,
                "playable": mime.startswith(_PLAYABLE),
            }
        )
    body = {
        "name": doc["name"] or (items[0]["name"] if items else "Playlist"),
        "items": items,
        "poster": bool(doc.get("pcid") and doc.get("pmid")) or bool(items),
    }
    _keep(_list_cache, token, body, _LIST_KEEP, whole)
    return body


def _trims_for(kept, stored):
    cuts = []
    for seat, (index, _tok, _info) in enumerate(kept):
        cuts.append(int(stored[index]) if index < len(stored) else 0)
    if any(cuts):
        return cuts
    derived = split_trims([i.get("name") or "" for _x, _t, i in kept])
    return derived or cuts


async def _merge_body(token):
    doc = await database.get_playlist(token)
    if not doc or not doc.get("merged"):
        _merge_cache.pop(token, None)
        return None
    hit = _cached(_merge_cache, token)
    if hit is not None:
        return hit
    return await _once(("merge", token), lambda: _build_merge(token, doc))


async def _build_merge(token, doc):
    hit = _cached(_merge_cache, token)
    if hit is not None:
        return hit
    items = doc["items"]
    durs = doc.get("durs") or []
    trims = doc.get("trims") or []
    found = await _locate(items)
    kept = []
    partial = False
    for index, tok in enumerate(items):
        where = found.get(tok)
        if not where:
            partial = True
            continue
        try:
            info = await probe(where[0], where[1])
        except StreamGone:
            _gone(where[0], where[1])
            partial = True
            continue
        except NoClientAvailable:
            raise
        except Exception as e:
            LOGGER.error(f"merge probe failed for {tok}: {e}")
            partial = True
            continue
        kept.append((index, tok, info))
    if not kept:
        return None
    cuts = _trims_for(kept, trims)
    parts = []
    at = 0
    size = 0
    for seat, (index, tok, info) in enumerate(kept):
        dur = int(durs[index] if index < len(durs) else 0)
        trim = cuts[seat]
        span = max(0, dur - trim)
        size += info.get("size") or 0
        parts.append(
            {
                "token": tok,
                "name": info.get("name") or "Untitled",
                "size": info.get("size") or 0,
                "mime": info.get("mime") or "",
                "dur": dur,
                "trim": trim,
                "start": at,
                "span": span,
            }
        )
        at += span
    body = {
        "token": token,
        "name": doc["name"] or parts[0]["name"],
        "mime": parts[0]["mime"],
        "size": size,
        "duration": at,
        "count": len(parts),
        "partial": partial,
        "parts": parts,
    }
    _keep(_merge_cache, token, body, _MERGE_KEEP, not partial)
    return body


async def _merge(request):
    token = request.match_info.get("token", "")
    if not _TOKEN_RE.match(token):
        raise web.HTTPNotFound(text="unknown link")
    try:
        body = await _merge_body(token)
    except NoClientAvailable as e:
        raise web.HTTPServiceUnavailable(text=str(e)) from None
    if body is None:
        raise web.HTTPNotFound(text="unknown link")
    tag = '"merge-%s-%d"' % (token, body["count"])
    return web.json_response(
        body,
        headers={
            "Cache-Control": "private, max-age=300",
            "ETag": tag,
        },
    )


async def _poster_source(token):
    doc = await database.get_playlist(token)
    if doc:
        if doc.get("purl"):
            return ("url", doc["purl"])
        if doc.get("pcid") and doc.get("pmid"):
            return ("tg", (int(doc["pcid"]), int(doc["pmid"])))
        found = await database.get_streams(doc["items"])
        for tok in doc["items"]:
            if tok in found:
                return ("tg", found[tok])
        return None
    art = await database.get_stream_art(token)
    if art:
        return art
    found = await database.get_stream(token)
    return ("tg", found) if found else None


async def _poster(request):
    token = request.match_info.get("token", "")
    if not _TOKEN_RE.match(token):
        raise web.HTTPNotFound(text="unknown link")

    source = await _poster_source(token)
    if not source:
        raise web.HTTPNotFound(text="unknown link")
    if source[0] == "url":
        raise web.HTTPFound(source[1])

    hit = _poster_cache.get(token)
    data = None
    if isinstance(hit, tuple):
        if monotonic() < hit[1]:
            data = hit[0]
            _poster_cache.move_to_end(token)
        else:
            _poster_cache.pop(token, None)
    elif hit is not None:
        data = hit
        _poster_cache.move_to_end(token)
    if data is None:
        try:
            data = await poster_bytes(source[1][0], source[1][1])
        except NoClientAvailable as e:
            raise web.HTTPServiceUnavailable(text=str(e)) from None
        except Exception as e:
            LOGGER.debug(f"poster unavailable for {token}: {e}")
            data = b""
        _poster_cache[token] = data or (b"", monotonic() + _POSTER_MISS_TTL)
        _poster_cache.move_to_end(token)
        while len(_poster_cache) > _POSTER_KEEP:
            _poster_cache.popitem(last=False)

    if not data:
        raise web.HTTPNotFound(text="no artwork")

    tag = f'"poster-{token}-{len(data)}"'
    common = {
        "ETag": tag,
        "Cache-Control": "private, max-age=86400",
        "Access-Control-Allow-Origin": "*",
    }
    if request.headers.get("If-None-Match") == tag:
        return web.Response(status=304, headers=common)
    return web.Response(
        body=data,
        headers={"Content-Type": "image/jpeg", **common},
    )


async def _playlist(request):
    token = request.match_info.get("token", "")
    if not _TOKEN_RE.match(token):
        raise web.HTTPNotFound(text="unknown link")
    try:
        body = await _playlist_body(token)
    except NoClientAvailable as e:
        raise web.HTTPServiceUnavailable(text=str(e)) from None
    if body is None:
        raise web.HTTPNotFound(text="unknown link")
    tag = '"list-%s-%d"' % (token, len(body["items"]))
    return web.json_response(
        body,
        headers={
            "Cache-Control": "private, max-age=300",
            "ETag": tag,
        },
    )


def forget(token):
    _list_cache.pop(token, None)
    _merge_cache.pop(token, None)
    _poster_cache.pop(token, None)


def purge_vtt(cid, mid):
    global _vtt_bytes
    for key in [k for k in _vtt_cache if k[0] == cid and k[1] == mid]:
        _vtt_bytes -= len(_vtt_cache.pop(key))


async def _subs(request):
    _, cid, mid, _exp = await _resolve(request)
    try:
        idx = int(request.match_info.get("idx", "0"))
    except ValueError:
        raise web.HTTPNotFound(text="bad track") from None
    if idx < 0 or idx > 31:
        raise web.HTTPNotFound(text="bad track")

    key = (cid, mid, idx)
    hit = _vtt_cache.get(key)
    if hit is not None:
        _vtt_cache.move_to_end(key)
        return _vtt_reply(request, key, hit)

    pending = _vtt_inflight.get(key)
    if pending is not None:
        try:
            shared = await shield(pending)
        except Exception:
            shared = None
        if shared:
            return _vtt_reply(request, key, shared)

    try:
        st = await open_stream(cid, mid, "bulk")
    except StreamGone:
        _gone(cid, mid)
        purge_vtt(cid, mid)
        raise web.HTTPNotFound(text="file is gone") from None
    except NoClientAvailable as e:
        raise web.HTTPServiceUnavailable(text=str(e)) from None

    try:
        proc = await _spawn_ffmpeg(
            [
                BinConfig.FFMPEG_NAME, "-hide_banner", "-loglevel", "error",
                "-threads", "1", "-vn", "-an",
                "-i", "pipe:0", "-map", f"0:s:{idx}",
                "-f", "webvtt", "-flush_packets", "1", "pipe:1",
            ],
            "subtitle extraction",
        )
    except BaseException:
        await shield(st._release())
        raise

    resp = web.StreamResponse(
        status=200,
        headers={
            "Content-Type": "text/vtt; charset=utf-8",
            "Cache-Control": "no-store",
            "Access-Control-Allow-Origin": "*",
        },
    )
    resp.enable_compression(False)
    try:
        await resp.prepare(request)
    except BaseException:
        _reap_proc(proc)
        await shield(st._release())
        raise

    done = get_running_loop().create_future()
    done.add_done_callback(lambda f: f.exception())
    _vtt_inflight[key] = done

    async def feed():
        gen = st.iter_range(0, st.size - 1)
        try:
            async for piece in gen:
                proc.stdin.write(piece)
                await proc.stdin.drain()
        except (BrokenPipeError, ConnectionResetError):
            pass
        finally:
            await gen.aclose()
            try:
                proc.stdin.close()
            except Exception:
                pass

    pusher = ensure_future(feed())
    buf = []
    seen = 0
    try:
        while True:
            chunk = await proc.stdout.read(65536)
            if not chunk:
                break
            if buf is not None:
                seen += len(chunk)
                if seen > _VTT_ENTRY_MAX:
                    buf = None
                else:
                    buf.append(chunk)
            await resp.write(chunk)
        await resp.write_eof()
        try:
            rc = await wait_for(proc.wait(), timeout=10)
        except Exception:
            rc = None
        if rc == 0 and buf:
            data = b"".join(buf)
            _vtt_keep(key, data)
            if not done.done():
                done.set_result(data)
            LOGGER.info(
                f"subtitle track cached: {cid}/{mid}/{idx} ({len(data)} bytes)"
            )
    except (ConnectionResetError, ConnectionError, CancelledError):
        LOGGER.debug(f"subtitle stream aborted: {cid}/{mid}")
    finally:
        if not done.done():
            done.set_result(None)
        if _vtt_inflight.get(key) is done:
            del _vtt_inflight[key]
        pusher.cancel()
        _reap_proc(proc)
    return resp


async def _ping(_):
    return web.json_response({"ok": True})


def build_app():
    app = web.Application()
    app.router.add_route("GET", "/_ping", _ping)
    app.router.add_route("GET", "/_meta/{token}", _meta)
    app.router.add_route("GET", "/_tracks/{token}", _tracks)
    app.router.add_route("GET", "/_playlist/{token}", _playlist)
    app.router.add_route("GET", "/_merge/{token}", _merge)
    app.router.add_route("GET", "/_poster/{token}", _poster)
    app.router.add_route("GET", "/_subs/{token}/{idx}", _subs)
    app.router.add_route("*", "/_stream/{token}", _stream)
    app.router.add_route("*", "/_dl/{token}", _dl)
    return app


async def start_stream_server():
    global _runner
    if _runner is not None:
        return
    port = stream_port()
    try:
        _runner = web.AppRunner(build_app(), access_log=None)
        await _runner.setup()
        await web.TCPSite(_runner, "127.0.0.1", port).start()
        start_reaper()
        LOGGER.info(f"Stream server listening on 127.0.0.1:{port}")
    except Exception as e:
        _runner = None
        LOGGER.error(f"Failed to start stream server on {port}: {e}")


async def stop_stream_server():
    global _runner
    if _runner is not None:
        try:
            await _runner.cleanup()
        except Exception as e:
            LOGGER.warning(f"stream server cleanup: {e}")
        _runner = None
    await shutdown()


def spawn_stream_server():
    bot_loop.create_task(start_stream_server())
