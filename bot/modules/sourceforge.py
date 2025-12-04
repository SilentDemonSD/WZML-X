import httpx
import time
from uuid import uuid4
from urllib.parse import urlparse, parse_qs, urljoin, urlencode

from bs4 import BeautifulSoup

from bot import LOGGER
from bot.helper.telegram_helper.button_build import ButtonMaker
from bot.helper.telegram_helper.message_utils import sendMessage

# key ngắn -> URL mirror đầy đủ
SF_URL_CACHE = {}


def _parse_sf_link(link: str):
    """
    Tách projectname + filename từ link /projects/.../files/.../download
    """
    p = urlparse(link)
    parts = p.path.split("/")  # ['', 'projects', '{project}', 'files', ... 'download']

    try:
        proj_idx = parts.index("projects")
        project = parts[proj_idx + 1]
    except ValueError:
        return None, None

    try:
        files_idx = parts.index("files")
    except ValueError:
        return project, None

    filename_parts = parts[files_idx + 1 :]
    if filename_parts and filename_parts[-1] == "download":
        filename_parts = filename_parts[:-1]

    filename = "/".join(filename_parts)
    return project, filename


async def _fetch_mirror_choices(project: str, filename: str):
    """
    Gọi settings/mirror_choices và parse HTML lấy danh sách mirrors.
    """
    params = urlencode({"projectname": project, "filename": filename})
    url = f"https://sourceforge.net/settings/mirror_choices?{params}"

    LOGGER.info(f"[SF] Fetching mirror choices: {url}")

    try:
        async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
            r = await client.get(url)
    except Exception as e:
        LOGGER.error(f"[SF] HTTP error getting mirror_choices: {e}")
        return []

    if r.status_code != 200:
        LOGGER.error(f"[SF] mirror_choices HTTP {r.status_code} for {url}")
        return []

    soup = BeautifulSoup(r.text, "lxml")
    mirrors = []

    # Tìm tất cả các link chứa downloads.sourceforge.net và use_mirror=
    for a in soup.find_all("a", href=True):
        href = a["href"]
        text = a.get_text(strip=True)
        if "downloads.sourceforge.net" not in href:
            continue
        if "use_mirror=" not in href:
            continue

        full_url = href if href.startswith("http") else urljoin("https://sourceforge.net/", href)
        q = parse_qs(urlparse(full_url).query)
        code = q.get("use_mirror", [""])[0]
        if not code:
            continue

        name = text or code
        mirrors.append({"name": name, "code": code, "url": full_url})

    # Loại mirror trùng theo code
    dedup = {}
    for m in mirrors:
        dedup[m["code"]] = m
    mirrors = list(dedup.values())

    LOGGER.info(f"[SF] Found {len(mirrors)} mirrors")
    return mirrors


async def handle_sourceforge(link: str, message):
    """
    - Parse link SourceForge
    - Lấy danh sách mirrors
    - Gửi inline keyboard cho user chọn server
    - Lưu URL vào SF_URL_CACHE với key ngắn để callback dùng
    """
    project, filename = _parse_sf_link(link)
    if not project or not filename:
        await sendMessage(
            message,
            "❌ Link SourceForge không đúng dạng /projects/.../files/.../download",
        )
        return

    mirrors = await _fetch_mirror_choices(project, filename)
    if not mirrors:
        await sendMessage(
            message, "❌ Không lấy được danh sách mirror SourceForge."
        )
        return

    btn = ButtonMaker()
    for m in mirrors:
        key = str(uuid4())[:8]
        SF_URL_CACHE[key] = m["url"]
        btn.ibutton(m["name"], f"sfmirror|{key}")

    await sendMessage(
        message,
        "🌐 <b>SourceForge Mirrors</b>\nChọn server để bắt đầu mirror:",
        btn.build_menu(1),
    )