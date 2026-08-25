from collections import OrderedDict
from time import time
from urllib.parse import quote

from pyrogram.errors import MediaEmpty, PhotoInvalidDimensions, WebpageMediaEmpty

from bot import LOGGER
from bot.core.plugin_manager import PluginBase, get_plugin_manager
from bot.helper.ext_utils.bot_utils import new_task
from bot.helper.ext_utils.mem_guard import register_cache
from bot.helper.telegram_helper.button_build import ButtonMaker
from bot.helper.telegram_helper.message_utils import (
    delete_message,
    edit_message,
    send_message,
)

from .render import DEFAULT_TEMPLATE, drama_fields, fill

API = "https://kuryana.vercel.app"
TIMEOUT = 20
CACHE_TTL = 300
CACHE_MAX = 32
FALLBACK_IMAGE = "https://te.legra.ph/file/5af8d90a479b0d11df298.jpg"
_cache = OrderedDict()


def _cached(key):
    hit = _cache.get(key)
    if hit is None:
        return None
    stamp, value = hit
    if time() - stamp > CACHE_TTL:
        _cache.pop(key, None)
        return None
    _cache.move_to_end(key)
    return value


def _store(key, value):
    if value is None:
        return value
    _cache[key] = (time(), value)
    _cache.move_to_end(key)
    while len(_cache) > CACHE_MAX:
        _cache.popitem(last=False)
    return value


def cache_bytes():
    return sum(len(str(value)) for _, value in _cache.values())


def cache_clear(aggressive=False):
    if aggressive:
        _cache.clear()
        return
    while len(_cache) > CACHE_MAX // 2:
        _cache.popitem(last=False)


class MyDramaListPlugin(PluginBase):
    async def on_load(self):
        register_cache("mydramalist", cache_bytes, cache_clear)
        LOGGER.info("mydramalist plugin ready")
        return True

    async def on_unload(self):
        cache_clear(True)
        return True


async def _get(path):
    from niquests import AsyncSession

    try:
        async with AsyncSession() as session:
            response = await session.get(f"{API}{path}", timeout=TIMEOUT)
            if response.status_code != 200:
                LOGGER.error(f"mydramalist: HTTP {response.status_code} for {path}")
                return None
            return response.json()
    except Exception as err:
        LOGGER.error(f"mydramalist: {err}")
        return None


async def search_dramas(title):
    key = ("search", title.lower())
    hit = _cached(key)
    if hit is not None:
        return hit
    payload = await _get(f"/search/q/{quote(title)}")
    if not payload:
        return None
    results = (payload.get("results") or {}).get("dramas") or []
    return _store(key, results)


async def fetch_drama(slug):
    key = ("drama", slug)
    hit = _cached(key)
    if hit is not None:
        return hit
    payload = await _get(f"/id/{slug}")
    if not payload or not payload.get("data"):
        return None
    return _store(key, payload["data"])


def _settings():
    return get_plugin_manager().effective_config("mydramalist")


@new_task
async def mydramalist_command(_, message):
    parts = message.text.split(" ", 1)
    if len(parts) == 1:
        return await send_message(
            message,
            "<b>Format :</b>\n<code>/mdl</code> <i>[movie or drama name]</i>",
        )
    status = await send_message(message, "<i>Searching MyDramaList…</i>")
    dramas = await search_dramas(parts[1].strip())
    if not dramas:
        return await edit_message(
            status, "<i>No results found. Try a different title.</i>"
        )

    user_id = message.from_user.id
    buttons = ButtonMaker()
    for drama in dramas[: _settings().get("results", 8)]:
        buttons.data_button(
            f"{drama.get('title')} ({drama.get('year')})",
            f"mdl {user_id} drama {drama.get('slug')}",
        )
    buttons.data_button("Close", f"mdl {user_id} close", position="footer")
    await edit_message(
        status, "<b><i>Dramas found on MyDramaList</i></b>", buttons.build_menu(1)
    )


@new_task
async def mydramalist_callback(_, query):
    data = query.data.split()
    if len(data) < 3 or query.from_user.id != int(data[1]):
        return await query.answer("Not Yours!", show_alert=True)

    message = query.message
    if data[2] != "drama":
        await query.answer()
        await delete_message(message)
        return await delete_message(message.reply_to_message)

    await query.answer()
    payload = await fetch_drama(data[3])
    if not payload:
        return await edit_message(message, "<i>MyDramaList did not answer.</i>")

    fields = drama_fields(payload, _settings().get("synopsis_limit", 300))
    template = _settings().get("template") or DEFAULT_TEMPLATE
    caption = fill(template, fields)

    buttons = ButtonMaker()
    buttons.data_button("Close", f"mdl {data[1]} close", position="footer")
    target = message.reply_to_message or message
    poster = fields.get("poster")
    if poster:
        try:
            await target.reply_photo(
                poster, caption=caption, reply_markup=buttons.build_menu(1)
            )
        except (MediaEmpty, PhotoInvalidDimensions, WebpageMediaEmpty):
            await send_message(
                target,
                caption,
                buttons.build_menu(1),
                photo=poster.replace("f.jpg?v=1", "c.jpg?v=1"),
            )
    else:
        await send_message(target, caption, buttons.build_menu(1), photo=FALLBACK_IMAGE)
    await delete_message(message)
