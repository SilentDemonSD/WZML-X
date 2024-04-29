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

import bot
from bot.helper.telegram_helper.filters import CustomFilters
from bot.helper.telegram_helper.bot_commands import BotCommands
from bot.helper.telegram_helper.message_utils import sendMessage, editMessage
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

async def imdb_search(client: bot.Bot, message: Message) -> None:
    if " " in message.text:
        k = await sendMessage(message, "<code>Searching IMDB ...</code>")
        title = message.text.split(" ", 1)[1]
        user_id = message.from_user.id
        buttons = ButtonMaker()
        if title.lower().startswith("https://www.imdb.com/title/tt"):
            movieid = title.replace("https://www.imdb.com/title/tt", "")
            if movie := imdb.get_movie(movieid):
                buttons.ibutton(f"🎬 {movie.get('title')} ({movie.get('year')})", f"imdb {user_id} movie {movieid}")
            else:
                return await editMessage(k, "<i>No Results Found</i>")
        else:
            movies = get_poster(title, bulk=True)
            if not movies:
                return editMessage("<i>No Results Found</i>, Try Again or Use <b>Title ID</b>", k)
            for movie in movies:
                buttons.ibutton(f"🎬 {movie.get('title')} ({movie.get('year')})", f"imdb {user_id} movie {movie.movieID}")
        buttons.ibutton("🚫 Close 🚫", f"imdb {user_id} close")
        await editMessage(k, '<b><i>Here What I found on IMDb.com</i></b>', buttons.build_menu(1))
    else:
        await sendMessage(message, '<i>Send Movie / TV Series Name along with /imdb Command or send IMDB URL</i>')


def get_poster(query, bulk=False, id=False, file=None) -> Union[List[Dict[str, Any]], Dict[str, Any]]:
    # ... (rest of the function)

def list_to_str(k) -> str:
    # ... (rest of the function)

def list_to_hash(k, flagg=False, emoji=False) -> str:
    # ... (rest of the function)

async def imdb_callback(client: bot.Bot, query:
