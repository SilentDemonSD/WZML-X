from asyncio import CancelledError
from os import getenv
from re import compile as re_compile
from urllib.parse import quote

from aiohttp import web

from .. import LOGGER, bot_loop
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
        "Cache-Control": "no-store",
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


async def _ping(_):
    return web.json_response({"ok": True})


def build_app():
    app = web.Application()
    app.router.add_route("GET", "/_ping", _ping)
    app.router.add_route("GET", "/_meta/{token}", _meta)
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
