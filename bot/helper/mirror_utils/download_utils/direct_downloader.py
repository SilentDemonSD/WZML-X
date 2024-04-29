import asyncio
import contextlib
import uuid
from typing import Dict, Any, List, Union, AsyncContextManager, Callable

import aiohttp
from bot.helper.ext_utils.bot_utils import sync_to_async
from bot.helper.ext_utils.task_manager import is_queued, stop_duplicate_check
from async_timeout import asyncio_timeout

@contextlib.asynccontextmanager
async def async_lock(lock):
    async with async_conditional_create(lock):
        yield lock

