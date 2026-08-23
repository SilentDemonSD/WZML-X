from html import escape
from secrets import token_urlsafe

from pyrogram.enums import ButtonStyle

from .. import LOGGER
from ..core.config_manager import Config
from ..core.tg_client import TgClient
from ..helper.ext_utils.db_handler import database
from ..helper.ext_utils.links_utils import is_telegram_link
from ..helper.telegram_helper.button_build import ButtonMaker
from ..helper.telegram_helper.message_utils import (
    delete_message,
    edit_message,
    get_tg_link_message,
    send_message,
)
from ..helper.ext_utils.status_utils import get_readable_file_size
from ..helper.telegram_helper.tg_transfer import media_of

_PLAYABLE = ("video/", "audio/")
_MAX_BATCH = 50
_MAX_BUTTONS = 20


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


async def _mint_playlist(name, items, poster):
    for _ in range(6):
        token = token_urlsafe(5)
        if await database.get_playlist(token) is None:
            await database.add_playlist(token, name, items, poster)
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
    return f"{base}/xstrm/{token}", f"{base}/dl/{token}"


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


def parse_stream_args(parts):
    poster = None
    link = None
    playlist = False
    words = []
    want_poster = False
    for part in parts:
        if want_poster:
            want_poster = False
            if is_telegram_link(part):
                poster = part
                continue
        if part in ("-t", "-thumb"):
            want_poster = True
            continue
        if part in ("-pl", "-playlist"):
            playlist = True
            continue
        if is_telegram_link(part):
            if link is None:
                link = part
            continue
        words.append(part)
    return {
        "link": link,
        "poster": poster,
        "playlist": playlist,
        "name": " ".join(words).strip(),
    }


async def _expand(link):
    payload, _ = await get_tg_link_message(link)
    if not isinstance(payload, list):
        return ([payload] if payload else []), 1
    found = []
    for one in payload[:_MAX_BATCH]:
        try:
            msg, _s = await get_tg_link_message(one)
        except Exception as e:
            LOGGER.debug(f"stream batch skipped {one}: {e}")
            continue
        if msg and not isinstance(msg, list):
            found.append(msg)
    return found, len(payload)


def _playable(media):
    return (getattr(media, "mime_type", "") or "").startswith(_PLAYABLE)


async def _register(message, poster=None):
    chat_id, msg_id = await _dump_copy(message)
    token = await _mint_token(chat_id, msg_id)
    if token and poster:
        await database.add_stream(token, chat_id, msg_id, poster)
    return token


def _ready():
    if Config.DISABLE_STREAM:
        return (
            "<b>Streaming is disabled.</b>\n\n<i>The bot owner turned it off in "
            "Module Settings.</i>"
        )
    if not (TgClient.stream_bots or TgClient.helper_bots):
        return (
            "<b>No streaming clients are running.</b>\n\n<i>Add STREAM_TOKENS or "
            "HELPER_TOKENS in bot settings, then restart.</i>"
        )
    if not Config.BASE_URL:
        return (
            "<b>BASE_URL is not configured.</b>\n\n<i>Set it in bot settings to "
            "generate stream links.</i>"
        )
    return None


