from urllib.parse import quote

from markdown import markdown

from bot import LOGGER
from bot.core.plugin_manager import PluginBase, get_plugin_manager
from bot.helper.ext_utils.bot_utils import new_task
from bot.helper.ext_utils.mem_guard import register_cache
from bot.helper.telegram_helper.button_build import ButtonMaker
from bot.helper.telegram_helper.message_utils import edit_message, send_message

from .api import cache_bytes, cache_clear, fetch_anime, fetch_character, fetch_manga
from .render import DEFAULT_ANIME_TEMPLATE, anime_fields, fill

FALLBACK_IMAGE = "https://te.legra.ph/file/8a5155c0fc61cc2b9728c.jpg"
SPOILER_LIMIT = 900
CHARACTER_LIMIT = 700


class AniListPlugin(PluginBase):
    async def on_load(self):
        register_cache("anilist", cache_bytes, cache_clear)
        LOGGER.info("anilist plugin ready")
        return True

    async def on_unload(self):
        cache_clear(True)
        return True


def _settings():
    return get_plugin_manager().effective_config("anilist")


def _template():
    return _settings().get("anime_template") or DEFAULT_ANIME_TEMPLATE


def _plain(text):
    return markdown(text or "").replace("<p>", "").replace("</p>", "")


async def _anime_view(media, user_id):
    fields = anime_fields(media, _settings().get("description_limit", 500))
    buttons = ButtonMaker()
    site_id = fields["siteid"]
    if fields["siteurl"]:
        buttons.url_button("AniList Info 🎬", fields["siteurl"], "header")
    if fields["trailer"]:
        buttons.url_button("Trailer 🎞", fields["trailer"], "header")
    for label, key in (
        ("Reviews 📑", "rev"),
        ("Tags 🎯", "tags"),
        ("Relations 🧬", "rel"),
        ("Streaming Sites 📊", "sts"),
        ("Characters 👥", "cha"),
    ):
        buttons.data_button(label, f"anime {user_id} {key} {site_id}")
    return fill(_template(), fields), buttons.build_menu(3)


@new_task
async def anime_command(_, message):
    parts = message.text.split(" ", 1)
    if len(parts) == 1:
        return await send_message(
            message, "<i>Provide AniList ID / Anime Name / MyAnimeList ID</i>"
        )
    query = parts[1].strip()
    variables = {"id": int(query)} if query.isdigit() else {"search": query}
    media = await fetch_anime(**variables)
    if not media:
        return await send_message(message, "<i>Nothing found on AniList.</i>")
    text, markup = await _anime_view(media, message.from_user.id)
    image = f"https://img.anili.st/media/{media.get('id')}"
    try:
        await send_message(message, text, markup, photo=image)
    except Exception:
        await send_message(message, text, markup, photo=FALLBACK_IMAGE)


def _tags(media):
    return "<b>Tags :</b>\n\n" + "\n".join(
        f'<a href="https://anilist.co/search/anime?genres={quote(tag["name"])}">'
        f'{tag["name"]}</a> {tag["rank"]}%'
        for tag in media.get("tags") or []
    )


def _links(media):
    return "<b>External & Streaming Links :</b>\n\n" + "\n".join(
        f'<a href="{link["url"]}">{link["site"]}</a>'
        for link in media.get("externalLinks") or []
    )


def _reviews(media):
    nodes = (media.get("reviews") or {}).get("nodes") or []
    return "<b>Reviews :</b>\n\n" + "\n\n".join(
        f'<a href="{item["siteUrl"]}">{item["summary"]}</a>\n'
        f'<b>Score :</b> <code>{item["score"]} / 100</code>\n'
        f'<i>By {item["user"]["name"]}</i>'
        for item in nodes[:8]
    )


def _relations(media):
    edges = (media.get("relations") or {}).get("edges") or []
    rows = []
    for edge in edges:
        node = edge.get("node") or {}
        title = node.get("title") or {}
        rows.append(
            f'<a href="{node.get("siteUrl")}">{title.get("english") or title.get("romaji")}</a>'
            f' ({title.get("romaji")})\n'
            f"<b>Format</b>: <code>{(node.get('format') or '').capitalize()}</code>\n"
            f"<b>Status</b>: <code>{(node.get('status') or '').capitalize()}</code>\n"
            f"<b>Average Score</b>: <code>{node.get('averageScore')}%</code>\n"
            f"<b>Source</b>: <code>{(node.get('source') or '').capitalize()}</code>\n"
            f"<b>Relation Type</b>: <code>{(edge.get('relationType') or 'N/A').capitalize()}</code>"
        )
    return "<b>Relations :</b>\n\n" + "\n\n".join(rows)


def _characters(media):
    edges = (media.get("characters") or {}).get("edges") or []
    rows = []
    for edge in edges[:8]:
        node = edge.get("node") or {}
        name = node.get("name") or {}
        rows.append(
            f'• <a href="{node.get("siteUrl")}">{name.get("full")}</a>'
            f' ({name.get("native")})\n'
            f"<b>Role :</b> {(edge.get('role') or '').capitalize()}"
        )
    return "<b>List of Characters :</b>\n\n" + "\n\n".join(rows)


SECTIONS = {
    "tags": _tags,
    "sts": _links,
    "rev": _reviews,
    "rel": _relations,
    "cha": _characters,
}


