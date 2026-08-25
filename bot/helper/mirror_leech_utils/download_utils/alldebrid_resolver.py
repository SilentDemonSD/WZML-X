from asyncio import Semaphore, gather, get_event_loop, sleep
from re import I as re_I, match as re_match
from urllib.parse import parse_qs, quote, urlparse

from niquests import AsyncSession

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


async def _call_api(method, url, params=None, data=None, files=None):
    kwargs = {"params": params or {}, "timeout": _TIMEOUT}
    if data is not None:
        kwargs["data"] = data
    if files is not None:
        kwargs["files"] = files
    async with AsyncSession(headers={"User-Agent": _USER_AGENT}) as client:
        try:
            response = await client.request(method, url, **kwargs)
            response.raise_for_status()
        except Exception as e:
            raise DirectDownloadLinkException(f"ERROR: AllDebrid network error: {e}")
        try:
            payload = response.json()
        except Exception as e:
            raise DirectDownloadLinkException(
                f"ERROR: AllDebrid returned malformed JSON: {e}"
            )

    if not isinstance(payload, dict):
        raise DirectDownloadLinkException(
            "ERROR: AllDebrid returned an unexpected payload shape"
        )

    if payload.get("status") != "success":
        error = payload.get("error") or {}
        raise DirectDownloadLinkException(
            f"ERROR: {_api_error_message(error, params.get('link', '') if params else '')}"
        )

    inner = payload.get("data")
    if not isinstance(inner, dict):
        raise DirectDownloadLinkException(
            "ERROR: AllDebrid response missing 'data' object"
        )
    return inner


async def _post_form(url, fields):
    api_key = _ensure_api_key()
    return await _call_api(
        "POST", url, params={"agent": _AGENT, "apikey": api_key}, data=fields
    )


def _basename_from_url(link):
    name = urlparse(link).path.rstrip("/").rsplit("/", 1)[-1]
    return name or "file"


async def alldebrid_resolve(link):
    """Unlock a filehost link. Returns a direct URL or a multi-file dict."""
    api_key = _ensure_api_key()
    data = await _call_api(
        "GET",
        f"{_API_BASE_V4}/link/unlock",
        params={"agent": _AGENT, "apikey": api_key, "link": link},
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
                f"{_API_BASE_V4}/magnet/upload", [("magnets[]", candidate)]
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
    api_key = _ensure_api_key()
    data = await _call_api(
        "POST",
        f"{_API_BASE_V4}/magnet/upload/file",
        params={"agent": _AGENT, "apikey": api_key},
        files={"files[]": (filename, torrent_bytes, "application/x-bittorrent")},
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
    api_key = _ensure_api_key()
    return await _call_api(
        "POST",
        f"{_API_BASE_V4}/link/unlock",
        params={"agent": _AGENT, "apikey": api_key},
        data=[("link", link)],
    )


async def _resolve_unlocked_files(raw_files, progress_callback=None):
    """Unlock every AllDebrid /f/ link with bounded concurrency."""
    semaphore = Semaphore(_MAGNET_UNLOCK_CONCURRENCY)
    resolved = [None] * len(raw_files)

    async def _unlock(index, file_entry):
        async with semaphore:
            if not file_entry.get("link"):
                return
            try:
                unlocked = await _unlock_alldebrid_link(file_entry["link"])
            except DirectDownloadLinkException as e:
                LOGGER.warning(
                    f"AllDebrid unlock failed for {file_entry.get('filename', '?')}: {e}"
                )
                return
            if not (direct := unlocked.get("link") or ""):
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

    return [entry for entry in resolved if entry is not None]


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

            status = await get_magnet_status(magnet_id)
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

        raw_files = await get_magnet_files(magnet_id)
        if not raw_files:
            raise DirectDownloadLinkException(
                "ERROR: AllDebrid returned no files for the magnet"
            )

        resolved = await _resolve_unlocked_files(
            raw_files, progress_callback=progress_callback
        )
        if not resolved:
            raise DirectDownloadLinkException(
                "ERROR: AllDebrid could not unlock any of the magnet files"
            )

        return {
            "magnet_id": magnet_id,
            "title": name,
            "total_size": sum(item.get("size", 0) for item in resolved)
            or int(fallback_size or 0),
            "contents": resolved,
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
