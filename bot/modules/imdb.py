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
    """
    Handle the /imdb command to search for movies or TV series on IMDb.

    If the user provides a movie or TV series name, this function will search for it on IMDb and display a list of
    matching results. If the user provides an IMDb URL, this function will fetch the corresponding movie or TV series
    details.

    :param client: The Pyrogram bot client
    :param message: The incoming Telegram message
    :return: None
    """
    if " " in message.text:
        # ... (rest of the function)
    else:
        # ... (rest of the function)

def get_poster(query, bulk=False, id=False, file=None) -> Union[List[Dict[str, Any]], Dict[str, Any]]:
    """
    Fetch movie or TV series poster(s) from IMDb using the provided query.

    :param query: The search query
    :param bulk: Whether to return multiple posters in a list or a single poster as a dictionary
    :param id: Whether to return the poster by ID instead of fetching it from IMDb
    :param file: The file object of the poster to return
    :return: A list of dictionaries containing movie or TV series poster details or a single dictionary if `bulk` is
    False, or the file object of the poster if `id` and `file` are both True
    """
    # ... (rest of the function)

def list_to_str(k) -> str:
    """
    Convert a list of dictionaries to a single string.

    :param k: The list of dictionaries
    :return: A single string
    """
    # ... (rest of the function)

def list_to_hash(k, flagg=False, emoji=False) -> str:
    """
    Convert a list of dictionaries to a single string with hash tags.

    :param k: The list of dictionaries
    :param flagg: Whether to add hash tags before each item
    :param emoji: Whether to add emojis before each item
    :return: A single string
    """
    # ... (rest of the function)

async def imdb_callback(client: bot.Bot, query: CallbackQuery):
    """
    Handle IMDb callback queries.

    :param client: The Pyrogram bot client
    :param query: The incoming Telegram callback query
    :return: None
    """
    # ... (rest of the function)
