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
    ...

