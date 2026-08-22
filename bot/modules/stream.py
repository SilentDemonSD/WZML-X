from html import escape
from secrets import token_urlsafe

from pyrogram.enums import ButtonStyle

from .. import LOGGER
from ..core.config_manager import Config
from ..core.tg_client import TgClient
from ..helper.ext_utils.db_handler import database
from ..helper.telegram_helper.button_build import ButtonMaker
from ..helper.telegram_helper.message_utils import (
    delete_message,
    edit_message,
    send_message,
)
from ..helper.ext_utils.status_utils import get_readable_file_size
from ..helper.telegram_helper.tg_transfer import media_of

_PLAYABLE = ("video/", "audio/")


async def _mint_token(chat_id, msg_id):
    existing = await database.find_stream(chat_id, msg_id)
    if existing:
        return existing
    for _ in range(6):
        token = token_urlsafe(5)
        if await database.get_stream(token) is None:
            await database.add_stream(token, chat_id, msg_id)
            return token
    return None


async def gen_stream_link(chat_id, msg_id):
    if not Config.BASE_URL:
        return None
    try:
        token = await _mint_token(int(chat_id), int(msg_id))
    except Exception as e:
        LOGGER.error(f"stream link generation failed for {chat_id}/{msg_id}: {e}")
        return None
    if not token:
        return None
    base = Config.BASE_URL.rstrip("/")
    return f"{base}/watch/{token}", f"{base}/dl/{token}"


async def _dump_copy(message):
    dump = Config.LEECH_DUMP_CHAT
    if not dump:
        return message.chat.id, message.id
    try:
        dump = int(str(dump).split("|", 1)[0])
    except (TypeError, ValueError):
        return message.chat.id, message.id
    if message.chat.id == dump:
        return dump, message.id
    copied = await TgClient.bot.copy_message(
        chat_id=dump,
        from_chat_id=message.chat.id,
        message_id=message.id,
        disable_notification=True,
    )
    return dump, copied.id


async def stream_links(_, message):
    reply = message.reply_to_message
    if not reply:
        await send_message(
            message,
            "<b>Reply to a media file</b>\n\n<i>Send /stream as a reply to any "
            "video, audio or document to get stream and download links.</i>",
        )
        return
    try:
        media = media_of(reply)
    except ValueError:
        await send_message(message, "<b>That message has no downloadable media.</b>")
        return
    if not Config.BASE_URL:
        await send_message(
            message,
            "<b>BASE_URL is not configured.</b>\n\n<i>Set it in bot settings to "
            "generate stream links.</i>",
        )
        return

    status = await send_message(message, "<i>Generating links...</i>")
    try:
        chat_id, msg_id = await _dump_copy(reply)
        token = await _mint_token(chat_id, msg_id)
        if not token:
            await edit_message(status, "<b>Could not allocate a link. Try again.</b>")
            return
    except Exception as e:
        LOGGER.error(f"stream link generation failed: {e}")
        await edit_message(status, f"<b>Failed to generate links.</b>\n\n<i>{e}</i>")
        return

    base = Config.BASE_URL.rstrip("/")
    name = getattr(media, "file_name", "") or "Media"
    size = getattr(media, "file_size", 0) or 0
    mime = getattr(media, "mime_type", "") or ""
    playable = mime.startswith(_PLAYABLE)

    watch = f"{base}/watch/{token}"
    direct = f"{base}/dl/{token}"

    msg = "<b>〶 Stream Links Generated</b>\n\n"
    msg += f"<b>┎ Name</b> → <code>{escape(name)}</code>\n"
    msg += f"<b>┠ Size</b> → {get_readable_file_size(size)}\n"
    msg += f"<b>┖ Type</b> → {escape(mime) if mime else 'unknown'}\n\n"
    if not playable:
        msg += "<i>Not a media type browsers can play — use the download link.</i>\n\n"
    msg += f"<b>Task By: </b>{message.from_user.mention if message.from_user else 'N/A'}"

    buttons = ButtonMaker()
    if playable:
        buttons.url_button("▶️ Stream", watch, style=ButtonStyle.PRIMARY)
    buttons.url_button("⬇️ Download", direct, style=ButtonStyle.SUCCESS)
    buttons.url_button(
        "🔗 Share", f"https://t.me/share/url?url={watch if playable else direct}"
    )
    await edit_message(status, msg, buttons.build_menu(2))
    await delete_message(message)
