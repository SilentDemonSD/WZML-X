#!/usr/bin/env python3
import asyncio
import os
import re
import shlex
from pathlib import Path

import aiohttp
import aiofiles
from pyrogram.handlers import MessageHandler
from pyrogram.filters import command
from pyrogram.errors import UserIsBlocked, MessageNotModified, ChatWriteForbidden

from bot import LOGGER, bot, config_dict
from bot.helper.telegram_helper.filters import CustomFilters
from bot.helper.telegram_helper.bot_commands import BotCommands
from bot.helper.telegram_helper.message_utils import editMessage, sendMessage
from bot.helper.ext_utils.bot_utils import cmd_exec
from bot.helper.ext_utils.telegraph_helper import telegraph

MEDIAINFO_PATH = "Mediainfo/"

async def download_file(session, url, file_path):
    async with session.get(url, headers={"user-agent": "Mozilla/5.0"}) as response:
        if response.status != 200:
            raise Exception(f"Failed to download file: {response.status}")
        async with aiofiles.open(file_path, "wb") as f:
            while True:
                chunk = await response.content.read(10000000)
                if not chunk:
                    break
                await f.write(chunk)

async def generate_mediainfo(message, link=None, media=None, mmsg=None):
    temp_send = await sendMessage(message, "Generating MediaInfo...")
    try:
        if link:
            file_name = re.search(".+/(.+)", link).group(1)
            file_path = Path(MEDIAINFO_PATH) / file_name
            async with aiohttp.ClientSession() as session:
                await download_file(session, link, file_path)
        elif media:
            file_path = Path(MEDIAINFO_PATH) / media.file_name
            if media.file_size <= 50000000:
              
