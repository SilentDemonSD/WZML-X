import asyncio
import contextlib
import uuid
from typing import Dict, Any, List, Union, AsyncContextManager, Callable

import aiohttp
from bot.helper.ext_utils.bot_utils import sync_to_async  # Importing sync_to_async function from bot_utils module
from bot.helper.ext_utils.task_manager import is_queued, stop_duplicate_check  # Importing is_queued and stop_duplicate_check functions from task_manager module
from async_timeout import asyncio_timeout  # Importing asyncio_timeout function for setting timeouts in asynchronous context managers

@contextlib.asynccontextmanager
async def async_lock(lock):
    """
    Asynchronous context manager for handling locks.
    This function ensures that the lock is acquired before entering the block and released after exiting the block.
    """
    async with async_conditional_create(lock):
        yield lock

