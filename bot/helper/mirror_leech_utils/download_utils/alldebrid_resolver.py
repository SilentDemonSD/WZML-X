from asyncio import Lock, Semaphore, gather, get_event_loop, sleep
from random import uniform
from re import I as re_I, compile as re_compile, match as re_match
from time import monotonic
from urllib.parse import parse_qs, quote, urlparse

from niquests import AsyncSession
from niquests.exceptions import ConnectTimeout, ProxyError, RequestException

from .... import LOGGER
from ....core.config_manager import Config
from ...ext_utils.exceptions import DirectDownloadLinkException

_API_BASE = "https://api.alldebrid.com/v4.1"
_API_BASE_V4 = "https://api.alldebrid.com/v4"
_AGENT = "wzmlx"
_TIMEOUT = 30
_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)

_MAGNET_POLL_INTERVAL_S = 5
_MAGNET_MAX_DURATION_S = 7200
_MAGNET_UNLOCK_CONCURRENCY = 3

# How long a status check or unlock may keep failing on the network before
# the task gives up. One dropped connection must not cost a 2 h torrent.
_MAGNET_POLL_GRACE_S = 300
_UNLOCK_GRACE_S = 60

# AllDebrid allows 12 requests/s and 600/min. Stay under both across every
# task at once -- a per-task limit alone lets several magnets burst past it.
_RATE_PER_S = 8
_MAX_IN_FLIGHT = 6

_RETRY_ATTEMPTS = 4
_RETRY_BASE_S = 1.0
_RETRY_CAP_S = 20.0
_RETRY_AFTER_CAP_S = 60.0
_RETRY_STATUSES = {429, 500, 502, 503, 504}
# 429 and 503 are AllDebrid's documented "too many requests" answers: the
# request was refused, so resending it is safe even when it is not idempotent.
_REFUSED_STATUSES = {429, 503}
_KEY_IN_TEXT = re_compile(r"(?i)(apikey=)[^&\s'\"]+")

_MAGNET_STATUS_READY = 4
_MAGNET_STATUS_LABELS = {
    0: "In queue",
    1: "Downloading",
    2: "Compressing",
    3: "Uploading to AllDebrid",
    4: "Ready",
    5: "Upload failed",
    6: "Internal error",
    7: "Not downloaded (timeout)",
    8: "File too big",
    9: "Internal error",
    10: "Download timeout (72h)",
    11: "Deleted by hoster",
    12: "Processing failed",
    13: "Processing failed",
    14: "Tracker error - no peers/seeders",
    15: "No peers - torrent is dead",
}
_MAGNET_ERROR_CODES = {5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15}

_FRIENDLY_ERRORS = {
    "AUTH_BAD_APIKEY": "ALLDEBRID_API_KEY is invalid",
    "AUTH_BLOCKED": "AllDebrid account is blocked",
    "AUTH_USER_BANNED": "AllDebrid account is banned",
    "LINK_HOST_NOT_SUPPORTED": "host is not supported by AllDebrid",
    "LINK_HOST_LIMIT_REACHED": "AllDebrid daily limit reached for this host",
    "LINK_HOST_UNAVAILABLE": "host is temporarily unavailable on AllDebrid",
    "LINK_DOWN": "the file is no longer available",
    "LINK_PASS_PROTECTED": "password-protected links are not supported",
    "LINK_TEMPORARY_UNAVAILABLE": "the link is temporarily unavailable",
    "LINK_NOT_SUPPORTED": "this link is not supported by AllDebrid",
    "MAGNET_INVALID_URI": "the magnet URI is malformed",
    "MAGNET_INVALID_FILE": "the .torrent file is invalid",
    "MAGNET_TOO_MANY_ACTIVE": "too many active magnets on AllDebrid",
}


def _api_error_message(error, link):
    code = (error.get("code") or "UNKNOWN").strip()
    message = error.get("message") or "Unknown AllDebrid error"
    friendly = _FRIENDLY_ERRORS.get(code, message)
    if link:
        return f"AllDebrid: {friendly} ({code}) for {link}"
    return f"AllDebrid: {friendly} ({code})"


