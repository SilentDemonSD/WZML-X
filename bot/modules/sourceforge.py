import asyncio
import time
from uuid import uuid4
from urllib.parse import urlparse

import httpx

from bot import LOGGER
from bot.helper.telegram_helper.message_utils import sendMessage
from bot.helper.telegram_helper.button_build import ButtonMaker

# key -> final direct URL (mirror đã chọn)
SF_URL_CACHE = {}

# Danh sách mirror phổ biến trên SourceForge
SF_MIRRORS = [
    # Europe
    {"label": "🇺🇸 GigeNET (IL)", "host": "gigenet.dl.sourceforge.net"},
    {"label": "🇺🇸 Psychz (NY)", "host": "psychz.dl.sourceforge.net"},
    {"label": "🇫🇷 Free.fr (FR)", "host": "freefr.dl.sourceforge.net"},
    {"label": "🇺🇸 VersaWeb (NV)", "host": "versaweb.dl.sourceforge.net"},
    {"label": "🇩🇪 NetCologne (DE)", "host": "netcologne.dl.sourceforge.net"},
    {"label": "🇧🇬 NetIX (BG)", "host": "netix.dl.sourceforge.net"},
    {"label": "🇷🇸 UNLIMITED (RS)", "host": "unlimited.dl.sourceforge.net"},
    {"label": "🇸🇪 AltusHost (SE)", "host": "altushost-swe.dl.sourceforge.net"},
    {"label": "🇱🇻 DEAC (LV)", "host": "deac-riga.dl.sourceforge.net"},
    {"label": "🌍 Auto-Select", "host": "downloads.sourceforge.net"},
    {"label": "🇦🇿 YER (AZ)", "host": "yer.dl.sourceforge.net"},
    {"label": "🇺🇸 Cytranet (TX)", "host": "cytranet.dl.sourceforge.net"},
    {"label": "🇭🇰 Zenlayer (HK)", "host": "zenlayer.dl.sourceforge.net"},
    {"label": "🇸🇬 OnboardCloud (SG)", "host": "onboardcloud.dl.sourceforge.net"},
    {"label": "🇮🇳 Web Werks (IN)", "host": "webwerks.dl.sourceforge.net"},
    {"label": "🇮🇳 Cyfuture (IN)", "host": "cyfuture.dl.sourceforge.net"},
    {"label": "🇹🇼 NCHC (TW)", "host": "nchc.dl.sourceforge.net"},
    {"label": "🇯🇵 JAIST (JP)", "host": "jaist.dl.sourceforge.net"},
    {"label": "🇮🇳 Excell Media (IN)", "host": "excellmedia.dl.sourceforge.net"},
    {"label": "🇰🇪 Liquid (KE)", "host": "liquidtelecom.dl.sourceforge.net"},
]


def _parse_sf_path(url: str):
    """
    Từ link SourceForge dạng:
      https://sourceforge.net/projects/<proj>/files/.../file.zip/download
    => project, rel_path, filename
    để build direct URL:
      https://<mirror-host>/project/<proj>/<rel_path>
    """
    p = urlparse(url)
    parts = p.path.split("/")  # ['', 'projects', '<proj>', 'files', ... 'download']

    try:
        proj_idx = parts.index("projects")
        project = parts[proj_idx + 1]
    except ValueError:
        return None, None, None

    try:
        files_idx = parts.index("files")
        rel_parts = parts[files_idx + 1 :]
    except ValueError:
        rel_parts = []

    if rel_parts and rel_parts[-1] == "download":
        rel_parts = rel_parts[:-1]

    if not rel_parts:
        return None, None, None

    rel_path = "/".join(rel_parts)
    filename = rel_parts[-1]
    return project, rel_path, filename


async def _measure_latency(client: httpx.AsyncClient, url: str):
    """
    Gửi HEAD tới từng mirror, đo thời gian phản hồi (giây).
    Trả về float hoặc None nếu lỗi/timeout.
    """
    start = time.monotonic()
    try:
        r = await client.head(url, follow_redirects=False)
        _ = r.status_code
        elapsed = time.monotonic() - start
        return elapsed
    except Exception as e:
        LOGGER.error(f"[SF] Latency check failed for {url}: {e}")
        return None


async def handle_sourceforge(url: str, message):
    """
    Được gọi từ mirror_leech khi phát hiện link SourceForge.
    - Phân tích link -> project + path
    - Build direct URL cho từng mirror host
    - Ping/HEAD từng mirror -> đo thời gian
    - Sort theo tốc độ (nhanh -> chậm)
    - Gửi 1 message + các button (mỗi button có kèm ping).
    Khi bấm button -> sfmirror_cb trong mirror_leech.py sẽ mirror URL đó.
    """
    project, rel_path, filename = _parse_sf_path(url)
    if not project or not rel_path:
        return await sendMessage(
            message,
            "❌ Link SourceForge không đúng dạng /projects/.../files/.../download",
        )

    direct_path = f"/project/{project}/{rel_path}"
    LOGGER.info(f"[SF] Direct path: {direct_path}")

    results = []

    async with httpx.AsyncClient(timeout=10, follow_redirects=False) as client:
        tasks = []
        for m in SF_MIRRORS:
            direct_url = f"https://{m['host']}{direct_path}"
            tasks.append(_measure_latency(client, direct_url))
            results.append(
                {
                    "label": m["label"],
                    "host": m["host"],
                    "url": direct_url,
                    "latency": None,  # sẽ gán sau
                }
            )

        latencies = await asyncio.gather(*tasks)

    for i, t in enumerate(latencies):
        results[i]["latency"] = t

    # sort theo tốc độ (None -> rất chậm)
    results.sort(key=lambda x: 9999 if x["latency"] is None else x["latency"])

    # Build buttons: mỗi server 1 nút, label có luôn ping
    btn = ButtonMaker()
    for r in results:
        t = r["latency"]
        if t is None:
            status = "🔴"
            t_str = "timeout"
        else:
            status = "🟢" if t < 1.0 else ("🟡" if t < 2.0 else "🔴")
            t_str = f"{t:.2f}s"
        label = f"{status} {r['label']} ({t_str})"

        key = uuid4().hex[:8]
        SF_URL_CACHE[key] = r["url"]
        btn.ibutton(label, f"sfmirror|{key}")

    await sendMessage(
        message,
        f"📦 <b>File:</b> <code>{filename}</code>\n"
        "⚡ <b>Chọn server SourceForge để mirror:</b>",
        btn.build_menu(2),
    )
