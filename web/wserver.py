# ruff: noqa: E402
try:
    from uvloop import install

    install()
except ImportError:
    pass


from asyncio import new_event_loop, set_event_loop

bot_loop = new_event_loop()
set_event_loop(bot_loop)

from asyncio import sleep
from importlib import import_module
from os import environ
from re import compile as re_compile
from html import escape
from urllib.parse import urlparse
from contextlib import asynccontextmanager
from logging import INFO, WARNING, FileHandler, StreamHandler, basicConfig, getLogger

from aioaria2 import Aria2HttpClient
from aiohttp.client_exceptions import ClientError
from aioqbt.client import create_client
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import (
    HTMLResponse,
    JSONResponse,
    Response,
    StreamingResponse,
)
from fastapi.templating import Jinja2Templates
from sabnzbdapi import SabnzbdClient
from aioqbt.exc import AQError

from web.nodes import extract_file_ids, make_tree
from aiohttp import ClientSession

getLogger("niquests").setLevel(WARNING)
getLogger("aiohttp").setLevel(WARNING)
getLogger("uvicorn").setLevel(WARNING)
getLogger("uvicorn.access").setLevel(WARNING)

basicConfig(
    format="[%(asctime)s] [%(levelname)s] - %(message)s",
    datefmt="%d-%b-%y %I:%M:%S %p",
    handlers=[FileHandler("log.txt"), StreamHandler()],
    level=INFO,
)

LOGGER = getLogger(__name__)

_SAFE_PATH = re_compile(r"^[A-Za-z0-9_./-]+$")
_SAFE_GID = re_compile(r"^[A-Za-z0-9_-]{1,64}$")
_SAFE_PIN = re_compile(r"^\d{4}$")
_SERVICE_PWD_SALT = b"wzmlx_v3_service_pwd_salt"
_PIN_SALT = b"wzmlx_v3_pin_salt"
_PIN_LEN = 4
_PIN_RATE_LIMIT = 5
_PIN_RATE_WINDOW = 60
_pin_attempts: dict = {}

_cached_secret_bytes = None


def _load_config():
    try:
        cfg = import_module("config")
    except ModuleNotFoundError:
        cfg = None
    bot_token = environ.get("BOT_TOKEN", "") or (
        getattr(cfg, "BOT_TOKEN", "") if cfg else ""
    )
    access_pwd = environ.get("WEB_ACCESS_PASSWORD", "") or (
        getattr(cfg, "WEB_ACCESS_PASSWORD", "") if cfg else ""
    )
    return bot_token, access_pwd


def _resolve_bot_id(token):
    if not token or not isinstance(token, str):
        return "0"
    token = token.strip()
    if not token:
        return "0"
    return (token.split(":", 1)[0] or "0").strip()


_BOT_TOKEN, _ACCESS_PASSWORD = _load_config()
_BOT_ID = _resolve_bot_id(_BOT_TOKEN)


def _service_pwd(service):
    from hashlib import sha256
    from hmac import new as hmac_new
    from secrets import token_bytes

    global _cached_secret_bytes
    if not _ACCESS_PASSWORD:
        if _cached_secret_bytes is None:
            _cached_secret_bytes = token_bytes(32)
        secret = _cached_secret_bytes
    elif isinstance(_ACCESS_PASSWORD, str):
        secret = _ACCESS_PASSWORD.encode("utf-8")
    else:
        secret = _ACCESS_PASSWORD
    msg = f"{_BOT_ID}:{service}".encode("utf-8")
    digest = hmac_new(_SERVICE_PWD_SALT, msg, sha256)
    digest.update(secret)
    raw = digest.hexdigest()
    return raw[:20] + raw[-4:]


def _derive_pin(gid):
    from hashlib import sha256
    from hmac import new as hmac_new

    sig = hmac_new(
        _PIN_SALT,
        f"{gid}|{_BOT_ID}".encode("utf-8"),
        sha256,
    ).hexdigest()
    digits = "".join(c for c in sig if c.isdigit())[:_PIN_LEN]
    if len(digits) < _PIN_LEN:
        digits = (digits + sig).ljust(_PIN_LEN, "0")[:_PIN_LEN]
    return digits