def _ensure_api_key():
    if api_key := (Config.ALLDEBRID_API_KEY or "").strip():
        return api_key
    raise DirectDownloadLinkException("ERROR: ALLDEBRID_API_KEY is not configured")


class AllDebridNetworkError(DirectDownloadLinkException):
    """No usable answer from AllDebrid even after retrying; worth trying later."""


class _RateLimiter:
    """Spaces request starts evenly, and makes a 429 slow every task down."""

    def __init__(self, per_second):
        self._interval = 1 / per_second
        self._lock = Lock()
        self._next = 0.0

    async def wait(self):
        async with self._lock:
            now = monotonic()
            start = max(now, self._next)
            self._next = start + self._interval
        if start > now:
            await sleep(start - now)

    async def hold(self, seconds):
        async with self._lock:
            self._next = max(self._next, monotonic() + seconds)


_limiter = _RateLimiter(_RATE_PER_S)
_in_flight = Semaphore(_MAX_IN_FLIGHT)
_session = None


def _get_session():
    # One session for every call, so connections stay open and get reused
    # instead of paying a TCP + proxy CONNECT + TLS handshake per request.
    # HTTP/3 is off: QUIC cannot pass through an HTTP proxy, and a long-lived
    # session would remember Alt-Svc upgrades that go around it.
    global _session
    if _session is None:
        _session = AsyncSession(
            headers={"User-Agent": _USER_AGENT},
            disable_http3=True,
            pool_maxsize=_MAX_IN_FLIGHT,
        )
    return _session


def _redact(text):
    text = _KEY_IN_TEXT.sub(r"\1***", str(text))
    if api_key := (Config.ALLDEBRID_API_KEY or "").strip():
        text = text.replace(api_key, "***")
    return text


def _backoff(attempt):
    return min(_RETRY_CAP_S, _RETRY_BASE_S * 2**attempt) * uniform(0.75, 1.25)


def _retry_after(response):
    try:
        seconds = float(response.headers.get("Retry-After"))
    except (TypeError, ValueError):
        return None
    return min(_RETRY_AFTER_CAP_S, max(0.0, seconds))


def _link_of(params, data):
    if params and params.get("link"):
        return params["link"]
    for key, value in data if isinstance(data, list) else ():
        if key == "link":
            return value
    return ""


def _parse_payload(response, link):
    status = response.status_code
    try:
        payload = response.json()
    except Exception as e:
        if status >= 400:
            raise DirectDownloadLinkException(
                f"ERROR: AllDebrid returned HTTP {status}"
            )
        raise DirectDownloadLinkException(
            f"ERROR: AllDebrid returned malformed JSON: {e}"
        )

    if not isinstance(payload, dict):
        raise DirectDownloadLinkException(
            "ERROR: AllDebrid returned an unexpected payload shape"
        )

    if payload.get("status") != "success" or status >= 400:
        error = payload.get("error")
        if not isinstance(error, dict):
            if status >= 400:
                raise DirectDownloadLinkException(
                    f"ERROR: AllDebrid returned HTTP {status}"
                )
            error = {}
        raise DirectDownloadLinkException(f"ERROR: {_api_error_message(error, link)}")

    inner = payload.get("data")
    if not isinstance(inner, dict):
        raise DirectDownloadLinkException(
            "ERROR: AllDebrid response missing 'data' object"
        )
    return inner


