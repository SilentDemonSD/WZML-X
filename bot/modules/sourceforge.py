import asyncio
import time
from uuid import uuid4
from urllib.parse import urlparse

import httpx

from bot import LOGGER
from bot.helper.telegram_helper.message_utils import sendMessage
from bot.helper.telegram_helper.button_build import ButtonMaker

# Cache: key -> final direct URL chosen từ server
SF_URL_CACHE = {}

# Danh sách mirror phổ biến trên SourceForge
SF_MIRRORS = [
    # Europe
    {"label": "🇫🇷 Free.fr (FR)", "host": "freefr.dl.sourceforge.net"},
    {"label": "🇩🇪 NetCologne (DE)", "host": "netcologne.dl.sourceforge.net"},
    {"label": "🇸🇪 AltusHost (SE)", "host": "altushost-swe.dl.sourceforge.net"},
    {"label": "🇧🇬 NetIX (BG)", "host": "netix.dl.sourceforge.net"},
    {"label": "🇷🇸 UNLIMITED (RS)", "host": "unlimited.dl.sourceforge.net"},
    {"label": "🇱🇻 DEAC (LV)", "host": "deac-riga.dl.sourceforge.net"},

    # Asia
    {"label": "🇭🇰 Zenlayer (HK)", "host": "zenlayer.dl.sourceforge.net"},
    {"label": "🇸🇬 OnboardCloud (SG)", "host": "onboardcloud.dl.sourceforge.net"},
    {"label": "🇮🇳 Web Werks (IN)", "host": "webwerks.dl.sourceforge.net"},
    {"label": "🇮🇳 Excell Media (IN)", "host": "excellmedia.dl.sourceforge.net"},
    {"label": "🇮🇳 Cyfuture (IN)", "host": "cyfuture.dl.sourceforge.net"},
    {"label": "🇯🇵 JAIST (JP)", "host": "jaist.dl.sourceforge.net"},
    {"label": "🇹🇼 NCHC (TW)", "host": "nchc.dl.sourceforge.net"},
    {"label": "🇦🇿 YER (AZ)", "host": "yer.dl.sourceforge.net"},

    # North America
    {"label": "🇺🇸 VersaWeb (NV)", "host": "versaweb.dl.sourceforge.net"},
    {"label": "🇺🇸 Cytranet (TX)", "host": "cytranet.dl.sourceforge.net"},
    {"label": "🇺🇸 Psychz (NY)", "host": "psychz.dl.sourceforge.net"},
    {"label": "🇺🇸 GigeNET (IL)", "host": "gigenet.dl.sourceforge.net"},

    # Africa
    {"label": "🇰🇪 Liquid (KE)", "host": "liquidtelecom.dl.sourceforge.net"},

    # Global auto
    {"label": "🌍 Auto-Select", "host": "downloads.sourceforge.net"},
]


def _parse_sf_download(url: str):
    """Từ link SourceForge trang projects/.../files/.../download
    => (project, rel_path, filename)

    Ví dụ:
      https://sourceforge.net/projects/xiaomi-eu-multilang-miui-roms/files/xiaomi.eu/HyperOS-STABLE-RELEASES/HyperOS2.0/file.zip/download

    -> project = "xiaomi-eu-multilang-miui-roms"
       rel_path = "xiaomi.eu/HyperOS-STABLE-RELEASES/HyperOS2.0/file.zip"
       filename = "file.zip"
    """
    parsed = urlparse(url)
    parts = parsed.path.strip("/").split("/")  # ["projects", "<proj>", "files", ..., "download"]

    project = None
    rel_parts = None

    if "projects" in parts:
        idx = parts.index("projects")
        if idx + 1 < len(parts):
            project = parts[idx + 1]
        if "files" in parts:
            fidx = parts.index("files")
            rel_parts = parts[fidx + 1 :]
    elif "project" in parts:
        # hiếm khi user đưa thẳng dạng /project/..., nhưng vẫn support
        idx = parts.index("project")
        if idx + 1 < len(parts):
            project = parts[idx + 1]
        rel_parts = parts[idx + 2 :]

    if rel_parts and rel_parts[-1] == "download":
        rel_parts = rel_parts[:-1]

    if not project or not rel_parts:
        return None, None, None

    rel_path = "/".join(rel_parts)
    filename = rel_parts[-1]
    return project, rel_path, filename


async def _measure_latency(client: httpx.AsyncClient, url: str):
    """Gửi HEAD tới mirror để đo ping (giây)."""
    start = time.monotonic()
    try:
        r = await client.head(url, follow_redirects=False)
        _ = r.status_code
        return time.monotonic() - start
    except Exception as e:
        LOGGER.error(f"[SF] Latency check failed for {url}: {e}")
        return None


async def handle_sourceforge(url: str, message):
    """Được gọi từ mirror_leech khi phát hiện link host=sourceforge.net.

    - Phân tích link -> project + path
    - Build direct URL cho từng mirror host
    - HEAD từng URL để lấy ping
    - Sort theo ping
    - Gửi 1 message có các button, mỗi button kèm ping.

    Trả về:
      True  - nếu đã gửi menu chọn server (mirror_leech sẽ dừng lại)
      False - nếu không xử lý được (mirror_leech sẽ mirror bình thường)
    """
    project, rel_path, filename = _parse_sf_download(url)
    if not project or not rel_path:
        # Không hỗ trợ chọn server cho dạng link này -> để mirror_leech xử lý như link thường.
        return False

    direct_path = f"/project/{project}/{rel_path}"
    LOGGER.info(f"[SF] Direct path: {direct_path}")

    mirrors = []
    async with httpx.AsyncClient(timeout=10, follow_redirects=False) as client:
        tasks = []
        for m in SF_MIRRORS:
            direct_url = f"https://{m['host']}{direct_path}"
            mirrors.append(
                {"label": m["label"], "host": m["host"], "url": direct_url, "latency": None}
            )
            tasks.append(_measure_latency(client, direct_url))

        latencies = await asyncio.gather(*tasks)

    for i, t in enumerate(latencies):
        mirrors[i]["latency"] = t

    mirrors.sort(key=lambda x: 9999 if x["latency"] is None else x["latency"])

    btn = ButtonMaker()
    for m in mirrors:
        t = m["latency"]
        if t is None:
            status = "🔴"
            t_str = "timeout"
        else:
            status = "🟢" if t < 1.0 else ("🟡" if t < 2.0 else "🔴")
            t_str = f"{t:.2f}s"
        label = f"{status} {m['label']} ({t_str})"

        key = uuid4().hex[:8]
        SF_URL_CACHE[key] = m["url"]

        btn.ibutton(label, f"sfmirror|{key}")

    await sendMessage(
        message,
        f"📦 <b>File:</b> <code>{filename}</code>\n"
        "⚡ <b>Chọn server SourceForge để mirror:</b>",
        btn.build_menu(2),  # 2 cột
    )
    return True