def _pin_rate_limited(gid):
    from time import time

    now = time()
    cutoff = now - _PIN_RATE_WINDOW
    attempts = _pin_attempts.get(gid, [])
    attempts = [t for t in attempts if t > cutoff]
    if attempts:
        _pin_attempts[gid] = attempts
    else:
        _pin_attempts.pop(gid, None)
    if len(_pin_attempts) > 10000:
        stale = [
            g for g, ts in _pin_attempts.items() if not ts or (ts and ts[-1] < cutoff)
        ]
        for g in stale:
            _pin_attempts.pop(g, None)
    return len(attempts) >= _PIN_RATE_LIMIT


def _record_pin_attempt(gid):
    from time import time

    _pin_attempts.setdefault(gid, []).append(time())


def _verify_pin(gid, pin):
    from hashlib import sha256
    from hmac import new as hmac_new

    if not gid or not pin:
        return False
    if not _SAFE_PIN.match(pin):
        return False
    expected = _derive_pin(gid)
    if not expected:
        return False
    return (
        hmac_new(_PIN_SALT, expected.encode(), sha256).hexdigest()
        == hmac_new(_PIN_SALT, pin.encode(), sha256).hexdigest()
    )


aria2 = None
qbittorrent = None
sabnzbd_client = SabnzbdClient(
    host="http://localhost",
    api_key=_service_pwd("sabnzbd"),
    port="8070",
)
SERVICES = {
    "nzb": {"url": "http://localhost:8070/", "password": _service_pwd("sabnzbd")},
    "qbit": {"url": "http://localhost:8090", "password": _service_pwd("qbit")},
}


STREAM_PORT = environ.get("STREAM_PORT", "") or "8091"
STREAM_BASE = f"http://127.0.0.1:{STREAM_PORT}"
_SAFE_TOKEN = re_compile(r"^[A-Za-z0-9_-]{4,32}$")
http_session = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global aria2, qbittorrent, http_session
    aria2 = Aria2HttpClient("http://localhost:6800/jsonrpc")
    qbittorrent = await create_client("http://localhost:8090/api/v2/")
    http_session = ClientSession(auto_decompress=True)
    yield
    await aria2.close()
    await qbittorrent.close()
    await http_session.close()


app = FastAPI(lifespan=lifespan)


templates = Jinja2Templates(directory="web/templates/")


def _client_ip(request: Request):
    fwd = request.headers.get("x-forwarded-for", "")
    if fwd:
        return fwd.split(",")[0].strip()[:64]
    return (request.client.host if request.client else "unknown")[:64]


async def re_verify(paused, resumed, hash_id):
    k = 0
    while True:
        res = await qbittorrent.torrents.files(hash_id)
        verify = True
        for i in res:
            if i.index in paused and i.priority != 0:
                verify = False
                break
            if i.index in resumed and i.priority == 0:
                verify = False
                break
        if verify:
            break
        LOGGER.info("Reverification Failed! Correcting stuff...")
        await sleep(0.5)
        if paused:
            try:
                await qbittorrent.torrents.file_prio(
                    hash=hash_id, id=paused, priority=0
                )
            except (ClientError, TimeoutError, Exception, AQError) as e:
                LOGGER.error(f"{e} Errored in reverification paused!")
        if resumed:
            try:
                await qbittorrent.torrents.file_prio(
                    hash=hash_id, id=resumed, priority=1
                )
            except (ClientError, TimeoutError, Exception, AQError) as e:
                LOGGER.error(f"{e} Errored in reverification resumed!")
        k += 1
        if k > 5:
            return False
    LOGGER.info(f"Verified! Hash: {hash_id}")
    return True


@app.get("/app/files", response_class=HTMLResponse)
async def files(request: Request):
    response = templates.TemplateResponse(request, "page.html")
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response