async def _call_api(method, url, params=None, data=None, files=None, idempotent=True):
    """One AllDebrid API call: shared session, global rate limit, retries.

    The key travels in the Authorization header, never the URL, so it cannot
    end up in an error message. Calls with idempotent=False (uploads) are only
    resent when AllDebrid refused them outright or they never left the proxy,
    because the docs do not say whether a repeated upload is merged or doubled.
    """
    headers = {"Authorization": f"Bearer {_ensure_api_key()}"}
    query = {"agent": _AGENT, **(params or {})}
    endpoint = urlparse(url).path
    last_error = ""

    for attempt in range(_RETRY_ATTEMPTS):
        try:
            async with _in_flight:
                await _limiter.wait()
                response = await _get_session().request(
                    method,
                    url,
                    params=query,
                    data=data,
                    files=files,
                    headers=headers,
                    timeout=_TIMEOUT,
                )
        except (ConnectTimeout, ProxyError) as e:
            last_error = _redact(e)
            delay = _backoff(attempt)
        except (RequestException, OSError) as e:
            last_error = _redact(e)
            if not idempotent:
                break
            delay = _backoff(attempt)
        except Exception as e:
            raise DirectDownloadLinkException(
                f"ERROR: AllDebrid request failed: {_redact(e)}"
            )
        else:
            status = response.status_code
            if status not in _RETRY_STATUSES or (
                not idempotent and status not in _REFUSED_STATUSES
            ):
                return _parse_payload(response, _link_of(params, data))
            last_error = f"HTTP {status}"
            delay = _retry_after(response) or _backoff(attempt)
            if status in _REFUSED_STATUSES:
                await _limiter.hold(delay)

        if attempt + 1 < _RETRY_ATTEMPTS:
            LOGGER.warning(
                f"AllDebrid {endpoint}: {last_error} - retry {attempt + 1} of "
                f"{_RETRY_ATTEMPTS - 1} in {delay:.1f}s"
            )
            await sleep(delay)

    raise AllDebridNetworkError(f"ERROR: AllDebrid network error: {last_error}")


async def _post_form(url, fields, idempotent=True):
    return await _call_api("POST", url, data=fields, idempotent=idempotent)


def _basename_from_url(link):
    name = urlparse(link).path.rstrip("/").rsplit("/", 1)[-1]
    return name or "file"


async def alldebrid_resolve(link):
    """Unlock a filehost link. Returns a direct URL or a multi-file dict."""
    data = await _call_api(
        "GET",
        f"{_API_BASE_V4}/link/unlock",
        params={"link": link},
    )

    direct = data.get("link")
    filename = data.get("filename") or _basename_from_url(link)
    filesize = int(data.get("filesize") or 0)
    streams = data.get("streams") or []

    if isinstance(direct, str) and direct:
        LOGGER.info(f"AllDebrid unlocked {link[:80]} -> {direct[:80]}...")
        return direct

    if isinstance(streams, list) and streams:
        contents = []
        for entry in streams:
            if stream_url := entry.get("link") or entry.get("url"):
                contents.append(
                    {
                        "filename": entry.get("filename") or filename,
                        "path": entry.get("filename") or filename,
                        "url": stream_url,
                        "size": int(entry.get("filesize") or 0),
                        "headers": {},
                    }
                )
        if contents:
            return {
                "contents": contents,
                "title": filename,
                "total_size": filesize or sum(c["size"] for c in contents),
            }

    raise DirectDownloadLinkException(
        f"ERROR: AllDebrid did not return a usable download link for {link}"
    )


def _extract_infohash(magnet):
    try:
        params = parse_qs(urlparse(magnet).query)
        for xt in params.get("xt", []):
            if match := re_match(r"urn:btih:([A-Za-z0-9]+)", xt, flags=re_I):
                return match[1].lower()
    except Exception:
        pass
    return ""


def _canonicalize_magnet(magnet):
    infohash = _extract_infohash(magnet)
    if not infohash:
        return magnet
    try:
        dn = parse_qs(urlparse(magnet).query).get("dn", [""])[0]
    except Exception:
        dn = ""
    canonical = f"magnet:?xt=urn:btih:{infohash}"
    if dn:
        canonical += "&dn=" + quote(dn, safe="")
    return canonical


