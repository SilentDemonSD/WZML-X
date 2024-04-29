#!/usr/bin/env python3
import asyncio
import secrets
from typing import Dict, Any, List, Union, AsyncContextManager

import aiohttp
from bot import (
    LOGGER,
    aria2_options,
    aria2c_global,
    download_dict,
    download_dict_lock,
    non_queued_dl,
    queue_dict_lock,
)
from bot.helper.ext_utils.bot_utils import sync_to_async
from bot.helper.ext_utils.task_manager import is_queued, stop_duplicate_check
from bot.helper.listeners.direct_listener import DirectListener
from bot.helper.mirror_utils.status_utils.direct_status import DirectStatus
from bot.helper.mirror_utils.status_utils.queue_status import QueueStatus
from bot.helper.telegram_helper.message_utils import sendMessage, sendStatusMessage
from contextlib import asynccontextmanager

@asynccontextmanager
async def acquire_download_dict_lock() -> AsyncContextManager[None]:
    async with download_dict_lock:
        yield

@asynccontextmanager
async def acquire_queue_dict_lock() -> AsyncContextManager[None]:
    async with queue_dict_lock:
        yield

async def add_direct_download(
    details: Dict[str, Union[str, int, bool, List[str]]],
    path: str,
    listener,
    foldername: str,
) -> None:
    """
    Adds a direct download to the download queue.

    :param details: A dictionary containing download details.
    :param path: The path to save the download.
    :param listener: The listener object.
    :param foldername: The name of the folder to save the download.
    :return: None
    """
    if not (contents := details.get("contents")):
        await sendMessage(listener.message, "There is nothing to download!")
        return
    size = details["total_size"]

    if not foldername:
        foldername = details["title"]
    path = f"{path}/{foldername}"

    msg, button = await stop_duplicate_check(foldername, listener)
    if msg:
        await sendMessage(listener.message, msg, button)
        return

    gid = secrets.token_hex(5)
    added_to_queue, event = await is_queued(listener.uid)
    if added_to_queue:
        LOGGER.info(f"Added to Queue/Download: {foldername}")
        async with acquire_download_dict_lock():
            download_dict[listener.uid] = QueueStatus(
                foldername, size, gid, listener, "dl"
            )
        await listener.onDownloadStart()
        await sendStatusMessage(listener.message)
        await event.wait()
        async with acquire_download_dict_lock():
            if listener.uid not in download_dict:
                return
    else:
        async with acquire_download_dict_lock():
            download_dict[listener.uid] = DirectStatus(
                DirectListener(foldername, size, path, listener, aria2_options),
                gid,
                listener,
                listener.upload_details,
            )

        async with acquire_queue_dict_lock():
            non_queued_dl.add(listener.uid)

        LOGGER.info(f"Download from Direct Download: {foldername}")
        await listener.onDownloadStart()
        await sendStatusMessage(listener.message)

        try:
            await sync_to_async(DirectListener.download, contents)
        finally:
            async with acquire_queue_dict_lock():
                non_queued_dl.discard(listener.uid)