@app.api_route(
    "/app/files/torrent", methods=["GET", "POST"], response_class=HTMLResponse
)
async def handle_torrent(request: Request):
    params = request.query_params

    if not (gid := params.get("gid")):
        return JSONResponse(
            {
                "files": [],
                "engine": "",
                "error": "GID is missing",
                "message": "GID not specified",
            }
        )

    if not _SAFE_GID.match(gid):
        return JSONResponse(
            {
                "files": [],
                "engine": "",
                "error": "Invalid GID",
                "message": "Invalid GID",
            }
        )

    if not (pin := params.get("pin")):
        return JSONResponse(
            {
                "files": [],
                "engine": "",
                "error": "Pin is missing",
                "message": "PIN not specified",
            }
        )

    if _pin_rate_limited(gid):
        return JSONResponse(
            {
                "files": [],
                "engine": "",
                "error": "Too many attempts",
                "message": f"Too many PIN attempts. Try again in {_PIN_RATE_WINDOW}s.",
            },
            status_code=429,
        )

    if not _verify_pin(gid, pin):
        _record_pin_attempt(gid)
        return JSONResponse(
            {
                "files": [],
                "engine": "",
                "error": "Invalid pin",
                "message": "The PIN you entered is incorrect. Try Again!",
            }
        )
    _pin_attempts.pop(gid, None)

    if request.method == "POST":
        if not (mode := params.get("mode")):
            return JSONResponse(
                {
                    "files": [],
                    "engine": "",
                    "error": "Mode is not specified",
                    "message": "Mode is not specified",
                }
            )
        data = await request.json()
        if mode == "rename":
            if len(gid) > 20:
                await handle_rename(gid, data)
                content = {
                    "files": [],
                    "engine": "",
                    "error": "",
                    "message": "Rename successfully.",
                }
            else:
                content = {
                    "files": [],
                    "engine": "",
                    "error": "Rename failed.",
                    "message": "Cannot rename aria2c torrent file",
                }
        else:
            selected_files, unselected_files = extract_file_ids(data)
            if gid.startswith("SABnzbd_nzo"):
                await set_sabnzbd(gid, unselected_files)
            elif len(gid) > 20:
                await set_qbittorrent(gid, selected_files, unselected_files)
            else:
                selected_files = ",".join(selected_files)
                await set_aria2(gid, selected_files)
            content = {
                "files": [],
                "engine": "",
                "error": "",
                "message": "Your selection has been submitted successfully.",
            }
    else:
        try:
            if gid.startswith("SABnzbd_nzo"):
                res = await sabnzbd_client.get_files(gid)
                content = make_tree(res, "sabnzbd")
            elif len(gid) > 20:
                res = await qbittorrent.torrents.files(gid)
                content = make_tree(res, "qbittorrent")
            else:
                res = await aria2.getFiles(gid)
                op = await aria2.getOption(gid)
                fpath = f"{op['dir']}/"
                content = make_tree(res, "aria2", fpath)
        except (ClientError, TimeoutError, Exception, AQError) as e:
            LOGGER.error(str(e))
            content = {
                "files": [],
                "engine": "",
                "error": "Error getting files",
                "message": str(e),
            }
    return JSONResponse(content)


async def handle_rename(gid, data):
    try:
        _type = data["type"]
        del data["type"]
        if _type == "file":
            await qbittorrent.torrents.rename_file(hash=gid, **data)
        else:
            await qbittorrent.torrents.rename_folder(hash=gid, **data)
    except (ClientError, TimeoutError, Exception, AQError) as e:
        LOGGER.error(f"{e} Errored in renaming")


async def set_sabnzbd(gid, unselected_files):
    await sabnzbd_client.remove_file(gid, unselected_files)
    LOGGER.info(f"Verified! nzo_id: {gid}")


async def set_qbittorrent(gid, selected_files, unselected_files):
    if unselected_files:
        try:
            await qbittorrent.torrents.file_prio(
                hash=gid, id=unselected_files, priority=0
            )
        except (ClientError, TimeoutError, Exception, AQError) as e:
            LOGGER.error(f"{e} Errored in paused")
    if selected_files:
        try:
            await qbittorrent.torrents.file_prio(
                hash=gid, id=selected_files, priority=1
            )
        except (ClientError, TimeoutError, Exception, AQError) as e:
            LOGGER.error(f"{e} Errored in resumed")
    await sleep(0.5)
    if not await re_verify(unselected_files, selected_files, gid):
        LOGGER.error(f"Verification Failed! Hash: {gid}")