def _flatten_files(nodes, result=None, prefix=""):
    """Flatten the AllDebrid file tree. Folders carry 'e', files carry n/s/l."""
    if result is None:
        result = []
    for node in nodes:
        if not isinstance(node, dict):
            continue
        if "e" in node and isinstance(node["e"], list):
            folder_name = node.get("n", "")
            _flatten_files(
                node["e"], result, f"{prefix}{folder_name}/" if folder_name else prefix
            )
        else:
            filename = node.get("n", "unknown")
            result.append(
                {
                    "filename": filename,
                    "path": f"{prefix}{filename}",
                    "size": int(node.get("s", 0) or 0),
                    "link": node.get("l", ""),
                }
            )
    return result


async def upload_magnet(magnet):
    LOGGER.info("Uploading magnet to AllDebrid")
    candidates = []
    for candidate in (magnet, _canonicalize_magnet(magnet), _extract_infohash(magnet)):
        candidate = (candidate or "").strip()
        if candidate and candidate not in candidates:
            candidates.append(candidate)

    for idx, candidate in enumerate(candidates, start=1):
        try:
            data = await _post_form(
                f"{_API_BASE_V4}/magnet/upload",
                [("magnets[]", candidate)],
                idempotent=False,
            )
            magnets = data.get("magnets") or []
            if not magnets:
                raise DirectDownloadLinkException(
                    "ERROR: AllDebrid returned no magnet data"
                )
            entry = magnets[0]
            if "error" in entry:
                raise DirectDownloadLinkException(
                    f"ERROR: {_api_error_message(entry['error'], '')}"
                )
            return entry
        except DirectDownloadLinkException as e:
            retryable = any(
                code in str(e) for code in ("MAGNET_INVALID_FILE", "MAGNET_INVALID_URI")
            )
            if idx < len(candidates) and retryable:
                LOGGER.warning(
                    f"AllDebrid magnet upload failed, retrying with normalized magnet: {e}"
                )
                continue
            raise

    raise DirectDownloadLinkException(
        "ERROR: AllDebrid magnet upload failed for unknown reason"
    )


async def upload_torrent(torrent_bytes, filename):
    LOGGER.info(f"Uploading torrent file to AllDebrid: {filename}")
    data = await _call_api(
        "POST",
        f"{_API_BASE_V4}/magnet/upload/file",
        files={"files[]": (filename, torrent_bytes, "application/x-bittorrent")},
        idempotent=False,
    )
    items = data.get("files") or []
    if not items:
        raise DirectDownloadLinkException("ERROR: AllDebrid returned no torrent data")
    entry = items[0]
    if "error" in entry:
        raise DirectDownloadLinkException(
            f"ERROR: {_api_error_message(entry['error'], '')}"
        )
    return entry


async def get_magnet_status(magnet_id):
    data = await _post_form(f"{_API_BASE}/magnet/status", [("id", str(magnet_id))])
    magnets = data.get("magnets")
    if not magnets:
        raise DirectDownloadLinkException(
            f"ERROR: AllDebrid returned no status for magnet {magnet_id}"
        )
    if isinstance(magnets, dict):
        return magnets
    if isinstance(magnets, list):
        return magnets[0]
    raise DirectDownloadLinkException(
        "ERROR: AllDebrid returned unexpected magnet status payload"
    )


async def delete_magnet(magnet_id):
    """Best-effort removal of a magnet from the AllDebrid history."""
    try:
        await _post_form(f"{_API_BASE_V4}/magnet/delete", [("ids[]", str(magnet_id))])
        LOGGER.info(f"Deleted AllDebrid magnet {magnet_id}")
        return True
    except DirectDownloadLinkException as e:
        LOGGER.warning(f"Failed to delete AllDebrid magnet {magnet_id}: {e}")
        return False


async def get_magnet_files(magnet_id):
    data = await _post_form(f"{_API_BASE_V4}/magnet/files", [("id[]", str(magnet_id))])
    magnets = data.get("magnets") or []
    if not magnets:
        raise DirectDownloadLinkException(
            f"ERROR: AllDebrid returned no files for magnet {magnet_id}"
        )
    entry = magnets[0]
    if "error" in entry:
        raise DirectDownloadLinkException(
            f"ERROR: {_api_error_message(entry['error'], '')}"
        )
    return _flatten_files(entry.get("files") or [])


