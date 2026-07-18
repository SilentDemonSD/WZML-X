from contextlib import suppress
from pyrogram.enums import ButtonStyle
from re import IGNORECASE, findall, search

from imdbio import search_title, get_movie, get_akas, get_media_gallery
from pycountry import countries as conn
from pyrogram.errors import MediaEmpty, PhotoInvalidDimensions, WebpageMediaEmpty

from ..core.tg_client import TgClient
from ..core.config_manager import Config
from ..helper.ext_utils.status_utils import get_readable_time
from ..helper.telegram_helper.button_build import ButtonMaker
from ..helper.telegram_helper.message_utils import (
    send_message,
    edit_message,
    delete_message,
)
from ..helper.ext_utils.bot_utils import sync_to_async

IMDB_GENRE_EMOJI = {
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
LIST_ITEMS = 4


async def imdb_search(_, message):
    if message.text and " " in message.text:
        k = await send_message(message, "<i>Searching IMDB ...</i>")
        title = message.text.split(" ", 1)[1]
        user_id = message.from_user.id
        buttons = ButtonMaker()
        if result := search(r"tt(\d+)", title, IGNORECASE):
            movieid = result.group(1)
            if movie := await sync_to_async(get_movie, movieid):
                buttons.data_button(
                    f"{movie.title} ({getattr(movie, 'year', 'N/A')})",
                    f"imdb {user_id} movie {movieid}",
                )
            else:
                return await edit_message(k, "<i>No Results Found</i>")
        else:
            movies = await sync_to_async(get_poster, title, bulk=True)
            if not movies:
                return await edit_message(
                    k, "<i>No Results Found</i>, Try Again or Use <b>Title ID</b>"
                )
            for movie in movies:
                buttons.data_button(
                    f"{movie.title} ({getattr(movie, 'year', 'N/A')})",
                    f"imdb {user_id} movie {movie.id}",
                )
        buttons.data_button(
            "Close", f"imdb {user_id} close", style=ButtonStyle.DANGER
        )
        await edit_message(
            k, "<b><i>Search Results found on IMDb.com</i></b>", buttons.build_menu(1)
        )
    else:
        await send_message(
            message,
            "<i>Send Movie / TV Series Name along with /imdb Command or send IMDB URL</i>",
        )


def get_poster(query, bulk=False, id=False, file=None):
    if not id:
        query = (query.strip()).lower()
        title = query
        year = findall(r"[1-2]\d{3}$", query, IGNORECASE)
        if year:
            year = list_to_str(year[:1])
            title = (query.replace(year, "")).strip()
        elif file is not None:
            year = findall(r"[1-2]\d{3}", file, IGNORECASE)
            if year:
                year = list_to_str(year[:1])
        else:
            year = None
        movieid = search_title(title.lower()).titles
        if not movieid:
            return None
        if year:
            filtered = (
                list(filter(lambda k: str(k.year or "") == str(year), movieid))
                or movieid
            )
        else:
            filtered = movieid
        movieid = (
            list(filter(lambda k: k.kind in ["movie", "tvSeries"], filtered))
            or filtered
        )
        if bulk:
            return movieid
        movieid = movieid[0].id
    else:
        movieid = query
    movie = get_movie(movieid)
    if not movie:
        return None
    if getattr(movie, "release_date", None):
        date = movie.release_date
    elif getattr(movie, "year", None):
        date = movie.year
    else:
        date = "N/A"

    plot = None
    for keyword in ["plot", "summaries", "synopses"]:
        plot_data = getattr(movie, keyword, None)
        if type(plot_data) is list:
            plot = plot_data[0]
        else:
            plot = plot_data
        if plot:
            break

    plot_full = plot or ""
    if plot and len(plot) > 300:
        plot = f"{plot[:300]}..."

    trailer_list = getattr(movie, "trailers", None)
    trailer = trailer_list[-1] if trailer_list else None

    awards = getattr(movie, "awards", None)
    awards_text = "N/A"
    if awards:
        parts = []
        if getattr(awards, "wins", 0):
            parts.append(f"{awards.wins} win{'s' if awards.wins != 1 else ''}")
        if getattr(awards, "nominations", 0):
            parts.append(
                f"{awards.nominations} nominatio{'n' if awards.nominations == 1 else 'ns'}"
            )
        awards_text = ", ".join(parts) if parts else "N/A"

    company_credits = getattr(movie, "company_credits", None) or {}
    production = (
        list_to_str([c.name for c in company_credits.get("production", [])]) or "N/A"
    )

    kind = ""
    if movie.is_series():
        kind = "Series"
    elif movie.is_episode():
        kind = "Episode"
    elif getattr(movie, "kind", None):
        kind = movie.kind.capitalize()

    try:
        akas = get_akas(f"tt{movie.imdb_id}")
        seen_aka = set()
        aka_list = []
        for a in akas["akas"][:LIST_ITEMS * 2]:
            title = a.title
            if title.lower() not in seen_aka:
                seen_aka.add(title.lower())
                aka_list.append(title)
            if len(aka_list) >= LIST_ITEMS:
                break
        aka_text = list_to_str(aka_list) or "N/A"
    except Exception:
        aka_text = list_to_str(getattr(movie, "title_akas", []) or []) or "N/A"

    _box_office = getattr(movie, "box_office", None) or {}
    _end_year = getattr(movie, "year_end", None)
    _end_year_str = f"-{_end_year}" if _end_year else ""
    _certificate = getattr(movie, "certificate", None) or getattr(movie, "mpaa", None) or ""
    if not _certificate:
        _certs = getattr(movie, "certificates", {}) or {}
        for _key in ["US", "MPAA"]:
            if _key in _certs:
                _val = _certs[_key]
                if isinstance(_val, (list, tuple)) and len(_val) >= 2:
                    cert_val = str(_val[1]).strip() if _val[1] else ""
                    if cert_val:
                        _certificate = cert_val
                        break
        if not _certificate:
            for _val in _certs.values():
                if isinstance(_val, (list, tuple)) and len(_val) >= 2:
                    cert_val = str(_val[1]).strip() if _val[1] else ""
                    if cert_val:
                        _certificate = cert_val
                        break
    _keywords_list = getattr(movie, "storyline_keywords", []) or []
    _creators_list = (
        getattr(getattr(movie, "info_series", None), "creators", []) or []
    )
    _production_companies = (
        [c.name for c in getattr(movie, "company_credits", {}).get("production", [])]
        if getattr(movie, "company_credits", None)
        else []
    )

    return {
        "title": movie.title,
        "trailer": trailer or "https://imdb.com/",
        "votes": str(getattr(movie, "votes", "N/A") or "N/A"),
        "aka": aka_text,
        "seasons": (
            len(movie.info_series.display_seasons)
            if getattr(movie, "info_series", None)
            and getattr(movie.info_series, "display_seasons", None)
            else "N/A"
        ),
        "box_office": getattr(movie, "worldwide_gross", "N/A") or "N/A",
        "localized_title": getattr(movie, "title_localized", "N/A") or "N/A",
        "kind": kind,
        "imdb_id": f"tt{movie.imdb_id}",
        "cast": list_to_str([i.name for i in getattr(movie, "stars", [])]) or "N/A",
        "runtime": get_readable_time(int(getattr(movie, "duration", 0) or "0") * 60)
        or "N/A",
        "countries": list_to_hash(getattr(movie, "countries", []) or []) or "N/A",
        "languages": list_to_hash(getattr(movie, "languages_text", []) or []) or "N/A",
        "director": list_to_str([i.name for i in getattr(movie, "directors", [])])
        or "N/A",
        "writer": list_to_str(
            [i.name for i in getattr(movie, "categories", {}).get("writer", [])]
        )
        or "N/A",
        "producer": list_to_str(
            [i.name for i in getattr(movie, "categories", {}).get("producer", [])]
        )
        or "N/A",
        "composer": list_to_str(
            [i.name for i in getattr(movie, "categories", {}).get("composer", [])]
        )
        or "N/A",
        "cinematographer": list_to_str(
            [
                i.name
                for i in getattr(movie, "categories", {}).get("cinematographer", [])
            ]
        )
        or "N/A",
        "music_team": list_to_str(
            [
                i.name
                for i in getattr(movie, "categories", {}).get("music_department", [])
            ]
        )
        or "N/A",
        "release_date": getattr(movie, "release_date", "N/A") or date or "N/A",
        "year": str(getattr(movie, "year", "N/A") or "N/A"),
        "genres": list_to_hash(getattr(movie, "genres", []) or [], emoji=True) or "N/A",
        "genres_plain": list_to_plain(getattr(movie, "genres", []) or []) or "N/A",
        "countries_plain": list_to_plain(getattr(movie, "countries", []) or []) or "N/A",
        "languages_plain": list_to_plain(getattr(movie, "languages_text", []) or []) or "N/A",
        "poster": getattr(
            movie, "cover_url", "https://telegra.ph/file/5af8d90a479b0d11df298.jpg"
        )
        or "https://telegra.ph/file/5af8d90a479b0d11df298.jpg",
        "plot": plot or "N/A",
        "plot_full": plot_full or "N/A",
        "rating": str(getattr(movie, "rating", "N/A") or "N/A") + " / 10",
        "url": getattr(movie, "url", "N/A") or "N/A",
        "url_cast": f"https://www.imdb.com/title/tt{movieid}/fullcredits#cast",
        "url_releaseinfo": f"https://www.imdb.com/title/tt{movieid}/releaseinfo",
        "awards": awards_text,
        "production": production,
        "metascore": str(getattr(movie, "metacritic_rating", "") or ""),
        "end_year": _end_year_str,
        "certificate": _certificate,
        "keywords": " · ".join(_keywords_list[:10]) or "",
        "creators": list_to_str([i.name for i in _creators_list[:3]]) or "N/A",
        "budget": getattr(movie, "production_budget", "") or "",
        "box_opening": _box_office.get("opening_weekend", "") or "",
        "box_domestic": _box_office.get("domestic", "") or "",
        "release_country": getattr(movie, "release_country", "") or "",
        "production_companies": _production_companies,
    }


def list_to_plain(k):
    if not k:
        return ""
    return ", ".join(str(item) for item in k[:10])


def list_to_str(k):
    if not k:
        return ""
    elif len(k) == 1:
        return str(k[0])
    elif LIST_ITEMS:
        k = k[: int(LIST_ITEMS)]
        return " ".join(f"{elem}," for elem in k)[:-1] + " ..."
    else:
        return " ".join(f"{elem}," for elem in k)[:-1]


def list_to_hash(k, flagg=False, emoji=False):
    listing = ""
    if not k:
        return ""
    elif len(k) == 1:
        if not flagg:
            if emoji:
                return str(
                    IMDB_GENRE_EMOJI.get(k[0], "")
                    + " #"
                    + k[0].replace(" ", "_").replace("-", "_")
                )
            return str("#" + k[0].replace(" ", "_").replace("-", "_"))
        try:
            conflag = (conn.get(name=k[0])).flag
            return str(f"{conflag} #" + k[0].replace(" ", "_").replace("-", "_"))
        except AttributeError:
            return str("#" + k[0].replace(" ", "_").replace("-", "_"))
    elif LIST_ITEMS:
        k = k[: int(LIST_ITEMS)]
        for elem in k:
            ele = elem.replace(" ", "_").replace("-", "_")
            if flagg:
                with suppress(AttributeError):
                    conflag = (conn.get(name=elem)).flag
                    listing += f"{conflag} "
            if emoji:
                listing += f"{IMDB_GENRE_EMOJI.get(elem, '')} "
            listing += f"#{ele}, "
        return f"{listing[:-2]}"
    else:
        for elem in k:
            ele = elem.replace(" ", "_").replace("-", "_")
            if flagg:
                conflag = (conn.get(name=elem)).flag
                listing += f"{conflag} "
            listing += f"#{ele}, "
        return listing[:-2]


async def imdb_callback(_, query):
    message = query.message
    user_id = query.from_user.id
    data = query.data.split()
    if len(data) < 4:
        await query.answer()
        await delete_message(message)
        return
    if user_id != int(data[1]):
        await query.answer("Not Yours!", show_alert=True)
    elif data[2] == "movie":
        await query.answer("Processing...")
        imdb = await sync_to_async(get_poster, query=data[3], id=True)
        if not imdb:
            await query.answer("Not Found!", show_alert=True)
            await delete_message(message)
            return
        reply_to = getattr(message, "reply_to_message", None)
        if not reply_to:
            await delete_message(message)
            return
        buttons = ButtonMaker()
        if imdb["trailer"]:
            if isinstance(imdb["trailer"], list):
                buttons.url_button(
                    "IMDb Trailer", imdb["trailer"][-1], style=ButtonStyle.PRIMARY
                )
                imdb["trailer"] = list_to_str(imdb["trailer"])
            else:
                buttons.url_button(
                    "IMDb Trailer", imdb["trailer"], style=ButtonStyle.PRIMARY
                )
        buttons.data_button(
            "Close", f"imdb {user_id} close", style=ButtonStyle.DANGER
        )
        buttons = buttons.build_menu(1)

        title = imdb.get("title", "N/A")
        year = imdb.get("year", "N/A")
        end_year = imdb.get("end_year", "")
        aka = imdb.get("aka", "")
        rating = imdb.get("rating", "N/A")
        votes = imdb.get("votes", "N/A")
        metascore = imdb.get("metascore", "")
        kind = imdb.get("kind", "N/A")
        runtime = imdb.get("runtime", "N/A")
        certificate = imdb.get("certificate", "")
        genres = imdb.get("genres", "N/A")
        genres_plain = imdb.get("genres_plain", "N/A")
        release_date = imdb.get("release_date", "N/A")
        release_country = imdb.get("release_country", "")
        countries = imdb.get("countries", "N/A")
        countries_plain = imdb.get("countries_plain", "N/A")
        languages = imdb.get("languages", "N/A")
        languages_plain = imdb.get("languages_plain", "N/A")
        plot = imdb.get("plot", "N/A")
        plot_full = imdb.get("plot_full", "N/A")
        director = imdb.get("director", "N/A")
        creators = imdb.get("creators", "N/A")
        writer = imdb.get("writer", "N/A")
        cast = imdb.get("cast", "N/A")
        production_companies = imdb.get("production_companies", [])
        budget = imdb.get("budget", "")
        box_opening = imdb.get("box_opening", "")
        box_domestic = imdb.get("box_domestic", "")
        box_office = imdb.get("box_office", "N/A")
        keywords = imdb.get("keywords", "")
        url = imdb.get("url", "https://imdb.com/")
        poster = imdb.get("poster", "")

        year_text = f"{year}{end_year}" if end_year else year

        tagline_parts = []
        if kind:
            tagline_parts.append(f"<b>{kind.title()}</b>")
        if runtime and runtime != "N/A":
            tagline_parts.append(f"<i>{runtime}</i>")
        if certificate:
            tagline_parts.append(f"<b>{certificate}</b>")
        tagline = " | ".join(tagline_parts)

        gallery_html = ""
        all_images = [poster] if poster else []
        seen = set()
        if poster:
            seen.add(poster)
        try:
            gallery = await sync_to_async(
                get_media_gallery, data[3], locale="en"
            )
            if gallery and gallery.items:
                for item in gallery.items[:5]:
                    url = item.url
                    if url and url not in seen:
                        seen.add(url)
                        all_images.append(url)
        except Exception:
            pass
        if len(all_images) == 1:
            gallery_html = f'<img src="{all_images[0]}"/>\n'
        elif len(all_images) > 1:
            slides = "\n".join(
                f'<img src="{img}"/>' for img in all_images
            )
            gallery_html = f"<tg-slideshow>\n{slides}\n</tg-slideshow>\n"

        prod_html = ""
        if production_companies:
            prod_items = "".join(
                f"<li>{p}</li>" for p in production_companies[:6]
            )
            prod_html = f"""
<details>
<summary>Production companies</summary>
<ul>{prod_items}</ul>
</details>"""

        ratings_rows = ""
        if rating and rating != "N/A":
            ratings_rows += f"<tr><td>IMDb</td><td>{rating} ({votes} votes)</td></tr>"
        if metascore:
            ratings_rows += f"<tr><td>Metascore</td><td>{metascore}/100</td></tr>"
        ratings_table = ""
        if ratings_rows:
            ratings_table = f"""
<table bordered striped>
<caption>Ratings</caption>
<tr><th>Source</th><th>Score</th></tr>
{ratings_rows}
</table>"""

        info_rows = ""
        if genres_plain and genres_plain != "N/A":
            info_rows += f"<tr><td><b>Genres</b></td><td>{genres_plain}</td></tr>"
        rel = " | ".join(filter(None, [release_date, release_country]))
        if rel:
            info_rows += f"<tr><td><b>Release</b></td><td>{rel}</td></tr>"
        if countries_plain and countries_plain != "N/A":
            info_rows += f"<tr><td><b>Countries</b></td><td>{countries_plain}</td></tr>"
        if languages_plain and languages_plain != "N/A":
            info_rows += f"<tr><td><b>Languages</b></td><td>{languages_plain}</td></tr>"
        info_table = ""
        if info_rows:
            info_table = f"""
<table striped>
<caption>Info</caption>
{info_rows}
</table>"""

        plot_lines = plot_full.split("\n") if plot_full else [""]
        plot_formatted = "\n".join(f"> {line}" for line in plot_lines)

        credits_items = ""
        if director and director != "N/A":
            credits_items += f"<li><b>Director</b> — {director}</li>"
        if creators and creators != "N/A":
            credits_items += f"<li><b>Creators</b> — {creators}</li>"
        if writer and writer != "N/A":
            credits_items += f"<li><b>Writers</b> — {writer}</li>"
        if cast and cast != "N/A":
            credits_items += f"<li><b>Stars</b> — {cast}</li>"
        credits_html = ""
        if credits_items:
            credits_html = f"""
<h3>Credits</h3>
<ul>{credits_items}</ul>"""

        box_office_rows = ""
        if budget:
            box_office_rows += f"<tr><td><b>Budget</b></td><td><code>{budget}</code></td></tr>"
        if box_opening:
            box_office_rows += f"<tr><td><b>Opening Weekend</b></td><td><code>{box_opening}</code></td></tr>"
        if box_domestic:
            box_office_rows += f"<tr><td><b>Domestic</b></td><td><code>{box_domestic}</code></td></tr>"
        if box_office and box_office != "N/A":
            box_office_rows += f"<tr><td><b>Worldwide</b></td><td><code>{box_office}</code></td></tr>"
        box_office_table = ""
        if box_office_rows:
            box_office_table = f"""
<table bordered striped>
<caption>Box Office</caption>
{box_office_rows}
</table>"""

        keywords_html = ""
        if keywords:
            kw_items = "".join(
                f"<li><code>{kw.strip()}</code></li>"
                for kw in keywords.split(" · ")[:10]
                if kw.strip()
            )
            keywords_html = f"""
<details>
<summary>Keywords</summary>
<ul>{kw_items}</ul>
</details>"""

        template = Config.IMDB_TEMPLATE
        if template:
            cap = template.format(**imdb, **locals())
            if poster:
                try:
                    await TgClient.bot.send_photo(
                        chat_id=reply_to.chat.id,
                        caption=cap,
                        photo=poster,
                        reply_to_message_id=reply_to.id,
                        reply_markup=buttons,
                    )
                except (MediaEmpty, PhotoInvalidDimensions, WebpageMediaEmpty):
                    fallback_poster = poster.replace(".jpg", "._V1_UX360.jpg")
                    await send_message(
                        reply_to, cap, buttons, photo=fallback_poster
                    )
            else:
                await send_message(
                    reply_to,
                    cap,
                    buttons,
                    "https://telegra.ph/file/5af8d90a479b0d11df298.jpg",
                )
        else:
            rich_html = f"""<h1>{title}  ({year_text})</h1>
<i>{aka}</i>

{gallery_html}
<p>{tagline}</p>

{ratings_table}

{info_table}

<details>
<summary><b>Plot (tap to expand — spoilers)</b></summary>
<aside>{plot_formatted}</aside>
</details>

{credits_html}

{prod_html}

{box_office_table}

{keywords_html}

<hr/>

<a href="{url}">Open on IMDb</a>"""

            await TgClient.bot.send_message(
                reply_to.chat.id,
                rich_text=rich_html,
                reply_to_message_id=reply_to.id,
                reply_markup=buttons,
            )
        await delete_message(message)
    else:
        await query.answer()
        await delete_message(message, getattr(message, "reply_to_message", None))
