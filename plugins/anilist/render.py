from calendar import month_name
from datetime import datetime

from pycountry import countries

from bot.helper.ext_utils.status_utils import get_readable_time

from .queries import GENRES_EMOJI

DEFAULT_ANIME_TEMPLATE = """<b>{ro_title}</b>({na_title})
<b>Format</b>: <code>{format}</code>
<b>Status</b>: <code>{status}</code>
<b>Start Date</b>: <code>{startdate}</code>
<b>End Date</b>: <code>{enddate}</code>
<b>Season</b>: <code>{season}</code>
<b>Country</b>: {country}
<b>Episodes</b>: <code>{episodes}</code>
<b>Duration</b>: <code>{duration}</code>
<b>Average Score</b>: <code>{avgscore}</code>
<b>Genres</b>: {genres}
<b>Hashtag</b>: {hashtag}
<b>Studios</b>: {studios}

<b>Description</b>: <i>{description}</i>"""


def _date(block):
    if not block or not block.get("day") or not block.get("year"):
        return ""
    return f"{month_name[block['month']]} {block['day']}, {block['year']}"


def _country(code):
    if not code:
        return ""
    entry = countries.get(alpha_2=code)
    if entry is None:
        return f"#{code}"
    tag = f"#{entry.name.replace(' ', '_').replace('-', '_')}"
    flag = getattr(entry, "flag", "")
    return f"{flag} {tag}" if flag else tag


def _genres(names):
    return ", ".join(
        f"{GENRES_EMOJI.get(name, '')} #{name.replace(' ', '_').replace('-', '_')}"
        for name in names or []
    )


def _clip(text, limit):
    text = text or ""
    return f"{text[:limit]}...." if len(text) > limit else text


def anime_fields(media, description_limit=500):
    trailer = media.get("trailer") or {}
    if trailer.get("site") == "youtube" and trailer.get("id"):
        trailer = f"https://youtu.be/{trailer['id']}"
    else:
        trailer = ""

    season = media.get("season")
    duration = media.get("duration")
    return {
        "ro_title": media["title"].get("romaji") or "",
        "na_title": media["title"].get("native") or "",
        "en_title": media["title"].get("english") or "",
        "format": (media.get("format") or "").capitalize(),
        "status": (media.get("status") or "").capitalize(),
        "year": media.get("seasonYear") or "N/A",
        "startdate": _date(media.get("startDate")),
        "enddate": _date(media.get("endDate")),
        "season": f"{season.capitalize()} {media.get('seasonYear')}" if season else "",
        "country": _country(media.get("countryOfOrigin")),
        "episodes": media.get("episodes") or "N/A",
        "duration": get_readable_time(duration * 60) if duration else "N/A",
        "avgscore": f"{media['averageScore']}%" if media.get("averageScore") else "",
        "genres": _genres(media.get("genres")),
        "studios": ", ".join(
            f'<a href="{node["siteUrl"]}">{node["name"]}</a>'
            for node in (media.get("studios") or {}).get("nodes") or []
        ),
        "source": media.get("source") or "-",
        "hashtag": media.get("hashtag") or "N/A",
        "synonyms": ", ".join(media.get("synonyms") or []),
        "siteurl": media.get("siteUrl") or "",
        "trailer": trailer,
        "postup": datetime.fromtimestamp(media["updatedAt"]).strftime("%d %B, %Y")
        if media.get("updatedAt")
        else "",
        "description": _clip(media.get("description"), description_limit),
        "popularity": media.get("popularity") or "",
        "trending": media.get("trending") or "",
        "favourites": media.get("favourites") or "",
        "siteid": media.get("id"),
        "bannerimg": media.get("bannerImage") or "",
        "coverimg": (media.get("coverImage") or {}).get("large") or "",
    }


def fill(template, fields):
    try:
        return template.format(**fields).replace("<br>", "")
    except Exception:
        return DEFAULT_ANIME_TEMPLATE.format(**fields).replace("<br>", "")
