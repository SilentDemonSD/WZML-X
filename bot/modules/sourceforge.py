import logging
from urllib.parse import urlparse, urlunparse, urlencode, parse_qsl

from bot.helper.telegram_helper.message_utils import sendMessage, editMessage
from bot.helper.telegram_helper.button_build import ButtonMaker
from bot import LOGGER

# Danh sách mirror phổ biến trên SourceForge
# Hostname lấy từ tài liệu/mapping mirror chính thức
SF_MIRRORS = [
    {"label": "🌐 Auto (master)", "host": "master.dl.sourceforge.net"},
    {"label": "🇭🇰 Hong Kong - Zenlayer", "host": "zenlayer.dl.sourceforge.net"},
    {"label": "🇸🇬 Singapore - OnboardCloud", "host": "onboardcloud.dl.sourceforge.net"},
    {"label": "🇮🇳 India - Cyfuture", "host": "cyfuture.dl.sourceforge.net"},
    {"label": "🇮🇳 India - Excell Media", "host": "excellmedia.dl.sourceforge.net"},
    {"label": "🇹🇼 Taiwan - NCHC", "host": "nchc.dl.sourceforge.net"},
    {"label": "🇦🇺 Australia - IX Australia", "host": "ixpeering.dl.sourceforge.net"},
    {"label": "🇺🇸 US - PhoenixNAP", "host": "phoenixnap.dl.sourceforge.net"},
    {"label": "🇺🇸 US - Gigenet", "host": "gigenet.dl.sourceforge.net"},
    {"label": "🇩🇪 Germany - NetCologne", "host": "netcologne.dl.sourceforge.net"},
    {"label": "🇧🇬 Bulgaria - NetIX", "host": "netix.dl.sourceforge.net"},
]


def _normalize_download_url(url: str) -> str:
    """
    Chuẩn hóa link SourceForge về dạng:
    https://sourceforge.net/projects/<proj>/files/.../download

    Đồng thời bỏ các query cũ như use_mirror, r, viasf,...
    để mình tự gắn lại use_mirror.
    """
    p = urlparse(url)

    # Bắt buộc dùng sourceforge.net
    scheme = "https"
    netloc = "sourceforge.net"

    path = p.path
    if not path.endswith("/download"):
        if path.endswith("/"):
            path = path + "download"
        else:
            path = path + "/download"

    # Giữ lại query nhưng bỏ các param liên quan mirror
    qs_pairs = [
        (k, v)
        for (k, v) in parse_qsl(p.query, keep_blank_values=True)
        if k not in ("use_mirror", "r", "viasf", "ts")
    ]
    query = urlencode(qs_pairs)

    normalized = urlunparse((scheme, netloc, path, "", query, ""))
    LOGGER.info(f"[SF] Normalized URL: {normalized}")
    return normalized


async def handle_sourceforge(url: str, message):
    """
    Được gọi từ mirror_leech khi phát hiện link SourceForge.
    Hiện inline keyboard cho user chọn server, KHÔNG tự mirror luôn.
    User copy link đã gắn use_mirror rồi dùng lại /mirror /leech.
    """
    base_url = _normalize_download_url(url)
    LOGGER.info(f"[SF] Using static SourceForge mirror list for: {base_url}")

    btn = ButtonMaker()
    for m in SF_MIRRORS:
        cb_data = f"sfmirror|{m['host']}|{base_url}"
        btn.ibutton(m["label"], cb_data)

    await sendMessage(
        message,
        (
            "🔽 <b>Chọn server SourceForge (mirror) bạn muốn dùng:</b>\n"
            "Sau khi chọn, bot sẽ trả lại link có <code>use_mirror=...</code>.\n"
            "➡️ Copy link đó và dùng lại với lệnh /mirror hoặc /leech."
        ),
        btn.build_menu(1),
    )


async def sfmirror_cb(client, query):
    """
    Callback khi user bấm nút chọn mirror.
    Chỉ build lại URL với use_mirror và gửi ra cho user copy.
    """
    try:
        data = query.data.split("|", 2)
        if len(data) != 3:
            await query.answer("❌ Dữ liệu mirror lỗi.", show_alert=True)
            return

        _, host, base_url = data
        sep = "&" if "?" in base_url else "?"
        final_url = f"{base_url}{sep}use_mirror={host}"

        LOGGER.info(f"[SF] Mirror selected {host} -> {final_url}")
        await query.answer()

        text = (
            f"✅ <b>Đã chọn server:</b> <code>{host}</code>\n"
            f"🔗 <code>{final_url}</code>\n\n"
            "➡️ Copy link này và dùng lại với lệnh /mirror hoặc /leech."
        )

        try:
            await editMessage(query.message, text)
        except Exception as e:
            LOGGER.error(f"[SF] editMessage failed: {e}")
            # fallback: gửi msg mới
            await sendMessage(query.message, text)

    except Exception as e:
        LOGGER.error(f"[SF] Callback error: {e}", exc_info=True)
        try:
            await query.answer("❌ Lỗi xử lý mirror.", show_alert=True)
        except Exception:
            pass
