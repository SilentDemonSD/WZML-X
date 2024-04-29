#!/usr/bin/env python3
# This is a Python 3 script for a Telegram bot that fetches anime, manga, and character information from AniList.

import asyncio
import re
from typing import Dict, List, Optional

import requests
from markdown import markdown
from pycountry import countries as conn
from urllib.parse import quote as q

from bot import bot, LOGGER, config_dict, user_data
from bot.helper.telegram_helper.filters import CustomFilters
from bot.helper.telegram_helper.bot_commands import BotCommands
from bot.helper.telegram_helper.message_utils import sendMessage, editMessage
from bot.helper.telegram_helper.button_build import ButtonMaker
from bot.helper.ext_utils.bot_utils import get_readable_time
from pyrogram.handlers import MessageHandler, CallbackQueryHandler
from pyrogram.filters import command, regex

GENRES_EMOJI: Dict[str, str] = {
    "Action": "👊",
    "Adventure": choice(["🪂", "🧗‍♀"]),
    "Comedy": "🤣",
    "Drama": " 🎭",
    "Ecchi": choice(["💋", "🥵"]),
    "Fantasy": choice(["🧞", "🧞‍♂", "🧞‍♀", "🌗"]),
    "Hentai": "🔞",
    "Horror": "☠",
    "Mahou Shoujo": "☯",
    "Mecha": "🤖",
    "Music": "🎸",
    "Mystery": "🔮",
    "Psychological": "♟",
    "Romance": "💞",
    "Sci-Fi": "🛸",
    "Slice of Life": choice(["☘", "🍁"]),
    "Sports": "⚽️",
    "Supernatural": "🫧",
    "Thriller": choice(["🥶", "🔪", "🤯"]),
}

ANIME_GRAPHQL_QUERY = """
query ($id: Int, $idMal: Int, $search: String) {
  Media(id: $id, idMal: $idMal, type: ANIME, search: $search) {
    ...anime_fields
  }
}
"""

character_query = """
query ($id: Int, $search: String) {
    Character (id: $id, search: $search) {
        ...character_fields
    }
}
"""

manga_query = """
query ($id: Int, $search: String) { 
    Media (id: $id, type: MANGA, search: $search) { 
        ...manga_fields
    }
}
"""

url = 'https://graphql.anilist.co'
sptext: str = ""

async def anilist(client, msg, aniid: Optional[int] = None, u_id: Optional[int] = None) -> None:
    # Implementation details

async def character(client, message, aniid: Optional[int] = None, u_id: Optional[int] = None) -> None:
    # Implementation details

async def setCharacButtons(client, query: str) -> None:
    # Implementation details

async def manga(client, message) -> None:
    # Implementation details

async def anime_help(client, message) -> None:
    # Implementation details

def setAnimeButtons(update, context) -> None:
    # Implementation details

def setCharacButtons(update, context) -> None:
    # Implementation details

bot.add_handler(MessageHandler(anilist, filters=command(BotCommands.AniListCommand) & CustomFilters.authorized & ~CustomFilters.blacklisted))
bot.add_handler(MessageHandler(character, filters=command("character") & CustomFilters.authorized & ~CustomFilters.blacklisted))
bot.add_handler(MessageHandler(manga, filters=command("manga") & CustomFilters.authorized & ~CustomFilters.blacklisted))
bot.add_handler(MessageHandler(anime_help, filters=command(BotCommands.AnimeHelpCommand) & CustomFilters.authorized & ~CustomFilters.blacklisted))
bot.add_handler(CallbackQueryHandler(setAnimeButtons, filters=regex(r'^anime')))
bot.add_handler(CallbackQueryHandler(setCharacButtons, filters=regex(r'^cha')))
