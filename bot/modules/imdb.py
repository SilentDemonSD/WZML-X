#!/usr/bin/env python3
import asyncio
import re
from contextlib import suppress
from typing import List, Dict, Any, Union

import pycountry
from imdb import Cinemagoer
from pyrogram.errors import MediaEmpty, PhotoInvalidDimensions, WebpageMediaEmpty
from pyrogram.handlers import MessageHandler, CallbackQueryHandler
from pyrogram.filters import command, regex
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message

from bot import bot, LOGGER, user_data, config_dict
from bot.helper.telegram_helper.filters import CustomFilters
from bot.helper.telegram_helper.bot_commands import BotCommands
from bot.helper.telegram_helper.message_utils import sendMessage, editMessage
from bot.helper.ext_utils.bot_utils import get_readable_time
from bot.helper.telegram_helper.button_build import ButtonMaker

imdb = Cinemagoer()
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

async def imdb_search(client, message):
    if " " in message.text:
        query = message.text.split(" ", 1)[1]
        user_id = message.from_user.id
        buttons = ButtonMaker()

        if query.lower().startswith("https://www.imdb.com/title/tt"):
            movieid = query.replace("https://www.imdb.com/title/tt", "")
            movie = imdb.get_movie(movieid)
            if movie:
                buttons.ibutton(f"🎬 {movie.get('title')} ({movie.get('year')})", f"imdb {user_id} movie {movieid}")
            else:
                return await editMessage(message, "<i>No Results Found</i>")
        else:
            movies = get_poster(query, bulk=True)
            if not movies:
                return await editMessage(message, "<i>No Results Found</i>", parse_mode="HTML")
            for movie in movies:
                buttons.ibutton(f"🎬 {movie.get('title')} ({movie.get('year')})", f"imdb {user_id} movie {movie.movieID}")

        buttons.ibutton("🚫 Close 🚫", f"imdb {user_id} close")
        await editMessage(message, '<b><i>Here What I found on IMDb.com</i></b>', buttons.build_menu(1))
    else:
        await sendMessage(message, '<i>Send Movie / TV Series Name along with /imdb Command or send IMDB URL</i>')


def get_poster(query: str, bulk: bool = False, id: bool = False, file: str = None) -> Union[List[Dict[str, Any]], Dict[str, Any]]:
    query = query.strip().lower()
    title = query
    year = re.findall(r"[1-2]\d{3}$", query, re.IGNORECASE)
    if year:
        year = year[0]
        title = query.replace(year, "").strip()
    elif file is not None:
        year = re.findall(r"[1-2]\d{3}", file, re.IGNORECASE)
        if year:
            year = year[0]
    else:
        year = None

    movieid = imdb.search_movie(title, results=10)
    if not movieid:
        return [] if bulk else None

    if year:
        filtered = [movie for movie in movieid if str(movie.get("year")) == year] or movieid
    else:
        filtered = [movie for movie in movieid if movie.get("kind") in ["movie", "tv series"]] or movieid

    if bulk:
        return filtered

    movieid = filtered[0].movieID
    movie = imdb.get_movie(movieid)
    return movie


async def imdb_callback(client, query):
    user_id = query.from_user.id
    data = query.data.split()
    if user_id != int(data[1]):
        await query.answer("Not Yours!", show_alert=True)
    elif data[2] == "movie":
        await query.answer()
        imdb = get_poster(query=data[3], id=True)
        buttons = []
        if imdb.get("videos"):
            buttons.append(
                [
                    InlineKeyboardButton(
                        "▶️ IMDb Trailer ", url=str(imdb["videos"][-1]), switch_inline_query_current_chat=""
                    )
                ]
            )
            imdb["trailer"] = list_to_str(imdb["videos"])
        else:
            imdb["trailer"] = ""

        buttons.append([InlineKeyboardButton("🚫 Close 🚫", callback_data=f"imdb {user_id} close")])

        template = config_dict.get("IMDB_TEMPLATE")
        if imdb and template:
            cap = template.format(
                title=imdb.get("title"),
                trailer=imdb["trailer"],
                votes=imdb.get("votes"),
                aka=imdb.get("aka"),
                seasons=imdb.get("number of seasons"),
                box_office=imdb.get("box office"),
                localized_title=imdb.get("localized title"),
                kind=imdb.get("kind"),
                imdb_id=imdb["imdbID"],
                cast=imdb.get("cast"),
                runtime=imdb.get("runtimes", "0"),
                countries=imdb.get("countries"),
                certificates=imdb.get("certificates"),
                languages=imdb.get("languages"),
                director=imdb.get("director"),
                writer=imdb.get("writer"),
                producer=imdb.get("producer"),
                composer=imdb.get("composer"),
                cinematographer=imdb.get("cinematographer"),
                music_team=imdb.get("music department"),
                distributors=imdb.get("distributors"),
                release_date=imdb.get("release date"),
                year=imdb.get("year"),
                genres=imdb.get("genres"),
                poster=imdb.get("full-size cover url"),
                plot=imdb.get("plot"),
                rating=imdb.get("rating"),
                url=imdb["url"],
                url_cast=imdb["url_cast"],
                url_releaseinfo=imdb["url_releaseinfo"],
            )
        else:
            cap = "No Results"

        if imdb.get("full-size cover url"):
            try:
                await bot.send_photo(
                    chat_id=query.message.reply_to_message.chat.id,
                    caption=cap,
                    photo=imdb["full-size cover url"],
                    reply_to_message_id=query.message.reply_to_message.id,
                    reply_markup=InlineKeyboardMarkup(buttons),
                )
            except (MediaEmpty, PhotoInvalidDimensions, WebpageMediaEmpty):
                poster = imdb.get("full-size cover url").replace(".jpg", "._V1_UX360.jpg")
                await sendMessage(
                    message=query.message.reply_to_message,
                    text=cap,
                    reply_markup=InlineKeyboardMarkup(buttons),
                    parse_mode="HTML",
                    photo=poster,
                )
        else:
            await sendMessage(
                message=query.message.reply_to_message,
                text=cap,
                reply_markup=InlineKeyboardMarkup(buttons),
                parse_mode="HTML",
            )

        await query.message.delete()
    else:
        await query.answer()
        await query.message.delete()
        await query.message.reply_to_message.delete()


bot.add_handler(MessageHandler(imdb_search, filters=command(BotCommands.IMDBCommand) & CustomFilters.authorized & ~CustomFilters.blacklisted))
bot.add_handler(CallbackQueryHandler(imdb_callback, filters=regex(r'^imdb')))
