import html
import re
from uuid import uuid4
from urllib.parse import urlparse

import httpx

from bot import LOGGER
from bot.helper.telegram_helper.message_utils import sendMessage
from bot.helper.telegram_helper.button_build import ButtonMaker

# key -> final direct URL (mirror đã chọn)
SF_URL_CACHE = {}


def _extract_project_and_filename(url: str):
    """
    Cố gắng suy ra projectname và filename (path tương đối) từ mọi dạng link SourceForge.

    Hỗ trợ:
    - https://sourceforge.net/projects/<proj>/files/<path>/download
    - https://downloads.sourceforge.net/project/<proj>/<path>
    - https://sourceforge.net/projects/<proj>/files/latest/download  (tạm, nếu parse được)
    """
    try:
        p = urlparse(url)
    except Exception:
        return None, None

    path = p.path or ""

    # Dạng: /projects/<proj>/files/.../download
    if path.startswith("/projects/"):
        parts = path.split("/")
        # ['', 'projects', proj, 'files', ... 'download']
        if len(parts) < 4:
            return None, None
        project = parts[2]

        try:
            files_idx = parts.index("files")
        except ValueError:
            return None, None

        rel_parts = parts[files_idx + 1 :]
        if rel_parts and rel_parts[-1] == "download":
            rel_parts = rel_parts[:-1]

        if not rel_parts:
            return None, None

        filename = "/".join(rel_parts)
        return project, filename

    # Dạng: /project/<proj>/<path>  (downloads.sourceforge.net)
    if path.startswith("/project/"):
        parts = path.split("/")
        # ['', 'project', proj, ...]
        if len(parts) < 3:
            return None, None
        project = parts[2]
        rel_parts = parts[3:]
        if not rel_parts:
            return None, None
        filename = "/".join(rel_parts)
        return project, filename

    return None, None


def _parse_mirror_choices(html_text: str):
    """
    Parse HTML mirror_choices để lấy danh sách:
    [{'label': 'OnboardCloud (Singapore, Singapore)', 'url': 'https://...'}, ...]
    Chỉ giữ những link mirror thực sự (dl.sourceforge.net / downloads.sourceforge.net).
    """
    mirrors = []
    seen_urls = set()

    for m in re.finditer(r'<a[^>]+href="([^"]+)"[^>]*>([^<]+)</a>', html_text):
        url = m.group(1)
        label = html.unescape(m.group(2)).strip()

        # Chỉ giữ các link tải thực sự
        if not (
            ".dl.sourceforge.net" in url
            or "downloads.sourceforge.net" in url
        ):
            continue

        if url in seen_urls:
            continue
        seen_urls.add(url)

        mirrors.append({"label": label, "url": url})

    return mirrors


def _sort_mirrors_for_us(mirrors):
    """
    Ưu tiên:
    0: Auto-select
    1: United States
    2: Others
    """
    def prio(m):
        label = m["label"]
        lower = label.lower()
        if "auto-select" in lower or "auto select" in lower or "auto" == lower:
            return (0, label)
        if "united states" in lower or "(us" in lower:
            return (1, label)
        return (2, label)

    return sorted(mirrors, key=prio)


async def handle_sourceforge(url: str, message):
    """
    Được gọi từ mirror_leech khi phát hiện link SourceForge.
    - Tìm projectname + filename
    - Gọi /settings/mirror_choices để lấy danh sách mirror thực
    - Sắp xếp theo ưu tiên US
    - Gửi 1 message với button; mỗi button dùng callback sfmirror|<key>
    Trả về True nếu đã xử lý, False nếu không parse được để mirror_leech xử lý bình thường.
    """
    project, filename = _extract_project_and_filename(url)
    if not project or not filename:
        LOGGER.warning(f"[SF] Không parse được project/filename từ: {url}")
        return False

    mirror_url = "https://sourceforge.net/settings/mirror_choices"
    params = {"projectname": project, "filename": filename}

    try:
        async with httpx.AsyncClient(timeout=15) as client:
            r = await client.get(mirror_url, params=params)
    except Exception as e:
        LOGGER.error(f"[SF] Lỗi gọi mirror_choices: {e}")
        return False

    if r.status_code != 200:
        LOGGER.error(f"[SF] mirror_choices trả mã {r.status_code}")
        return False

    mirrors = _parse_mirror_choices(r.text)
    if not mirrors:
        LOGGER.warning(f"[SF] Không tìm được mirror nào trong mirror_choices cho {project}/{filename}")
        return False

    mirrors = _sort_mirrors_for_us(mirrors)

    # Build button: mỗi server 1 nút, không test ping
    btn = ButtonMaker()
    for m in mirrors:
        key = uuid4().hex[:8]
        SF_URL_CACHE[key] = m["url"]
        btn.ibutton(m["label"], f"sfmirror|{key}")

    text = (
        f"📦 <b>File:</b> <code>{filename}</code>\n"
        "⚡ <b>Chọn server SourceForge để mirror:</b>"
    )

    await sendMessage(
        message,
        text,
        btn.build_menu(2),  # 2 cột cho gọn
    )
    return True