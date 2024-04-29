#!/usr/bin/env python3

import os
from asyncio import get_event_loop
from aiofiles.os import remove as aioremove, path as aiopath
from typing import Dict, Any

# Import necessary modules and functions from the bot package
from bot import aria2, download_dict_lock, download_dict, LOGGER, config_dict, aria2_options, aria2c_global, non_queued_dl, queue_dict_lock
from bot.helper.ext_utils.bot_utils import bt_selection_buttons, sync_to_async
from bot.helper.mirror_utils.status_utils.aria2_status import Aria2Status
from bot.helper.telegram_helper.message_utils import sendStatusMessage, sendMessage
from bot.helper.ext_utils.task_manager import is_queued

async def add_aria2c_download(link: str, path: str, listener: Any, filename: str = None, header: Dict[str, str] = None, ratio: float = None, seed_time: int = None) -> None:
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
    a2c_opt['dir'] = path
    if filename:
        a2c_opt['out'] = filename
    if header:
        a2c_opt['header'] = header
    if ratio:
        a2c_opt['seed-ratio'] = ratio
    if seed_time:
        a2c_opt['seed-time'] = seed_time
    if TORRENT_TIMEOUT := config_dict['TORRENT_TIMEOUT']:
        a2c_opt['bt-stop-timeout'] = f'{TORRENT_TIMEOUT}'

    # Check if the download is already in the queue
    added_to_queue, event = await is_queued(listener.uid)
    if added_to_queue:
        if link.startswith('magnet:'):
            a2c_opt['pause-metadata'] = 'true'
        else:
            a2c_opt['pause'] = 'true'

    try:
        # Add the download to Aria2
        download = (await sync_to_async(aria2.add, link, a2c_opt))[0]
    except Exception as e:
        LOGGER.info(f"Aria2c Download Error: {e}")
        await sendMessage(listener.message, f'{e}')
        return

    # Remove the link file if it exists
    if await aiopath.exists(link):
        await aioremove(link)

    # Check for error messages in the download
    if download.error_message:
        error = str(download.error_message).replace('<', ' ').replace('>', ' ')
        LOGGER.info(f"Aria2c Download Error: {error}")
        await sendMessage(listener.message, error)
        return

    # Store the download in the download_dict
    gid = download.gid
    name = download.name
    async with download_dict_lock:
        download_dict[listener.uid] = Aria2Status(
            gid, listener, queued=added_to_queue)

    # Actions if the download is added to the queue
    if added_to_queue:
        LOGGER.info(f"Added to Queue/Download: {name}. Gid: {gid}")
        if not listener.select or not download.is_torrent:
            await sendStatusMessage(listener.message)
    else:
        async with queue_dict_lock:
            non_queued_dl.add(listener.uid)
        LOGGER.info(f"Aria2Download started: {name}. Gid: {gid}")

    # Call the onDownloadStart method of the listener
    await listener.onDownloadStart()

    # Actions if the download is not added to the queue
    if not added_to_queue and (not listener.select or not config_dict['BASE_URL']):
        await sendStatusMessage(listener.message)
    elif listener.select and download.is_torrent and not download.is_metadata:
        if not added_to_queue:
            await sync_to_async(aria2.client.force_pause, gid)
        SBUTTONS = bt_selection_buttons(gid)
        msg = "Your download paused. Choose files then press Done Selecting button to start downloading."
        await sendMessage(listener.message, msg, SBUTTONS)

    # Wait for the event if the download is added to the queue
    if added_to_queue:
        await event.wait()

        async with download_dict_lock:
            if listener.uid not in download_dict:
                return
            download = download_dict[listener.uid]
            download.queued = False
            new_gid = download.gid()

        # Unpause the download
        await sync_to_async(aria2.client.unpause, new_gid)
        LOGGER.info(f'Start Queued Download from Aria2c: {name}. Gid: {gid}')

        async with queue_dict_lock:
            non_queued_dl.add(listener.uid)
