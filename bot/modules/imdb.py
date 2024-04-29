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

# Mapping of IMDb genres to corresponding emojis
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

# Number of list items to display in one page
LIST_ITEMS = 4

async def imdb_search(client: bot.Bot, message: Message) -> None:
    text = message.text.split(" ", 1)
    if len(text) == 1:
        await sendMessage(message, "Please provide a search query!")
        return
    query = text[1]
    try:
        movie = ia.search_movie(query)
    except Cinemagoer.IMDbError:
        movie = []
    if not movie:
        await sendMessage(message, "No results found!")
        return
    buttons = []
    for m in movie:
        buttons.append(
            [
                InlineKeyboardButton(
                    f"{m.title} ({m.year})",
                    callback_data=f"imdb_movie_{m.movieID}",
                )
            ]
        )
    if len(buttons) > LIST_ITEMS:
        buttons = buttons[:LIST_ITEMS]
        buttons.append(
            [
                InlineKeyboardButton(
                    "Next >>", callback_data=f"imdb_next_{len(buttons)}"
                )
            ]
        )
    await editMessage(
        message,
        f"Results for '{query}':",
        reply_markup=InlineKeyboardMarkup(buttons),
    )

def get_poster(query, bulk=False, id=False, file=None) -> Union[List[Dict[str, Any]], Dict[str, Any]]:
    # ... (rest of the function)

def list_to_str(k) -> str:
    # ... (rest of the function)

def list_to_hash(k, flagg=False, emoji=False) -> str:
    # ... (rest of the function)

async def imdb_callback(client: bot.Bot, query: CallbackQuery):
    # ... (rest of the function)

if __name__ == "__main__":
    # ... (rest of the code)
