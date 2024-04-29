#!/usr/bin/env python3
import asyncio
import os
import re
import time
from urllib.parse import urlparse

import aiofiles
import aiohttp
import telegraph
from pyrogram.handlers import MessageHandler, CallbackQueryHandler
from pyrogram.filters import command, regex
from pyrogram.errors import FloodWait

from bot import bot, LOGGER, config_dict, DATABASE_URL
from bot.helper.telegram_helper.message_utils import sendMessage, editMessage, deleteMessage
from bot.helper.ext_utils.bot_utils import handleIndex, new_task
from bot.helper.telegram_helper.filters import CustomFilters
from bot.helper.telegram_helper.bot_commands import BotCommands
from bot.helper.ext_utils.db_handler import DbManger
from bot.helper.telegram_helper.button_build import ButtonMaker

async def picture_add(_, message):
    editable = await sendMessage(message, "Fetching Input...")
    args = message.command[1:]
    msg_text = ""
    if len(args) > 0:
        msg_text = args[0]
    elif message.reply_to_message:
        msg_text = message.reply_to_message.text or message.reply_to_message.caption
    else:
        await editMessage(editable, "Invalid input. Use /addimage [image_url] or reply to an image.")
        return

    if not msg_text.startswith("http"):
        await editMessage(editable, "Image URL must start with 'http'")
        return

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(msg_text) as resp:
                if resp.status != 200:
                    await editMessage(editable, "Failed to download image.")
                    return
              
