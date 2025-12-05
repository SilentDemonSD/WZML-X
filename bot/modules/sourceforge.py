from uuid import uuid4
from urllib.parse import urlparse

from bot import LOGGER
from bot.helper.telegram_helper.message_utils import sendMessage
from bot.helper.telegram_helper.button_build import ButtonMaker

# key -> final direct URL (mirror đã chọn)
SF_URL_CACHE = {}

# Danh sách mirror SourceForge (ưu tiên US trước, rồi tới các khu vực khác)
# Host pattern chuẩn: https://<host>/project/<project>/<rel_path>
SF_MIRRORS = [
    # --- North America / US (ưu tiên vì VPS ở US) ---
    {"label": "🇺🇸 GigeNET (IL, US)", "host": "gigenet.dl.sourceforge.net"},
    {"label": "🇺🇸 Psychz (NY, US)", "host": "psychz.dl.sourceforge.net"},
    {"label": "🇺🇸 Cytranet (TX, US)", "host": "cytranet.dl.sourceforge.net"},
    {"label": "🇺🇸 VersaWeb (NV, US)", "host": "versaweb.dl.sourceforge.net"},
    {"label": "🇺🇸 PhoenixNAP (AZ, US)", "host": "phoenixnap.dl.sourceforge.net"},
    {"label": "🇺🇸 Pilotfiber (NY, US)", "host": "pilotfiber.dl.sourceforge.net"},
    {"label": "🇺🇸 NetActuate (NC, US)", "host": "netactuate.dl.sourceforge.net"},
    {"label": "🇺🇸 Cfhcable (FL, US)", "host": "cfhcable.dl.sourceforge.net"},
    {"label": "🇺🇸 SourceForge (US Auto)", "host": "downloads.sourceforge.net"},

    # --- Europe ---
    {"label": "🇩🇪 NetCologne (DE)", "host": "netcologne.dl.sourceforge.net"},
    {"label": "🇫🇷 Free.fr (FR)", "host": "freefr.dl.sourceforge.net"},
    {"label": "🇸🇪 AltusHost (SE)", "host": "altushost-swe.dl.sourceforge.net"},
    {"label": "🇧🇬 NetIX (BG)", "host": "netix.dl.sourceforge.net"},
    {"label": "🇧🇬 AltusHost (BG)", "host": "altushost-sofia.dl.sourceforge.net"},
    {"label": "🇱🇻 DEAC (LV)", "host": "deac-riga.dl.sourceforge.net"},
    {"label": "🇷🇸 UNLIMITED.RS (RS)", "host": "unlimited.dl.sourceforge.net"},
    {"label": "🇩🇪 Delska (Frankfurt, DE)", "host": "delsa-frankfurt.dl.sourceforge.net"},

    # --- Asia ---
    {"label": "🇭🇰 Zenlayer (HK)", "host": "zenlayer.dl.sourceforge.net"},
    {"label": "🇸🇬 OnboardCloud (SG)", "host": "onboardcloud.dl.sourceforge.net"},
    {"label": "🇹🇼 TWDS (TW)", "host": "twds.dl.sourceforge.net"},
    {"label": "🇮🇳 Web Werks (IN)", "host": "webwerks.dl.sourceforge.net"},
    {"label": "🇮🇳 Excell Media (IN)", "host": "excellmedia.dl.sourceforge.net"},
    {"label": "🇮🇳 Cyfuture (IN)", "host": "cyfuture.dl.sourceforge.net"},
    {"label": "🇹🇼 NCHC (TW)", "host": "nchc.dl.sourceforge.net"},
    {"label": "🇯🇵 JAIST (JP)", "host": "jaist.dl.sourceforge.net"},
    {"label": "🇦🇿 YER (AZ)", "host": "yer.dl.sourceforge.net"},

    # --- Africa / South America / Oceania ---
    {"label": "🇰🇪 Liquid Telecom (KE)", "host": "liquidtelecom.dl.sourceforge.net"},
    {"label": "🇰🇪 Icolo (KE)", "host": "icolo.dl.sourceforge.net"},
    {"label": "🇦🇷 SiTSA (AR)", "host": "sitsa.dl.sourceforge.net"},
    {"label": "🇧🇷 SinalBR (BR)", "host": "sinalbr.dl.sourceforge.net"},
    {"label": "🇪🇨 Fly Life (EC)", "host": "flylife-ec.dl.sourceforge.net"},
    {"label": "🇦🇺 IX Australia (AU)", "host": "ix.dl.sourceforge.net"},
]


def _extract_project_and_relpath(url: str):
    """
    Tách projectname và rel_path từ các dạng link SourceForge thường gặp.

    Hỗ trợ:
    - https://sourceforge.net/projects/<proj>/files/<path>/file.zip/download
    - https://downloads.sourceforge.net/project/<proj>/<path>/file.zip
    """
    try:
        p = urlparse(url)
    except Exception as e:
        LOGGER.error(f"[SF] urlparse lỗi cho {url}: {e}")
        return None, None

    path = p.path or ""

    # Dạng: /projects/<proj>/files/.../download
    if path.startswith("/projects/"):
        parts = path.split("/")
        # ['', 'projects', proj, 'files', ... 'download?']
        if len(parts) < 4:
            return None, None

        project = parts[2]

        try:
            files_idx = parts.index("files")
        except ValueError:
            return None, None

        rel_parts = parts[files_idx + 1 :]
        # Bỏ "download" ở cuối nếu có
        if rel_parts and rel_parts[-1] == "download":
            rel_parts = rel_parts[:-1]

        if not rel_parts:
            return None, None

        rel_path = "/".join(rel_parts)
        return project, rel_path

    # Dạng: /project/<proj>/<path>/file.zip (downloads.sourceforge.net)
    if path.startswith("/project/"):
        parts = path.split("/")
        # ['', 'project', proj, ...]
        if len(parts) < 4:
            return None, None
        project = parts[2]
        rel_parts = parts[3:]
        rel_path = "/".join(rel_parts)
        return project, rel_path

    return None, None


async def handle_sourceforge(url: str, message):
    """
    Được gọi từ mirror_leech khi phát hiện link SourceForge.

    Flow:
      1. Tách project + rel_path từ link gốc.
      2. Với mỗi mirror trong SF_MIRRORS, build URL:
           https://<host>/project/<project>/<rel_path>
      3. Gửi 1 message có inline buttons cho user chọn server.
      4. Mỗi button callback dạng: sfmirror|<key>
         Key dùng để tra URL thật trong SF_URL_CACHE.

    Trả về:
      - True  -> đã xử lý (mirror_leech không mirror tiếp link gốc nữa)
      - False -> không parse được, mirror_leech cứ xử lý như link thường.
    """
    project, rel_path = _extract_project_and_relpath(url)
    if not project or not rel_path:
        LOGGER.warning(f"[SF] Không parse được project/rel_path từ: {url}")
        return False

    LOGGER.info(f"[SF] project={project} rel_path={rel_path}")

    btn = ButtonMaker()

    for m in SF_MIRRORS:
        direct_url = f"https://{m['host']}/project/{project}/{rel_path}"
        key = uuid4().hex[:8]
        SF_URL_CACHE[key] = direct_url
        btn.ibutton(m["label"], f"sfmirror|{key}")

    text = (
        f"📦 <b>File:</b> <code>{rel_path}</code>\n"
        "⚡ <b>Chọn server SourceForge để mirror:</b>"
    )

    # 2 cột cho gọn, giữ nguyên hành vi cũ
    await sendMessage(message, text, btn.build_menu(2))
    return True