async def set_aria2(gid, selected_files):
    res = await aria2.changeOption(gid, {"select-file": selected_files})
    if res == "OK":
        LOGGER.info(f"Verified! Gid: {gid}")
    else:
        LOGGER.info(f"Verification Failed! Report! Gid: {gid}")


@app.get("/", response_class=HTMLResponse)
async def homepage(request: Request):
    response = templates.TemplateResponse(request, "landing.html")
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response


def rewrite_location(location: str, proxy_prefix: str) -> str:
    parsed = urlparse(location)
    if not parsed.netloc:
        return proxy_prefix + location
    if parsed.hostname in ["localhost", "127.0.0.1"]:
        return proxy_prefix + parsed.path
    return location


async def proxy_fetch(
    method: str, url: str, headers: dict, params: dict, body: bytes, proxy_prefix: str
):
    session = http_session or ClientSession(auto_decompress=True)
    async with session.request(
        method,
        url,
        headers=headers,
        params=params,
        data=body,
        allow_redirects=False,
    ) as upstream:
        raw = [
            (k.lower().encode("latin-1"), v.encode("latin-1"))
            for k, v in upstream.headers.items()
            if k.lower() not in ("content-length", "content-encoding")
        ]
        if upstream.status in (301, 302, 303, 307, 308):
            loc = upstream.headers.get("Location")
            if loc:
                new_loc = rewrite_location(loc, proxy_prefix)
                raw = [
                    (k, new_loc.encode("latin-1") if k == b"location" else v)
                    for k, v in raw
                ]
        body = (
            await upstream.read()
            if upstream.status not in (301, 302, 303, 307, 308)
            else b""
        )
        response = Response(content=body, status_code=upstream.status)
        response.raw_headers = raw
        return response


async def protected_proxy(
    service: str, path: str, request: Request, password: str = None
):
    from hmac import compare_digest

    service_info = SERVICES.get(service)
    if not service_info:
        raise HTTPException(status_code=404, detail="Service not found")
    if "password" in service_info:
        if password is None:
            password = request.query_params.get("pass") or request.cookies.get(
                f"{service}_pass"
            )
        if not password or not compare_digest(password, service_info["password"]):
            raise HTTPException(status_code=403, detail="Unauthorized access")
    if path:
        if not _SAFE_PATH.match(path):
            raise HTTPException(status_code=400, detail="Invalid path")
        if ".." in path.split("/"):
            raise HTTPException(status_code=400, detail="Invalid path")
    base = service_info["url"].rstrip("/")
    url = f"{base}/{path.lstrip('/')}" if path else f"{base}/"
    headers = {k: v for k, v in request.headers.items() if k.lower() != "host"}
    body = await request.body()
    params = {k: v for k, v in request.query_params.items() if k != "pass"}
    if "password" in service_info:
        params["apikey"] = service_info["password"]
    response = await proxy_fetch(
        request.method, url, headers, params, body, f"/{service}"
    )
    if "pass" in request.query_params:
        is_https = request.headers.get("x-forwarded-proto") == "https"
        response.set_cookie(
            f"{service}_pass",
            password,
            httponly=True,
            samesite="strict",
            secure=is_https,
        )
    return response


