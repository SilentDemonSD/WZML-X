from html import escape
from secrets import token_urlsafe
from time import time

from pyrogram.enums import ButtonStyle

from .. import LOGGER
from ..core.config_manager import Config
from ..core.tg_client import TgClient
from ..helper.ext_utils.db_handler import database
from ..helper.ext_utils.links_utils import is_telegram_link
from ..helper.telegram_helper.bot_commands import BotCommands
from ..helper.telegram_helper.button_build import ButtonMaker
from ..helper.telegram_helper.message_utils import (
    delete_links,
    edit_message,
    get_tg_link_message,
    send_message,
)
from ..helper.ext_utils.status_utils import (
    get_raw_time,
    get_readable_file_size,
    get_readable_time,
)
from ..helper.telegram_helper.tg_transfer import media_of

_PLAYABLE = ("video/", "audio/")
_MAX_BATCH = 50
_MAX_BUTTONS = 20
_LABEL = 22


async def _mint_token(chat_id, msg_id, poster=None, exp=None):
    if not exp and not poster:
        existing = await database.find_stream(chat_id, msg_id)
        if existing:
            return existing
    for _ in range(6):
        token = token_urlsafe(5)
        if await database.get_stream(token) is None:
            await database.add_stream(token, chat_id, msg_id, poster, exp)
            return token
    return None


async def _mint_playlist(name, items, poster, exp):
    for _ in range(6):
        token = token_urlsafe(5)
        if await database.get_playlist(token) is None:
            await database.add_playlist(token, name, items, poster, exp)
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
    ttl = 0
    words = []
    want = None
    for part in parts:
        if want == "poster":
            want = None
            if is_telegram_link(part):
                poster = part
                continue
        elif want == "ttl":
            want = None
            seconds = get_raw_time(part)
            if seconds:
                ttl = seconds
                continue
        if part in ("-t", "-thumb"):
            want = "poster"
            continue
        if part in ("-ttl", "-expire"):
            want = "ttl"
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
        "ttl": ttl,
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


def _short(name, limit=_LABEL):
    name = name or "File"
    return name if len(name) <= limit else name[: limit - 1] + "…"


async def _register(message, poster=None, exp=None):
    chat_id, msg_id = await _dump_copy(message)
    return await _mint_token(chat_id, msg_id, poster, exp)


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


def _usage():
    one, two = BotCommands.StreamCommand[0], BotCommands.StreamCommand[1]
    return f"""
<b>By replying to media:</b>
<code>/{one} or /{two} [media]</code>

<b>By reply/sending telegram link:</b>
<code>/{one} or /{two} [link]</code>

<b>By sending a batch range:</b>
<code>/{one} or /{two} [link]-[last id]</code>

<b>As one playlist page:</b>
<code>/{one} -pl [name] [link range]</code>

<b>With cover art:</b>
<code>/{one} -t [photo link] [link]</code>

<b>Self expiring links:</b>
<code>/{one} -ttl [1d2h3m] [link]</code>
"""


def _head(title, rows, tag):
    msg = f"<b><i>{escape(title)}</i></b>\n│"
    for i, (label, value) in enumerate(rows):
        edge = "┟" if i == 0 else "┠"
        msg += f"\n{edge} <b>{label}</b> → {value}"
    msg += f"\n┖ <b>Task By</b> → {tag}\n\n"
    return msg


def _done(line):
    return "〶 <b><u>Action Performed :</u></b>\n" + f"⋗ <i>{line}</i>\n"


async def stream_links(_, message):
    blocked = _ready()
    if blocked:
        await send_message(message, blocked)
        return

    parts = (message.text or message.caption or "").split()[1:]
    args = parse_stream_args(parts)
    reply = message.reply_to_message

    if not args["link"] and not reply:
        await send_message(message, _usage())
        await delete_links(message)
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

    ttl = args["ttl"]
    exp = int(time() + ttl) if ttl else None

    try:
        minted = []
        for msg, media in picked:
            token = await _register(msg, poster, exp)
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
    tag = message.from_user.mention if message.from_user else "N/A"
    total = sum(getattr(m, "file_size", 0) or 0 for _t, m in minted)
    buttons = ButtonMaker()

    if args["playlist"]:
        title = args["name"] or (
            getattr(minted[0][1], "file_name", "") or "Playlist"
        )
        token = await _mint_playlist(
            title, [t for t, _m in minted], poster, exp
        )
        if not token:
            await edit_message(
                status, "<b>Could not allocate a playlist. Try again.</b>"
            )
            return
        rows = [
            ("Task Size", get_readable_file_size(total)),
            ("Total Files", f"{len(minted)} of {asked}"),
            ("In Mode", "#TgMedia"),
            ("Out Mode", "#Playlist"),
        ]
        if ttl:
            rows.append(("Expires In", get_readable_time(ttl)))
        page = f"{base}/playlist/{token}"
        msg = _head(title, rows, tag) + _done("Playlist page is ready")
        buttons.url_button("▶️ Open Playlist", page, style=ButtonStyle.PRIMARY)
        buttons.url_button("🔗 Share", f"https://t.me/share/url?url={page}")
        await edit_message(status, msg, buttons.build_menu(2))
        await delete_links(message)
        return

    if len(minted) == 1:
        token, media = minted[0]
        name = getattr(media, "file_name", "") or "Media"
        mime = getattr(media, "mime_type", "") or "unknown"
        watch = f"{base}/xstrm/{token}"
        direct = f"{base}/dl/{token}"
        rows = [
            ("Task Size", get_readable_file_size(total)),
            ("Type", escape(mime)),
            ("In Mode", "#TgMedia"),
            ("Out Mode", "#Stream" if _playable(media) else "#Download"),
        ]
        if ttl:
            rows.append(("Expires In", get_readable_time(ttl)))
        msg = _head(name, rows, tag)
        if _playable(media):
            msg += _done("Stream and download links are ready")
            buttons.url_button("▶️ Stream", watch, style=ButtonStyle.PRIMARY)
        else:
            msg += _done("Browsers cannot play this type, use download")
        buttons.url_button("⬇️ Download", direct, style=ButtonStyle.SUCCESS)
        buttons.url_button(
            "🔗 Share",
            f"https://t.me/share/url?url={watch if _playable(media) else direct}",
        )
        await edit_message(status, msg, buttons.build_menu(2))
        await delete_links(message)
        return

    shown = minted[:_MAX_BUTTONS]
    rows = [
        ("Task Size", get_readable_file_size(total)),
        ("Total Files", f"{len(minted)} of {asked}"),
        ("In Mode", "#TgMedia"),
        ("Out Mode", "#Stream"),
    ]
    if ttl:
        rows.append(("Expires In", get_readable_time(ttl)))
    title = getattr(minted[0][1], "file_name", "") or "Stream Links"
    msg = _head(title, rows, tag)
    if len(minted) > len(shown):
        msg += _done(f"Showing the first {len(shown)}, use -pl for one page")
    else:
        msg += _done("Stream and download links are ready")

    for token, media in shown:
        label = _short(getattr(media, "file_name", ""))
        if _playable(media):
            buttons.url_button(f"S: {label}", f"{base}/xstrm/{token}")
        buttons.url_button(f"D: {label}", f"{base}/dl/{token}")
    await edit_message(status, msg, buttons.build_menu(2))
    await delete_links(message)
