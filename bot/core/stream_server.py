from asyncio import (
    CancelledError,
    create_subprocess_exec,
    ensure_future,
    wait_for,
)
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
    probe,
    purge_fid,
    shutdown,
)

_TOKEN_RE = re_compile(r"^[A-Za-z0-9_-]{4,32}$")
_PLAYABLE = ("video/", "audio/")
_runner = None

_PROBE_BYTES = 6 * 1024 * 1024
_PROBE_TIMEOUT = 45
_probe_cache = {}
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
    if len(_probe_cache) > 128:
        _probe_cache.clear()
    _probe_cache[key] = result
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


async def _meta(request):
    _, cid, mid = await _resolve(request)
    try:
        info = await probe(cid, mid)
    except StreamGone:
        purge_fid(cid, mid)
        raise web.HTTPNotFound(text="file is gone") from None
    except NoClientAvailable as e:
        raise web.HTTPServiceUnavailable(text=str(e)) from None
    mime = info["mime"]
    info["playable"] = mime.startswith(_PLAYABLE)
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
        return web.json_response(await _probe(cid, mid))
    except StreamGone:
        purge_fid(cid, mid)
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


async def _subs(request):
    _, cid, mid = await _resolve(request)
    try:
        idx = int(request.match_info.get("idx", "0"))
    except ValueError:
        raise web.HTTPNotFound(text="bad track") from None
    if idx < 0 or idx > 31:
        raise web.HTTPNotFound(text="bad track")
    try:
        st = await open_stream(cid, mid, "bulk")
    except StreamGone:
        purge_fid(cid, mid)
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
    resp = web.StreamResponse(
        status=200,
        headers={
            "Content-Type": "text/vtt; charset=utf-8",
            "Cache-Control": "no-store",
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
    try:
        while True:
            chunk = await proc.stdout.read(65536)
            if not chunk:
                break
            await resp.write(chunk)
        await resp.write_eof()
    except (ConnectionResetError, ConnectionError, CancelledError):
        LOGGER.debug(f"subtitle stream aborted: {cid}/{mid}")
    finally:
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
