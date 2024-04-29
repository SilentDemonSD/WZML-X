#!/usr/bin/env python3
import asyncio
from functools import wraps
from typing import Callable, Coroutine

import pyrogram
from pyrogram.errors import UserIsBlocked, MessageNotModified
from pyrogram.handlers import MessageHandler
from pyrogram.filters import command, regex

from bot import bot
from bot.helper.mirror_utils.upload_utils.gdriveTools import GoogleDriveHelper
from bot.helper.telegram_helper.message_utils import deleteMessage, sendMessage, sendPhoto
from bot.helper.telegram_helper.filters import CustomFilters
from bot.helper.telegram_helper.bot_commands import BotCommands
from bot.helper.ext_utils.bot_utils import is_gdrive_link, human_readable
from bot.helper.themes import BotTheme


async def send_typing_action(func: Callable[[pyrogram.types.Message], Coroutine]):
    @wraps(func)
    async def wrapper(message: pyrogram.types.Message, *args, **kwargs):
        await bot.send_chat_action(message.chat.id, "typing")
        return await func(message, *args, **kwargs)

    return wrapper


@send_typing_action
async def count_node(client, message):
    args = message.text.split()
    username = message.from_user.username
    tag = f"@{username}" if username else message.from_user.mention

    link = args[1] if len(args) > 1 else None
    if not link:
        reply_to = message.reply_to_message
        if reply_to:
            link = reply_to.text.split(maxsplit=1)[0].strip()

    if is_gdrive_link(link):
        try:
            await deleteMessage(message)
        except MessageNotModified:
            pass

        msg = await sendMessage(message, BotTheme('COUNT_MSG', LINK=link))
        gd = GoogleDriveHelper()
        name, mime_type, size, files, folders = await gd.count(link)

        if mime_type is None:
            await sendMessage(message, name)
            return

        await deleteMessage(msg)

        msg = BotTheme('COUNT_NAME', COUNT_NAME=name)
        msg += BotTheme('COUNT_SIZE', COUNT_SIZE=human_readable(size))
        msg += BotTheme('COUNT_TYPE', COUNT_TYPE=mime_type)

        if mime_type == 'Folder':
            msg += BotTheme('COUNT_SUB', COUNT_SUB=folders)
            msg += BotTheme('COUNT_FILE', COUNT_FILE=files)

        msg += BotTheme('COUNT_CC', COUNT_CC=tag)
        await sendPhoto(message, msg, 'IMAGES')
    else:
        await sendMessage(message, 'Send Gdrive link along with command or by replying to the link by command',
                          photo='IMAGES')


bot.add_handler(MessageHandler(count_node, filters=command(BotCommands.CountCommand) & CustomFilters.authorized & ~CustomFilters.blacklisted))
