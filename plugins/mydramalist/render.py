from contextlib import suppress

from pycountry import countries

LIST_ITEMS = 4
DEFAULT_TEMPLATE = """<b>Title:</b> {title}
<b>Also Known As:</b> {aka}
<b>Rating ⭐️:</b> <i>{rating}</i>
<b>Release Info:</b> {aired_date}
<b>Genre:</b> {genres}
<b>MyDramaList URL:</b> {url}
<b>Country of Origin:</b> {country}

<b>Story Line:</b> {synopsis}

<a href='{url}'>Read More ...</a>"""

GENRE_EMOJI = {
    "Action": "🚀",
    "Adult": "🔞",
    "Adventure": "🌋",
    "Animation": "🎠",
    "Biography": "📜",
    "Comedy": "🪗",
    "Crime": "🔪",
    "Documentary": "🎞",
    "Drama": "🎭",
    "Family": "👨‍👩‍👧‍👦",
    "Fantasy": "🫧",
    "Film Noir": "🎯",
    "Game Show": "🎮",
    "History": "🏛",
    "Horror": "🧟",
    "Musical": "🎻",
    "Music": "🎸",
    "Mystery": "🧳",
    "News": "📰",
    "Reality-TV": "🖥",
    "Romance": "🥰",
    "Sci-Fi": "🌠",
    "Short": "📝",
    "Sport": "⛳",
    "Talk-Show": "👨‍🍳",
    "Thriller": "🗡",
    "War": "⚔",
    "Western": "🪩",
}


def _tag(name):
    return name.replace(" ", "_").replace("-", "_")


def _flag(name):
    with suppress(AttributeError, KeyError, LookupError):
        entry = countries.get(name=name)
        if entry is not None:
            return getattr(entry, "flag", "")
    return ""


def list_to_str(items, cast=False):
    if not items:
        return ""
    items = items[:LIST_ITEMS]
    if cast:
        return ", ".join(
            f'<a href="{item.get("link")}">{item.get("name")}</a>' for item in items
        )
    return ", ".join(str(item) for item in items)


def list_to_hash(items, flags=False, emoji=False):
    if not items:
        return ""
    parts = []
    for item in items[:LIST_ITEMS]:
        if not item:
            continue
        prefix = ""
        if flags:
            mark = _flag(item)
            if mark:
                prefix += f"{mark} "
        if emoji:
            mark = GENRE_EMOJI.get(item, "")
            if mark:
                prefix += f"{mark} "
        parts.append(f"{prefix}#{_tag(item)}")
    return ", ".join(parts)


def drama_fields(payload, synopsis_limit=300):
    details = payload.get("details") or {}
    others = payload.get("others") or {}
    plot = payload.get("synopsis") or ""
    if len(plot) > synopsis_limit:
        plot = f"{plot[:synopsis_limit]}..."
    poster = (payload.get("poster") or "").replace("c.jpg?v=1", "f.jpg?v=1").strip()
    return {
        "title": payload.get("title") or "",
        "score": details.get("score") or "",
        "aka": list_to_str(payload.get("also_known_as")),
        "episodes": details.get("episodes") or "",
        "type": details.get("type") or "",
        "cast": list_to_str(payload.get("casts"), cast=True),
        "country": list_to_hash([details.get("country")], flags=True),
        "aired_date": details.get("aired", "N/A"),
        "aired_on": details.get("aired_on") or "",
        "org_network": details.get("original_network") or "",
        "duration": details.get("duration") or "",
        "watchers": details.get("watchers") or "",
        "ranked": details.get("ranked") or "",
        "popularity": details.get("popularity") or "",
        "related_content": list_to_str(others.get("related_content")),
        "native_title": list_to_str(others.get("native_title")),
        "director": list_to_str(others.get("director")),
        "screenwriter": list_to_str(others.get("screenwriter")),
        "genres": list_to_hash(others.get("genres"), emoji=True),
        "tags": list_to_str(others.get("tags")),
        "poster": poster,
        "synopsis": plot,
        "rating": f"{payload.get('rating')} / 10",
        "content_rating": details.get("content_rating") or "",
        "url": payload.get("link") or "",
    }


def fill(template, fields):
    try:
        return template.format(**fields)
    except Exception:
        return DEFAULT_TEMPLATE.format(**fields)