async def _unlock_alldebrid_link(link):
    return await _post_form(f"{_API_BASE_V4}/link/unlock", [("link", link)])


async def _keep_trying(
    call,
    what,
    is_cancelled=None,
    interval=_MAGNET_POLL_INTERVAL_S,
    grace=_MAGNET_POLL_GRACE_S,
):
    """Repeat a read while it keeps failing on the network, for up to `grace` s.

    _call_api has already retried a few times by then; this rides out longer
    outages -- a VPN reconnect, a proxy restart -- instead of throwing away a
    magnet that may have been downloading on AllDebrid for an hour.
    """
    loop = get_event_loop()
    started = loop.time()
    while True:
        try:
            return await call()
        except AllDebridNetworkError as e:
            if loop.time() - started >= grace:
                raise
            if is_cancelled is not None and is_cancelled():
                raise DirectDownloadLinkException(
                    "ERROR: AllDebrid magnet cancelled by user"
                )
            LOGGER.warning(f"AllDebrid {what} failed, trying again: {e}")
            await sleep(interval)


async def _resolve_unlocked_files(raw_files, progress_callback=None, is_cancelled=None):
    """Unlock every AllDebrid /f/ link with bounded concurrency.

    Returns (resolved, failed). A file that still fails after retrying lands
    in `failed` so the user is told, rather than being silently left out.
    """
    semaphore = Semaphore(_MAGNET_UNLOCK_CONCURRENCY)
    resolved = [None] * len(raw_files)
    failed = []

    async def _unlock(index, file_entry):
        async with semaphore:
            if not file_entry.get("link"):
                return
            name = file_entry.get("filename") or "file"
            try:
                unlocked = await _keep_trying(
                    lambda: _unlock_alldebrid_link(file_entry["link"]),
                    f"unlock of {name}",
                    is_cancelled,
                    grace=_UNLOCK_GRACE_S,
                )
            except DirectDownloadLinkException as e:
                LOGGER.warning(f"AllDebrid unlock failed for {name}: {e}")
                failed.append((name, str(e).removeprefix("ERROR: ")))
                return
            if not (direct := unlocked.get("link") or ""):
                LOGGER.warning(f"AllDebrid returned no direct link for {name}")
                failed.append((name, "AllDebrid returned no direct link"))
                return
            resolved[index] = {
                "filename": unlocked.get("filename")
                or file_entry.get("filename")
                or "file",
                "path": file_entry.get("path") or unlocked.get("filename") or "file",
                "url": direct,
                "size": int(unlocked.get("filesize") or file_entry.get("size") or 0),
                "headers": {},
            }
            if progress_callback is not None:
                await progress_callback(
                    {"unlock_done": index + 1, "unlock_total": len(raw_files)}
                )

    await gather(*(_unlock(idx, entry) for idx, entry in enumerate(raw_files)))

    return [entry for entry in resolved if entry is not None], failed


