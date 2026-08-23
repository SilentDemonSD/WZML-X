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
from urllib.parse import quote

from aiohttp import web

from .. import LOGGER, bot_loop, service_cores
from .config_manager import BinConfig
from ..helper.ext_utils.db_handler import database
from ..helper.telegram_helper.tg_stream import (
    FULL,
    NoClientAvailable,
    StreamAbort,
    StreamGone,
    open_stream,
    parse_range,
    poster_bytes,
    probe,
    purge_fid,
    shutdown,
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

_POSTER_KEEP = 256
_poster_cache = OrderedDict()

_VTT_TOTAL_MAX = 48 * 1024 * 1024
_VTT_ENTRY_MAX = 6 * 1024 * 1024
_vtt_cache = OrderedDict()
_vtt_bytes = 0
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
    st = await open_stream(cid, mid, "bulk")
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
    info = await probe(cid, mid)
    raw = await _prefix(cid, mid, info["size"] or _PROBE_BYTES)
    proc = await create_subprocess_exec(
        "ffprobe", "-hide_banner", "-loglevel", "error",
        "-print_format", "json", "-show_streams", "-",
        stdin=PIPE, stdout=PIPE, stderr=PIPE,
    )
    try:
        out, _ = await wait_for(proc.communicate(raw), timeout=_PROBE_TIMEOUT)
    except Exception:
        try:
            proc.kill()
        except Exception:
            pass
        out = b""
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


def stream_port():
    return int(getenv("STREAM_PORT", "") or 8091)


async def _resolve(request):
    token = request.match_info.get("token", "")
    if not _TOKEN_RE.match(token):
        raise web.HTTPNotFound(text="unknown link")
    found = await database.get_stream(token)
    if not found:
        raise web.HTTPNotFound(text="unknown link")
    return token, found[0], found[1]


def _disposition(name, inline):
    kind = "inline" if inline else "attachment"
    if not name:
        return kind
    return f"{kind}; filename*=UTF-8''{quote(name, safe='')}"


async def _neighbours(token):
    nav = await database.get_stream_nav(token)
    if not nav:
        return None
    body = await _playlist_body(nav[0])
    if not body or not body["items"]:
        return None
    tokens = [i["token"] for i in body["items"]]
    idx = tokens.index(token) if token in tokens else nav[1]
    if idx < 0 or idx >= len(tokens):
        return None
    out = {
        "token": nav[0],
        "name": body["name"],
        "index": idx + 1,
        "total": len(tokens),
        "prev": None,
        "next": None,
    }
    if idx > 0:
        out["prev"] = {
            "token": tokens[idx - 1],
            "name": body["items"][idx - 1]["name"],
        }
    if idx + 1 < len(tokens):
        out["next"] = {
            "token": tokens[idx + 1],
            "name": body["items"][idx + 1]["name"],
        }
    return out


async def _meta(request):
    token, cid, mid = await _resolve(request)
    try:
        info = await probe(cid, mid)
    except StreamGone:
        purge_fid(cid, mid)
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


async def _serve(request, kind):
    _, cid, mid = await _resolve(request)
    inline = kind == "playback"

    viewer = request.headers.get("X-Viewer") or request.remote

    if request.method == "HEAD":
        try:
            info = await probe(cid, mid)
        except StreamGone:
            purge_fid(cid, mid)
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
                "Cache-Control": "private, max-age=86400, immutable",
                "ETag": f'"{info["unique_id"]}"',
            },
        )

    try:
        st = await open_stream(cid, mid, kind, viewer=viewer)
    except StreamGone:
        purge_fid(cid, mid)
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
        "Cache-Control": "private, max-age=86400, immutable",
    }
    if st.unique_id:
        headers["ETag"] = f'"{st.unique_id}"'
    if partial:
        headers["Content-Range"] = f"bytes {start}-{end}/{st.size}"

    resp = web.StreamResponse(status=206 if partial else 200, headers=headers)
    resp.enable_compression(False)
    await resp.prepare(request)

    gen = st.iter_range(start, end)
    try:
        async for piece in gen:
            await resp.write(piece)
        await resp.write_eof()
    except (ConnectionResetError, ConnectionError, CancelledError):
        LOGGER.debug(f"stream aborted by client: {cid}/{mid}")
    except StreamGone:
        purge_fid(cid, mid)
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
    if service_cores:
        return ["taskset", "-c", service_cores] + args
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
    _, cid, mid = await _resolve(request)
    try:
        return web.json_response(
            await _probe(cid, mid),
            headers={
                "Cache-Control": "private, max-age=3600",
                "ETag": f'"tracks-{cid}-{mid}"',
            },
        )
    except StreamGone:
        purge_fid(cid, mid)
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
    hit = _list_cache.get(token)
    if hit is not None:
        _list_cache.move_to_end(token)
        return hit
    doc = await database.get_playlist(token)
    if not doc:
        return None
    items = []
    for tok in doc["items"]:
        found = await database.get_stream(tok)
        if not found:
            continue
        try:
            info = await probe(found[0], found[1])
        except StreamGone:
            purge_fid(found[0], found[1])
            continue
        except NoClientAvailable:
            raise
        except Exception as e:
            LOGGER.error(f"playlist probe failed for {tok}: {e}")
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
    _list_cache[token] = body
    while len(_list_cache) > _LIST_KEEP:
        _list_cache.popitem(last=False)
    return body


