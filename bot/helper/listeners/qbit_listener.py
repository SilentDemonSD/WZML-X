#!/usr/bin/env python3

import asyncio
import aiohttp
import time
from typing import Any, Dict, Union, Optional, List, TypeVar, Awaitable
import logging as LOGGER
from bot.helper.mirror_utils.status_utils.qbit_status import QbittorrentStatus
from bot.helper.telegram_helper.message_utils import update_all_messages
from bot.helper.ext_utils.bot_utils import get_readable_time, getDownloadByGid
from bot.helper.ext_utils.fs_utils import clean_unwanted
from bot.helper.ext_utils.task_manager import limit_checker, stop_duplicate_check
from contextlib import asynccontextmanager

TASK_TYPE = TypeVar("TASK_TYPE", bound=Awaitable)

@asynccontextmanager
async def qb_listener_lock():
    yield QbTorrents