@new_task
async def anime_callback(_, query):
    data = query.data.split()
    if len(data) < 4 or query.from_user.id != int(data[1]):
        return await query.answer("Not Yours!", show_alert=True)

    action, site_id = data[2], data[3]
    await query.answer()
    media = await fetch_anime(id=int(site_id))
    if not media:
        return await edit_message(query.message, "<i>AniList did not answer.</i>")

    if action == "home":
        text, markup = await _anime_view(media, data[1])
        return await edit_message(query.message, text, markup)

    builder = SECTIONS.get(action)
    if builder is None:
        return
    buttons = ButtonMaker()
    buttons.data_button("⌫ Back", f"anime {data[1]} home {site_id}")
    body = builder(media)
    await edit_message(query.message, body, buttons.build_menu(1))


def _spoiler_of(description):
    if "~!" not in description or "!~" not in description:
        return "", description
    hidden = (
        description.split("~!", 1)[1]
        .rsplit("!~", 1)[0]
        .replace("~!", "")
        .replace("!~", "")
    )
    return hidden, description.split("~!", 1)[0]


async def _character_view(person, user_id):
    name = person.get("name") or {}
    header = f"<b>{name.get('full')}</b> (<code>{name.get('native')}</code>)\n\n"
    hidden, visible = _spoiler_of(person.get("description") or "")
    markup = None
    if hidden:
        buttons = ButtonMaker()
        buttons.data_button(
            "🔍 View Spoiler", f"cha {user_id} spoil {person.get('id')}"
        )
        markup = buttons.build_menu(1)
    if len(visible) > CHARACTER_LIMIT:
        visible = f"{visible[:CHARACTER_LIMIT]}...."
    return header + _plain(visible), markup


@new_task
async def character_command(_, message):
    parts = message.text.split(" ", 1)
    if len(parts) == 1:
        return await send_message(
            message,
            "<b>Format :</b>\n<code>/character</code> <i>[search AniList Character]</i>",
        )
    person = await fetch_character(search=parts[1].strip())
    if not person:
        return await send_message(message, "<i>No character found.</i>")
    text, markup = await _character_view(person, message.from_user.id)
    image = (person.get("image") or {}).get("large")
    if image:
        await send_message(message, text, markup, photo=image)
    else:
        await send_message(message, text, markup)


@new_task
async def character_callback(_, query):
    data = query.data.split()
    if len(data) < 4 or query.from_user.id != int(data[1]):
        return await query.answer("Not Yours!", show_alert=True)

    person = await fetch_character(id=int(data[3]))
    if not person:
        await query.answer()
        return await edit_message(query.message, "<i>AniList did not answer.</i>")

    if data[2] == "home":
        await query.answer()
        text, markup = await _character_view(person, data[1])
        return await edit_message(query.message, text, markup)

    await query.answer("Alert !! Shh")
    hidden, _ = _spoiler_of(person.get("description") or "")
    if len(hidden) > SPOILER_LIMIT:
        hidden = f"{hidden[:SPOILER_LIMIT]}..."
    buttons = ButtonMaker()
    buttons.data_button("⌫ Back", f"cha {data[1]} home {data[3]}")
    await edit_message(
        query.message,
        f"<b>Spoiler Ahead :</b>\n\n<tg-spoiler>{_plain(hidden)}</tg-spoiler>",
        buttons.build_menu(1),
    )


@new_task
async def manga_command(_, message):
    parts = message.text.split(" ", 1)
    if len(parts) == 1:
        return await send_message(
            message, "<b>Format :</b>\n<code>/manga</code> <i>[search manga]</i>"
        )
    media = await fetch_manga(search=parts[1].strip())
    if not media:
        return await send_message(message, "<i>No manga found.</i>")

    title = media.get("title") or {}
    lines = [f"<b>{title.get('romaji') or ''}</b>"]
    if title.get("native"):
        lines[0] += f" (<code>{title['native']}</code>)"
    if (media.get("startDate") or {}).get("year"):
        lines.append(f"<b>Start Date</b> → <code>{media['startDate']['year']}</code>")
    if media.get("status"):
        lines.append(f"<b>Status</b> → <code>{media['status']}</code>")
    if media.get("averageScore"):
        lines.append(f"<b>Score</b> → <code>{media['averageScore']}</code>")
    if media.get("genres"):
        lines.append("<b>Genres</b> → " + ", ".join(f"#{g}" for g in media["genres"]))
    description = (media.get("description") or "").replace("<br>", "")
    if description:
        lines.append(f"\n<i>{description}</i>")

    buttons = ButtonMaker()
    if media.get("siteUrl"):
        buttons.url_button("AniList Info", media["siteUrl"])
    text = "\n".join(lines)
    image = f"https://img.anili.st/media/{media.get('id')}"
    try:
        await send_message(message, text, buttons.build_menu(1), photo=image)
    except Exception:
        await send_message(message, text, buttons.build_menu(1))


@new_task
async def animehelp_command(_, message):
    await send_message(
        message,
        "⌬ <b><u>Anime Help</u></b>\n│\n"
        "┟ <b>/anime</b> → search AniList\n"
        "┠ <b>/character</b> → search an AniList character\n"
        "┖ <b>/manga</b> → search manga",
    )