async def _poster_source(token):
    doc = await database.get_playlist(token)
    if doc:
        if doc.get("purl"):
            return ("url", doc["purl"])
        if doc.get("pcid") and doc.get("pmid"):
            return ("tg", (int(doc["pcid"]), int(doc["pmid"])))
        for tok in doc["items"]:
            found = await database.get_stream(tok)
            if found:
                return ("tg", found)
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

    data = _poster_cache.get(token)
    if data is None:
        try:
            data = await poster_bytes(source[1][0], source[1][1])
        except NoClientAvailable as e:
            raise web.HTTPServiceUnavailable(text=str(e)) from None
        except Exception as e:
            LOGGER.debug(f"poster unavailable for {token}: {e}")
            data = b""
        _poster_cache[token] = data
        while len(_poster_cache) > _POSTER_KEEP:
            _poster_cache.popitem(last=False)
    else:
        _poster_cache.move_to_end(token)

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


def purge_vtt(cid, mid):
    global _vtt_bytes
    for key in [k for k in _vtt_cache if k[0] == cid and k[1] == mid]:
        _vtt_bytes -= len(_vtt_cache.pop(key))


async def _subs(request):
    _, cid, mid = await _resolve(request)
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
        purge_fid(cid, mid)
        purge_vtt(cid, mid)
        raise web.HTTPNotFound(text="file is gone") from None
    except NoClientAvailable as e:
        raise web.HTTPServiceUnavailable(text=str(e)) from None

    proc = await _spawn_ffmpeg(
        [
            BinConfig.FFMPEG_NAME, "-hide_banner", "-loglevel", "error",
            "-threads", "1", "-vn", "-an",
            "-i", "pipe:0", "-map", f"0:s:{idx}",
            "-f", "webvtt", "-flush_packets", "1", "pipe:1",
        ],
        "subtitle extraction",
    )
    done = get_running_loop().create_future()
    done.add_done_callback(lambda f: f.exception())
    _vtt_inflight[key] = done

    resp = web.StreamResponse(
        status=200,
        headers={
            "Content-Type": "text/vtt; charset=utf-8",
            "Cache-Control": "private, max-age=86400",
            "ETag": f'"{cid}-{mid}-{idx}-live"',
            "Access-Control-Allow-Origin": "*",
        },
    )
    resp.enable_compression(False)
    await resp.prepare(request)

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
        try:
            proc.kill()
        except Exception:
            pass
    return resp


async def _ping(_):
    return web.json_response({"ok": True})


def build_app():
    app = web.Application()
    app.router.add_route("GET", "/_ping", _ping)
    app.router.add_route("GET", "/_meta/{token}", _meta)
    app.router.add_route("GET", "/_tracks/{token}", _tracks)
    app.router.add_route("GET", "/_playlist/{token}", _playlist)
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
