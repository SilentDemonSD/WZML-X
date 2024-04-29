#!/usr/bin/env python3
import re
from typing import List, Dict, Union
from urllib.parse import urlparse

import requests
from pyrogram.handlers import MessageHandler, CallbackQueryHandler
from pyrogram.filters import command, regex
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, InputMediaPhoto
from pyrogram.errors import MediaEmpty, PhotoInvalidDimensions, WebpageMediaEmpty

from bot import bot, LOGGER, user_data, config_dict
from bot.helper.telegram_helper.filters import CustomFilters
from bot.helper.telegram_helper.bot_commands import BotCommands
from bot.helper.telegram_helper.message_utils import sendMessage, editMessage
from bot.helper.ext_utils.bot_utils import get_readable_time
from bot.helper.telegram_helper.button_build import ButtonMaker

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

def get_imdb_id(url: str) -> str:
    if "imdb.com/title/tt" in url:
        return url.split("imdb.com/title/tt")[-1]
    return ""

async def get_imdb_data(query: str) -> Union[Dict, None]:
    if "http" not in query and "https" not in query:
        query = f"https://www.imdb.com/find?q={query}&s=tt&ttype=ft&ref_=fn_ft"
    try:
        response = requests.get(query)
        if response.status_code == 200:
            html_content = response.text
            start_index = html_content.index('"poster":"') + len('"poster":"')
            end_index = html_content.index('","image"', start_index)
            poster_url = html_content[start_index:end_index].replace("\\/", "/")
            start_index = html_content.index('"title":"') + len('"title":"')
            end_index = html_content.index('","year"', start_index)
            title = html_content[start_index:end_index]
            start_index = html_content.index('"year":"') + len('"year":"')
            end_index = html_content.index('","id"', start_index)
            year = html_content[start_index:end_index]
            start_index = html_content.index('"id":"') + len('"id":"')
            end_index = html_content.index('","type"', start_index)
            imdb_id = html_content[start_index:end_index]
            return {
                "poster": poster_url,
                "title": title,
                "year": year,
                "imdb_id": imdb_id,
            }
    except Exception as e:
        LOGGER.error(e)
    return None

async def imdb_search(client, message):
    if " " not in message.text:
        await sendMessage(message, '<i>Send Movie / TV Series Name along with /imdb Command or send IMDB URL</i>')
        return
    query = message.text.split(" ", 1)[1]
    user_id = message.from_user.id
    buttons = ButtonMaker()
    if "http" in query or "https" in query:
        imdb_id = get_imdb_id(query)
        if not imdb_id:
            await sendMessage(message, "Invalid IMDB URL")
            return
        movie_data = await get_imdb_data(f"https://www.imdb.com/title/{imdb_id}/")
        if not movie_data:
            await sendMessage(message, "No results found")
            return
    else:
        movie_data = await get_imdb_data(f"https://www.imdb.com/find?q={query}&s=tt&ttype=ft&ref_=fn_ft")
        if not movie_data:
            await sendMessage(message, "No results found")
            return
    buttons.ibutton(f"🎬 {movie_data['title']} ({movie_data['year']})", f"imdb {user_id} movie {movie_data['imdb_id']}")
    buttons.ibutton("🚫 Close 🚫", f"imdb {user_id} close")
    await editMessage(message, '<b><i>Here What I found on IMDb.com</i></b>', buttons.build_menu(1))

async def imdb_callback(client, query):
    message = query.message
    user_id = query.from_user.id
    data = query.data.split()
    if user_id != int(data[1]):
        await query.answer("Not Yours!", show_alert=True)
        return
    elif data[2] == "movie":
        await query.answer()
        movie_id = data[3]
        movie_data = await get_imdb_data(f"https://www.imdb.com/title/{movie_id}/")
        if not movie_data:
            await query.answer("No results found", show_alert=True)
            return
        buttons = []
        if movie_data.get("poster"):
            try:
                await bot.send_photo(
                    chat_id=query.message.reply_to_message.chat.id,
                    caption=movie_data["title"],
                    photo=movie_data["poster"],
                    reply_to_message_id=query.message.reply_to_message.id,
                    reply_markup=InlineKeyboardMarkup(buttons),
                )
            except (MediaEmpty, PhotoInvalidDimensions, WebpageMediaEmpty):
                await sendMessage(
                    message.reply_to_message,
                    movie_data["title"],
                    InlineKeyboardMarkup(buttons),
                    movie_data["poster"],
                )
        else:
            await sendMessage(
                message.reply_to_message,
                movie_data["title"],
                InlineKeyboardMarkup(buttons),
                'https://telegra.ph/file/5af8d90a479b0d11df298.jpg',
            )
        await message.delete()
    else:
        await query.answer()
        await query.message.delete()
        await query.message.reply_to_message.delete()

bot.add_handler(MessageHandler(imdb_search, filters=command(BotCommands.IMDBCommand) & CustomFilters.authorized & ~CustomFilters.blacklisted))
bot.add_handler(CallbackQueryHandler(imdb_callback, filters=regex(r'^imdb')))
