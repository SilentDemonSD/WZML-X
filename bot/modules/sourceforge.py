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
    {"label": "🇫🇷 Free.fr (FR)", "host": "freefr.dl.sourceforge.net", "region": "Europe"},
    {"label": "🇩🇪 NetCologne (DE)", "host": "netcologne.dl.sourceforge.net", "region": "Europe"},
    {"label": "🇸🇪 AltusHost (SE)", "host": "altushost-swe.dl.sourceforge.net", "region": "Europe"},
    {"label": "🇧🇬 NetIX (BG)", "host": "netix.dl.sourceforge.net", "region": "Europe"},
    {"label": "🇷🇸 UNLIMITED (RS)", "host": "unlimited.dl.sourceforge.net", "region": "Europe"},
    {"label": "🇱🇻 DEAC (LV)", "host": "deac-riga.dl.sourceforge.net", "region": "Europe"},

    # Asia
    {"label": "🇭🇰 Zenlayer (HK)", "host": "zenlayer.dl.sourceforge.net", "region": "Asia"},
    {"label": "🇸🇬 OnboardCloud (SG)", "host": "onboardcloud.dl.sourceforge.net", "region": "Asia"},
    {"label": "🇮🇳 Web Werks (IN)", "host": "webwerks.dl.sourceforge.net", "region": "Asia"},
    {"label": "🇮🇳 Excell Media (IN)", "host": "excellmedia.dl.sourceforge.net", "region": "Asia"},
    {"label": "🇮🇳 Cyfuture (IN)", "host": "cyfuture.dl.sourceforge.net", "region": "Asia"},
    {"label": "🇯🇵 JAIST (JP)", "host": "jaist.dl.sourceforge.net", "region": "Asia"},
    {"label": "🇹🇼 NCHC (TW)", "host": "nchc.dl.sourceforge.net", "region": "Asia"},
    {"label": "🇦🇿 YER (AZ)", "host": "yer.dl.sourceforge.net", "region": "Asia"},

    # North America
    {"label": "🇺🇸 VersaWeb (NV)", "host": "versaweb.dl.sourceforge.net", "region": "North America"},
    {"label": "🇺🇸 Cytranet (TX)", "host": "cytranet.dl.sourceforge.net", "region": "North America"},
    {"label": "🇺🇸 Psychz (NY)", "host": "psychz.dl.sourceforge.net", "region": "North America"},
    {"label": "🇺🇸 GigeNET (IL)", "host": "gigenet.dl.sourceforge.net", "region": "North America"},

    # Africa
    {"label": "🇰🇪 Liquid (KE)", "host": "liquidtelecom.dl.sourceforge.net", "region": "Africa"},

    # Global / auto
    {"label": "🌍 Auto-Select", "host": "downloads.sourceforge.net", "region": "Global"},
]


def _parse_sf_path(url: str):
    """
    Từ link SourceForge dạng:
      https://sourceforge.net/projects/<proj>/files/.../file.zip/download
    => trả về:
      project, rel_path, filename
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


async def _measure_latency(client: httpx.AsyncClient, url: str) -> float | None:
    """
    Gửi HEAD tới từng mirror, đo thời gian phản hồi.
    Trả về số giây (float) hoặc None nếu lỗi/timeout.
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
    - Gửi message + inline button cho từng server.
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
                    "region": m["region"],
                    "url": direct_url,
                    "latency": None,  # sẽ gán sau
                }
            )

        latencies = await asyncio.gather(*tasks)

    for i, t in enumerate(latencies):
        results[i]["latency"] = t

    # sort theo tốc độ (None -> rất chậm)
    results.sort(key=lambda x: 9999 if x["latency"] is None else x["latency"])

    # Build text giống kiểu m đưa
    lines = []
    lines.append(f"📦 File: <code>{filename}</code>")
    lines.append("⚡ <b>Direct Links (Sorted by Speed):</b>")

    region_order = ["Europe", "North America", "Asia", "Africa", "Global"]
    for region in region_order:
        region_items = [r for r in results if r["region"] == region]
        if not region_items:
            continue
        lines.append(f"🌍 {region}")
        for r in region_items:
            t = r["latency"]
            if t is None:
                status = "🔴"
                t_str = "timeout"
            else:
                status = "🟢" if t < 1.0 else ("🟡" if t < 2.0 else "🔴")
                t_str = f"{t:.2f}s"
            # link để m có thể bấm mở trực tiếp nếu muốn
            lines.append(
                f"{status} <a href=\"{r['url']}\">{r['label']}</a> - {t_str}"
            )

    text = "\n".join(lines)

    # Build button: mỗi server 1 nút, callback ngắn: sfmirror|<key>
    btn = ButtonMaker()
    for r in results:
        key = uuid4().hex[:8]
        SF_URL_CACHE[key] = r["url"]
        # callback data rất ngắn -> không còn 400 BUTTON_DATA_INVALID
        btn.ibutton(r["label"], f"sfmirror|{key}")

    await sendMessage(
        message,
        text,
        btn.build_menu(1),
    )