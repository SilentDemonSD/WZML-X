#!/usr/bin/env python3

import argparse
import asyncio
import time
from typing import Dict, Any, Optional

import pyrogram
from pyrogram.filters import command, regex
from pyrogram.handlers import CallbackQueryHandler, MessageHandler
from pyrogram.types import Message, CallbackQuery, InputMediaPhoto
from bot import bot, bot_cache, categories_dict, download_dict, download_dict_lock
from bot.helper.ext_utils.bot_utils import MirrorStatus, arg_parser, fetch_user_tds, fetch_user_dumps, getDownloadByGid, is_gdrive_link, new_task, sync_to_async, get_readable_time
from bot.helper.ext_utils.help_messages import CATEGORY_HELP_MESSAGE
from bot.helper.mirror_utils.upload_utils.gdriveTools import GoogleDriveHelper
from bot.helper.telegram_helper.bot_commands import BotCommands
from bot.helper.telegram_helper.button_build import ButtonMaker
from bot.helper.telegram_helper.filters import CustomFilters
from bot.helper.telegram_helper.message_utils import editMessage, sendMessage, open_category_btns

def parse_arguments(args: list) -> Dict[str, Any]:
    """
    Parse command line arguments.

    :param args: List of command line arguments
    :return: Dictionary of parsed arguments
    """
    parser = argparse.ArgumentParser(description="Change the category of a download task.")
    parser.add_argument('-id', type=str, help="GDrive ID of the file")
    parser.add_argument('-index', type=str, help="Index link of the category")
    parser.add_argument('link', type=str, help="GID or reply to a message")
    return parser.parse_args(args).__dict__

async def change_category(client: pyrogram.Client, message: Message) -> None:
    """
    Change the category of a download task.

    :param client: Pyrogram client
    :param message: Received message
    """
    user_id = message.from_user.id
    args = parse_arguments(message.text.split()[1:])

    if not categories_dict:
        await sendMessage(message, "No categories defined!")
        return

    if download_dict is None or client is None:
        await sendMessage(message, "Internal error: missing download_dict or client object!")
        return

    drive_id = args['id']
    index_link = args['index']
    gid = args['link']

    if drive_id and is_gdrive_link(drive_id):
        drive_id = GoogleDriveHelper.getIdFromUrl(drive_id)

    dl: Optional[Dict[str, Any]] = None
    if gid.isdigit():
        dl = download_dict.get(int(gid), None)
    elif gid.startswith('gid:'):
        dl = await getDownloadByGid(gid[4:])

    if not dl:
        await sendMessage(message, "This is not an active task!" if gid.isdigit() else f"GID: <code>{gid[4:]}</code> Not Found.")
        return

    if not await CustomFilters.sudo(client, message) and dl.get('user_id') != user_id:
        await sendMessage(message, "You do not have permission to change the category of this task!")
        return

    if not index_link:
        await sendMessage(message, CATEGORY_HELP_MESSAGE)
        return

    category = categories_dict.get(index_link)
    if not category:
        await sendMessage(message, "Invalid category!")
        return

    async with download_dict_lock:
        dl['category'] = category

    await sendMessage(message, f"Category changed to {category}!")
