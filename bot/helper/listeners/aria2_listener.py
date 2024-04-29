#!/usr/bin/env python3
import asyncio
import logging
import time
from typing import Any, AsyncIterator, Callable, Optional

import aioaria2
import aiopath
import humanize
import walrus
from bot import aria2, download_dict_lock, download_dict, LOGGER, config_dict
from bot.helper.ext_utils.task_manager import limit_checker, create_task
from bot.helper.mirror_utils.upload_utils.gdriveTools import GoogleDriveHelper
from bot.helper.mirror_utils.status_utils.aria2_status import Aria2Status
from bot.helper.ext_utils.fs_utils import get_base_name, clean_unwanted
from bot.helper.ext_utils.bot_utils import getDownloadByGid
from bot.helper.telegram_helper.message_utils import sendMessage, deleteMessage, update_all_messages
from bot.helper.themes import BotTheme

logger = logging.getLogger(__name__)


async def on_download_started(api: aioaria2.Aria2, gid: str) -> None:
    ...