@app.api_route("/nzb/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
async def sabnzbd_proxy(path: str = "", request: Request = None):
    return await protected_proxy("nzb", path, request)


@app.api_route("/qbit/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
async def qbittorrent_proxy(path: str = "", request: Request = None):
    return await protected_proxy("qbit", path, request)


_HOP = (
    "connection",
    "keep-alive",
    "proxy-authenticate",
    "proxy-authorization",
    "te",
    "trailers",
    "transfer-encoding",
    "upgrade",
    "content-encoding",
)


def _stream_offline():
    return HTTPException(
        status_code=503,
        detail="Streaming is disabled or the stream service is not running.",
    )


async def stream_proxy(
    token: str, request: Request, upstream_path: str, params: dict = None
):
    if not _SAFE_TOKEN.match(token or ""):
        raise HTTPException(status_code=404, detail="Unknown link")
    headers = {}
    rng = request.headers.get("range")
    if rng:
        headers["Range"] = rng
    if inm := request.headers.get("if-range"):
        headers["If-Range"] = inm
    headers["X-Viewer"] = _client_ip(request)

    try:
        upstream = await http_session.request(
            request.method,
            f"{STREAM_BASE}{upstream_path}/{token}",
            headers=headers,
            params=params or None,
            allow_redirects=False,
        )
    except ClientError as e:
        raise _stream_offline() from e

    out = {
        k: v for k, v in upstream.headers.items() if k.lower() not in _HOP
    }
    out.setdefault("Accept-Ranges", "bytes")
    out.setdefault("Cache-Control", "private, max-age=86400, immutable")
    out["Referrer-Policy"] = "no-referrer"
    out["X-Content-Type-Options"] = "nosniff"

    if request.method == "HEAD" or upstream.status in (204, 304, 416):
        body = await upstream.read()
        upstream.release()
        return Response(
            content=body if request.method != "HEAD" else b"",
            status_code=upstream.status,
            headers=out,
        )

    async def _pump():
        try:
            async for chunk in upstream.content.iter_chunked(262144):
                yield chunk
        finally:
            upstream.release()

    return StreamingResponse(_pump(), status_code=upstream.status, headers=out)


@app.api_route("/stream/{token}", methods=["GET", "HEAD"])
async def stream_route(token: str, request: Request):
    return await stream_proxy(token, request, "/_stream")


@app.api_route("/dl/{token}", methods=["GET", "HEAD"])
async def download_route(token: str, request: Request):
    return await stream_proxy(token, request, "/_dl")


@app.get("/playlist/{token}", response_class=HTMLResponse)
async def playlist_page(token: str, request: Request):
    if not _SAFE_TOKEN.match(token or ""):
        raise HTTPException(status_code=404, detail="Unknown link")
    response = templates.TemplateResponse(request, "playlist.html")
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Referrer-Policy"] = "no-referrer"
    return response


@app.get("/api/playlist/{token}")
async def playlist_api(token: str, request: Request):
    if not _SAFE_TOKEN.match(token or ""):
        raise HTTPException(status_code=404, detail="Unknown link")
    try:
        async with http_session.get(f"{STREAM_BASE}/_playlist/{token}") as upstream:
            body = await upstream.read()
            cache = upstream.headers.get("Cache-Control", "no-store")
            tag = upstream.headers.get("ETag")
            status = upstream.status
    except ClientError as e:
        raise _stream_offline() from e
    headers = {"Cache-Control": cache, "Referrer-Policy": "no-referrer"}
    if tag:
        headers["ETag"] = tag
    return Response(
        content=body,
        status_code=status,
        media_type="application/json",
        headers=headers,
    )


@app.get("/poster/{token}")
async def poster_route(token: str, request: Request):
    if not _SAFE_TOKEN.match(token or ""):
        raise HTTPException(status_code=404, detail="Unknown link")
    forward = {}
    if tag := request.headers.get("if-none-match"):
        forward["If-None-Match"] = tag
    try:
        async with http_session.get(
            f"{STREAM_BASE}/_poster/{token}", headers=forward
        ) as upstream:
            status = upstream.status
            body = b"" if status == 304 else await upstream.read()
            out = {
                "Cache-Control": upstream.headers.get(
                    "Cache-Control", "private, max-age=86400"
                ),
                "Referrer-Policy": "no-referrer",
            }
            if etag := upstream.headers.get("ETag"):
                out["ETag"] = etag
            ctype = upstream.headers.get("Content-Type", "image/jpeg")
    except ClientError as e:
        raise _stream_offline() from e
    if status not in (200, 304):
        raise HTTPException(status_code=404, detail="No artwork")
    if status == 304:
        return Response(status_code=304, headers=out)
    return Response(content=body, media_type=ctype, headers=out)


@app.get("/xstrm/{token}", response_class=HTMLResponse)
async def xstrm_page(token: str, request: Request):
    if not _SAFE_TOKEN.match(token or ""):
        raise HTTPException(status_code=404, detail="Unknown link")
    response = templates.TemplateResponse(request, "stream.html")
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Referrer-Policy"] = "no-referrer"
    return response


@app.get("/subs/{token}/{track}")
async def subs_route(token: str, track: str, request: Request):
    if not _SAFE_TOKEN.match(token or ""):
        raise HTTPException(status_code=404, detail="Unknown link")
    idx = track[:-4] if track.endswith(".vtt") else track
    if not idx.isdigit() or len(idx) > 2:
        raise HTTPException(status_code=404, detail="Unknown track")

    forward = {}
    if tag := request.headers.get("if-none-match"):
        forward["If-None-Match"] = tag

    try:
        upstream = await http_session.get(
            f"{STREAM_BASE}/_subs/{token}/{idx}", headers=forward
        )
    except ClientError as e:
        raise _stream_offline() from e
    if upstream.status not in (200, 304):
        upstream.release()
        raise HTTPException(status_code=upstream.status, detail="Track unavailable")

    passed = {"Referrer-Policy": "no-referrer"}
    for name in ("Cache-Control", "ETag"):
        if value := upstream.headers.get(name):
            passed[name] = value

    if upstream.status == 304:
        upstream.release()
        return Response(status_code=304, headers=passed)

    async def _pump():
        try:
            async for chunk in upstream.content.iter_chunked(16384):
                yield chunk
        finally:
            upstream.release()

    return StreamingResponse(
        _pump(),
        status_code=200,
        media_type="text/vtt; charset=utf-8",
        headers=passed,
    )


@app.get("/api/tracks/{token}")
async def tracks_route(token: str, request: Request):
    if not _SAFE_TOKEN.match(token or ""):
        raise HTTPException(status_code=404, detail="Unknown link")
    try:
        async with http_session.get(f"{STREAM_BASE}/_tracks/{token}") as upstream:
            body = await upstream.read()
            cache = upstream.headers.get("Cache-Control", "no-store")
            tag = upstream.headers.get("ETag")
    except ClientError as e:
        raise _stream_offline() from e
    headers = {"Cache-Control": cache}
    if tag:
        headers["ETag"] = tag
    return Response(
        content=body,
        status_code=upstream.status,
        media_type="application/json",
        headers=headers,
    )


@app.get("/api/stream/{token}")
async def stream_meta(token: str, request: Request):
    if not _SAFE_TOKEN.match(token or ""):
        raise HTTPException(status_code=404, detail="Unknown link")
    try:
        async with http_session.get(f"{STREAM_BASE}/_meta/{token}") as upstream:
            body = await upstream.read()
            status = upstream.status
    except ClientError as e:
        raise _stream_offline() from e
    return Response(
        content=body,
        status_code=status,
        media_type="application/json",
        headers={"Cache-Control": "no-store"},
    )


@app.exception_handler(HTTPException)
async def http_error(request: Request, exc: HTTPException):
    if request.url.path.startswith(("/app/files/", "/api/", "/stream/", "/dl/")):
        return JSONResponse(
            {"error": str(exc.detail)}, status_code=exc.status_code
        )
    return HTMLResponse(
        f"<h1>{exc.status_code}: {escape(str(exc.detail))}</h1>",
        status_code=exc.status_code,
    )


@app.exception_handler(Exception)
async def server_error(request: Request, exc: Exception):
    LOGGER.error(f"Unhandled error on {request.url.path}: {exc}")
    if request.url.path.startswith(("/app/files/", "/api/", "/stream/", "/dl/")):
        return JSONResponse({"error": "Internal server error"}, status_code=500)
    return HTMLResponse("<h1>500: Internal server error</h1>", status_code=500)
