#!/usr/bin/env python3

import os
import asyncio
from typing import Dict, Any, Union, Optional

import aiofiles.os
from aiofiles.os import remove as aioremove, path as aiopath
from bot.helper.ext_utils.bot_utils import bt_selection_buttons, sync_to_async
from bot.helper.mirror_utils.status_utils.aria2_status import Aria2Status
from bot.helper.telegram_helper.message_utils import sendStatusMessage, sendMessage
from bot.helper.ext_utils.task_manager import is_queued
from bot.config import TORRENT_TIMEOUT

import aioaria2c
from aioaria2c.aioaria2c import Aria2c

async def add_aria2c_download(
    link: str,
    path: str,
    listener: Any,
    filename: Optional[str] = None,
    header: Optional[Dict[str, str]] = None,
    ratio: Optional[float] = None,
    seed_time: Optional[int] = None,
) -> None:
    """
    Add a download to Aria2 using aria2c with the given parameters.

    :param link: The download link.
    :param path: The path to save the download.
    :param listener: The listener object.
    :param filename: Optional filename.
    :param header: Optional headers.
    :param ratio: Optional seed ratio.
    :param seed_time: Optional seed time.
    """
    a2c_opt = {**aria2_options}  # Copy aria2_options to a2c_opt
    [a2c_opt.pop(k) for k in aria2c_global if k in aria2_options]  # Remove aria2c_global keys from a2c_opt
    a2c_opt["dir"] = path
    if filename:
        a2c_opt["out"] = filename
    if header:
        a2c_opt["header"] = header
    if ratio:
        a2c_opt["seed-ratio"] = ratio
    if seed_time:
        a2c_opt["seed-time"] = seed_time
    if TORRENT_TIMEOUT:
        a2c_opt["bt-stop-timeout"] = str(TORRENT_TIMEOUT)

    added_to_queue, event = await is_queued(listener.uid)
    if added_to_queue:
        if link.startswith("magnet:"):
            a2c_opt["pause-metadata"] = "true"
        else:
            a2c_opt["pause"] = "true"

    try:
        aria2 = Aria2c()
        await aria2.start()
        download = await aria2.add_download(link, **a2c_opt)
    except aioaria2c.exceptions.Aria2cException as e:
        LOGGER.debug(f"Aria2c Download Error: {e}")
        await sendMessage(listener.message, f"{e}")
        return
    except Exception as e:
        LOGGER.debug(f"Aria2c Download Error: {e}")
        await sendMessage(listener.message, f"Unexpected error: {e}")
        return
    finally:
        await aria2.stop()

    if await aiopath.exists(link):
        await aioremove(link)

    if download.error_message:
        error = str(download.error_message).replace("<", " ").replace(">", " ")
        LOGGER.debug(f"Aria2c Download Error: {error}")
        await sendMessage(listener.message, error)
        return

    gid = download.gid
    name = download.name
    async with download_dict_lock:
        download_dict[listener.uid] = Aria2Status(gid, listener, queued=added_to_queue)

    if added_to_queue:
        LOGGER.debug(f"Added to Queue/Download: {name}. Gid: {gid}")
        if not listener.select or not download.is_torrent:
            await sendStatusMessage(listener.message)
    else:
        async with queue_dict_lock:
            non_queued_dl.add(listener.uid)
        LOGGER.debug(f"Aria2Download started: {name}. Gid: {gid}")

    await listener.onDownloadStart()

    if not added_to_queue and (not listener.select or not config_dict["BASE_URL"]):
        await sendStatusMessage(listener.message)
    elif listener.select and download.is_torrent and not download.is_metadata:
        if not added_to_queue:
            await sync_to_async(aria2.client.force_pause, gid)
        buttons = bt_selection_buttons(gid)
        msg = "Your download paused. Choose files then press Done Selecting button to start downloading."
        await sendMessage(listener.message, msg, buttons)

    if added_to_queue:
        await event.wait()

        async with download_dict_lock:
            if listener.uid not in download_dict:
                return
            download = download_dict[listener.uid]
            download.queued = False
            new_gid = download.gid()

        await sync_to_async(aria2.client.unpause, new_gid)
        LOGGER.debug(f'Start Queued Download from Aria2c: {name}. Gid: {gid}')

        async with queue_dict_lock:
            non_queued_dl.add(listener.uid)


pip install aioaria2c
