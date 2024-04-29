#!/usr/bin/env python3
from typing import Final, List, Optional

import aiohttp
import pycountry
from urllib.parse import quote as q
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, InputMediaPhoto, InputMessagePhoto, InputMessagePhotoFileID
from pyrogram.raw.functions.messages import (
    SendMediaCommand,
    SendMessageCommand,
    EditMessageTextCommand,
    DeleteMessagesCommand,
    DeleteMessageCommand,
)
from pyrogram.raw.types import (
    InputMessageContent,
    InputMedia,
)
from pyrogram.errors import MediaEmpty, PhotoInvalidDimensions, WebpageMediaEmpty, ReplyMarkupInvalid
from pyrogram.filters import command, regex, ChatTypeFilter
from pyrogram.handlers import MessageHandler, CallbackQueryHandler
from bot import LOGGER, bot, config_dict, user_data
from bot.helper.telegram_helper.filters import CustomFilters
from bot.helper.telegram_helper.message_utils import send_message, edit_message
from bot.helper.telegram_helper.bot_commands import BotCommands
from bot.helper.telegram_helper.button_build import ButtonMaker

LIST_ITEMS: Final = 4
IMDB_GENRE_EMOJI: Final = {
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
MDL_API: Final = "http://kuryana.vercel.app/"  # Public API ! Do Not Abuse !

async def mydramalist_search(client, message):
    if " " in message.text:
        query = message.text.split(" ", 1)[1]
        user_id = message.from_user.id
        buttons = ButtonMaker()

        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(
                    f"{MDL_API}/search/q/{q(query)}"
                ) as resp:
                    data = await resp.json()
                    if resp.status != 200 or not data or not data.get("results", {}).get("dramas"):
                        return await edit_message(message, "<i>No Results Found</i>, Try Again or Use <b>MyDramaList Link</b>")
            except Exception as e:
                LOGGER.error(e)
                return await edit_message(message, "<i>Error occurred while searching MyDramaList</i>")

        for drama in data["results"]["dramas"]:
            buttons.button(
                f"🎬 {drama.get('title')} ({drama.get('year')})",
                f"mdl {user_id} drama {drama.get('slug')}",
            )

        buttons.button("🚫 Close 🚫", f"mdl {user_id} close")
        await edit_message(
            message,
            '<b><i>Dramas found on MyDramaList :</i></b>',
            buttons.build_menu(1),
        )
    else:
        await send_message(message, f'<i>Send Movie / TV Series Name along with /{BotCommands.MyDramaListCommand} Command</i>')


async def extract_mdl(slug):
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(
                f"{MDL_API}/id/{slug}"
            ) as resp:
                if resp.status != 200:
                    return None
                return await resp.json()
        except Exception as e:
            LOGGER.error(e)
            return None