async def stream_links(_, message):
    blocked = _ready()
    if blocked:
        await send_message(message, blocked)
        return

    parts = (message.text or message.caption or "").split()[1:]
    args = parse_stream_args(parts)
    reply = message.reply_to_message

    if not args["link"] and not reply:
        await send_message(
            message,
            "<b>Reply to a media file or pass a link</b>\n\n"
            "<i>/stream — as a reply to any video, audio or document</i>\n"
            "<i>/stream https://t.me/c/123/45 — one file</i>\n"
            "<i>/stream https://t.me/c/123/45-49 — a batch</i>\n"
            "<i>/stream -pl Name https://t.me/c/123/45-49 — one playlist page</i>\n"
            "<i>/stream -t https://t.me/c/123/9 ... — set the cover art</i>",
        )
        return

    status = await send_message(message, "<i>Generating links...</i>")

    try:
        if args["link"]:
            sources, asked = await _expand(args["link"])
        else:
            sources, asked = [reply], 1
    except Exception as e:
        LOGGER.error(f"stream link resolution failed: {e}")
        await edit_message(status, f"<b>Could not read that link.</b>\n\n<i>{e}</i>")
        return

    picked = []
    for msg in sources:
        try:
            picked.append((msg, media_of(msg)))
        except ValueError:
            continue

    if not picked:
        await edit_message(status, "<b>No playable media found in that link.</b>")
        return

    poster = None
    if args["poster"]:
        try:
            pmsg, _s = await get_tg_link_message(args["poster"])
            if pmsg and not isinstance(pmsg, list):
                poster = await _dump_copy(pmsg)
        except Exception as e:
            LOGGER.error(f"stream poster failed: {e}")

    try:
        minted = []
        for msg, media in picked:
            token = await _register(msg, poster)
            if token:
                minted.append((token, media))
    except Exception as e:
        LOGGER.error(f"stream link generation failed: {e}")
        await edit_message(status, f"<b>Failed to generate links.</b>\n\n<i>{e}</i>")
        return

    if not minted:
        await edit_message(status, "<b>Could not allocate links. Try again.</b>")
        return

    base = Config.BASE_URL.rstrip("/")
    buttons = ButtonMaker()

    if args["playlist"]:
        first = getattr(minted[0][1], "file_name", "") or "Playlist"
        title = args["name"] or first
        token = await _mint_playlist(title, [t for t, _m in minted], poster)
        if not token:
            await edit_message(status, "<b>Could not allocate a playlist. Try again.</b>")
            return
        total = sum(getattr(m, "file_size", 0) or 0 for _t, m in minted)
        page = f"{base}/playlist/{token}"
        msg = "<b>〶 Playlist Generated</b>\n\n"
        msg += f"<b>┎ Name</b> → <code>{escape(title)}</code>\n"
        msg += f"<b>┠ Files</b> → {len(minted)} of {asked}\n"
        msg += f"<b>┖ Size</b> → {get_readable_file_size(total)}\n\n"
        msg += f"<b>Task By: </b>{message.from_user.mention if message.from_user else 'N/A'}"
        buttons.url_button("▶️ Open Playlist", page, style=ButtonStyle.PRIMARY)
        buttons.url_button("🔗 Share", f"https://t.me/share/url?url={page}")
        await edit_message(status, msg, buttons.build_menu(2))
        await delete_message(message)
        return

    if len(minted) == 1:
        token, media = minted[0]
        name = getattr(media, "file_name", "") or "Media"
        size = getattr(media, "file_size", 0) or 0
        mime = getattr(media, "mime_type", "") or ""
        watch = f"{base}/xstrm/{token}"
        direct = f"{base}/dl/{token}"

        msg = "<b>〶 Stream Links Generated</b>\n\n"
        msg += f"<b>┎ Name</b> → <code>{escape(name)}</code>\n"
        msg += f"<b>┠ Size</b> → {get_readable_file_size(size)}\n"
        msg += f"<b>┖ Type</b> → {escape(mime) if mime else 'unknown'}\n\n"
        if not _playable(media):
            msg += "<i>Not a media type browsers can play — use the download link.</i>\n\n"
        msg += f"<b>Task By: </b>{message.from_user.mention if message.from_user else 'N/A'}"

        if _playable(media):
            buttons.url_button("▶️ Stream", watch, style=ButtonStyle.PRIMARY)
        buttons.url_button("⬇️ Download", direct, style=ButtonStyle.SUCCESS)
        buttons.url_button(
            "🔗 Share",
            f"https://t.me/share/url?url={watch if _playable(media) else direct}",
        )
        await edit_message(status, msg, buttons.build_menu(2))
        await delete_message(message)
        return

    total = sum(getattr(m, "file_size", 0) or 0 for _t, m in minted)
    shown = minted[:_MAX_BUTTONS]
    msg = "<b>〶 Stream Links Generated</b>\n\n"
    msg += f"<b>┎ Files</b> → {len(minted)} of {asked}\n"
    msg += f"<b>┖ Size</b> → {get_readable_file_size(total)}\n\n"
    if len(minted) > len(shown):
        msg += f"<i>Showing the first {len(shown)}. Use -pl for one page.</i>\n\n"
    msg += f"<b>Task By: </b>{message.from_user.mention if message.from_user else 'N/A'}"

    for i, (token, media) in enumerate(shown, 1):
        label = getattr(media, "file_name", "") or f"File {i}"
        if len(label) > 28:
            label = label[:27] + "…"
        target = "xstrm" if _playable(media) else "dl"
        buttons.url_button(f"{i}. {label}", f"{base}/{target}/{token}")
    await edit_message(status, msg, buttons.build_menu(1))
    await delete_message(message)