async def _wait_and_resolve(
    magnet_id,
    name,
    fallback_size,
    progress_callback=None,
    is_cancelled=None,
    poll_interval=_MAGNET_POLL_INTERVAL_S,
    no_seed_timeout=None,
    max_duration=_MAGNET_MAX_DURATION_S,
):
    """Poll AllDebrid until the torrent is ready, then unlock every file.

    Shared by the magnet and .torrent routes. The magnet is removed from
    the AllDebrid history if anything fails.
    """
    if no_seed_timeout is None:
        no_seed_timeout = Config.ALLDEBRID_NO_SEED_TIMEOUT
    try:
        no_seed_since = 0
        last_downloaded = 0
        loop = get_event_loop()
        start_time = loop.time()

        while True:
            if is_cancelled is not None and is_cancelled():
                raise DirectDownloadLinkException(
                    "ERROR: AllDebrid magnet cancelled by user"
                )

            status = await _keep_trying(
                lambda: get_magnet_status(magnet_id),
                f"status check for magnet {magnet_id}",
                is_cancelled,
                poll_interval,
            )
            status_code = int(status.get("statusCode", 0) or 0)
            seeders = int(status.get("seeders", 0) or 0)

            if progress_callback is not None:
                await progress_callback({"phase": "torrent", **status})

            if status_code == _MAGNET_STATUS_READY:
                break

            if status_code in _MAGNET_ERROR_CODES:
                label = _MAGNET_STATUS_LABELS.get(
                    status_code, status.get("status", "unknown")
                )
                raise DirectDownloadLinkException(
                    f"ERROR: AllDebrid - {label} (code {status_code})"
                )

            now = loop.time()
            downloaded = int(status.get("downloaded", 0) or 0)
            if (
                no_seed_timeout > 0
                and status_code == 1
                and seeders == 0
                and downloaded <= last_downloaded
            ):
                if no_seed_since == 0:
                    no_seed_since = now
                elif now - no_seed_since >= no_seed_timeout:
                    raise DirectDownloadLinkException(
                        f"ERROR: AllDebrid no-seed timeout after {int(no_seed_timeout)}s"
                    )
            else:
                no_seed_since = 0
            last_downloaded = downloaded

            if now - start_time >= max_duration:
                raise DirectDownloadLinkException(
                    f"ERROR: AllDebrid magnet exceeded {int(max_duration)}s"
                )

            await sleep(poll_interval)

        raw_files = await _keep_trying(
            lambda: get_magnet_files(magnet_id),
            f"file list for magnet {magnet_id}",
            is_cancelled,
            poll_interval,
        )
        if not raw_files:
            raise DirectDownloadLinkException(
                "ERROR: AllDebrid returned no files for the magnet"
            )

        resolved, failed = await _resolve_unlocked_files(
            raw_files, progress_callback=progress_callback, is_cancelled=is_cancelled
        )
        if not resolved:
            reason = f": {failed[0][1]}" if failed else ""
            raise DirectDownloadLinkException(
                f"ERROR: AllDebrid could not unlock any of the magnet files{reason}"
            )
        if failed:
            LOGGER.warning(
                f"AllDebrid magnet {magnet_id}: {len(failed)} of "
                f"{len(failed) + len(resolved)} files could not be unlocked"
            )

        return {
            "magnet_id": magnet_id,
            "title": name,
            "total_size": sum(item.get("size", 0) for item in resolved)
            or int(fallback_size or 0),
            "contents": resolved,
            "failed_files": [name for name, _ in failed],
        }
    except Exception:
        try:
            await delete_magnet(magnet_id)
        except Exception:
            pass
        raise


async def alldebrid_resolve_magnet(magnet, **kwargs):
    """Resolve a magnet URI into the multi-file dict add_direct_download eats."""
    _ensure_api_key()
    if not magnet:
        raise DirectDownloadLinkException("ERROR: empty magnet URI")

    entry = await upload_magnet(magnet)
    magnet_id = int(entry.get("id") or 0)
    if not magnet_id:
        raise DirectDownloadLinkException("ERROR: AllDebrid did not return a magnet id")

    return await _wait_and_resolve(
        magnet_id,
        entry.get("name") or _basename_from_url(magnet) or "torrent",
        entry.get("size"),
        **kwargs,
    )


async def alldebrid_resolve_torrent(torrent_bytes, filename, **kwargs):
    """Same flow as alldebrid_resolve_magnet but for .torrent bytes."""
    _ensure_api_key()
    entry = await upload_torrent(torrent_bytes, filename)
    magnet_id = int(entry.get("id") or 0)
    if not magnet_id:
        raise DirectDownloadLinkException(
            "ERROR: AllDebrid did not return a magnet id for the torrent file"
        )

    return await _wait_and_resolve(
        magnet_id,
        entry.get("name") or filename or "torrent",
        entry.get("size"),
        **kwargs,
    )
