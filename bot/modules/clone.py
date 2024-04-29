#!/usr/bin/env python3
import os
import asyncio
import json
import typing
from urllib.parse import urlparse

import aiofiles.os
import pyrogram.filters
import pyrogram.handlers
from pyrogram.errors import FloodWait
from pyrogram.types import Message, InlineKeyboardButton, InlineKeyboardMarkup

import bot
from bot.config import config_dict
from bot.constants import BotCommands
from bot.helper.ext_utils.bot_utils import (
    cmd_exec,
    delete_links,
    edit_or_reply,
    fetch_user_tds,
    get_readable_file_size,
    is_gdrive_link,
    is_rclone_path,
    new_task,
    sync_to_async,
)
from bot.helper.ext_utils.exceptions import DirectDownloadLinkException
from bot.helper.ext_utils.task_manager import limit_checker
from bot.helper.mirror_utils.download_utils.direct_link_generator import (
    direct_link_generator,
)
from bot.helper.mirror_utils.rclone_utils.list import RcloneList
from bot.helper.mirror_utils.rclone_utils.transfer import RcloneTransferHelper
from bot.helper.telegram_helper.button_build import ButtonMaker
from bot.helper.telegram_helper.filters import CustomFilters
from bot.helper.telegram_helper.message_utils import (
    sendMessage,
    sendStatusMessage,
)
from bot.helper.telegram_helper.telegram_client import TelegramClient
from bot.helper.themes import BotTheme

config: typing.Final = config_dict
RCLONE_PATH: typing.Final = config.get("RCLONE_PATH", "rcl")
STOP_DUPLICATE: typing.Final = config.get("STOP_DUPLICATE", False)

async def rclone_node(
    client: TelegramClient,
    message: Message,
    link: str,
    dst_path: str,
    rcf: str,
    tag: str,
) -> None:
    if not is_rclone_path(link):
        await sendMessage(message, "Invalid rclone path")
        return

    rclone_list = RcloneList(RCLONE_PATH)
    remote_info = rclone_list.get_remote_info(link)
    if not remote_info:
        await sendMessage(message, "Failed to get remote info")
        return

    if dst_path.startswith("/"):
        dst_path = dst_path[1:]

    try:
        rclone_transfer_helper = RcloneTransferHelper(
            RCLONE_PATH,
            remote_info["remote"],
            remote_info["path"],
            dst_path,
            rcf,
            STOP_DUPLICATE,
        )
        await rclone_transfer_helper.transfer()
        await sendMessage(message, f"Successfully transferred {remote_info['path']} to {dst_path} in {remote_info['remote']}")
    except Exception as e:
        await sendMessage(message, f"Error: {str(e)}")

@pyrogram.on_message(pyrogram.filters.command(BotCommands.RCLONE_NODE) & CustomFilters.authorized_chat)
async def rclone_node_command(client: TelegramClient, message: Message):
    if len(message.command) < 3:
        await sendMessage(message, "Usage: /rclonenode link destination_path remote_config_file tag")
        return

    link = message.command[1]
    dst_path = message.command[2]
    rcf = message.command[3] if len(message.command) > 3 else ""
    tag = message.command[4] if len(message.command) > 4 else ""

    await rclone_node(client, message, link, dst_path, rcf, tag)
