#!/usr/bin/env python3
import asyncio
import aiohttp
import aiofiles
import httpx
from typing import TypeVar, Optional, Tuple, Dict, Any, List, Union
from contextlib import asynccontextmanager
from bot import download_dict, download_dict_lock, get_client, LOGGER, config_dict, non_queued_dl, queue_dict_lock
from bot.helper.mirror_utils.status_utils.qbit_status import QbittorrentStatus
from bot.helper.telegram_helper.message_utils import sendMessage, deleteMessage, sendStatusMessage
from bot.helper.ext_utils.bot_utils import bt_selection_buttons, sync_to_async
from bot.helper.ext_utils.task_manager import is_queued

T = TypeVar('T')

@asynccontextmanager
async def async_open(file: Union[str, aiofiles.File], mode: str = 'r') -> aiofiles.File:
    async with aiofiles.open(file, mode) as f:
        yield f

