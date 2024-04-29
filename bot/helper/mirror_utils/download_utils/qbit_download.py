#!/usr/bin/env python3
import asyncio
import time
from typing import Tuple

import aiofiles.os as aio_os
import httpx
from aiofiles import open as aioopen
from bot import download_dict, download_dict_lock, get_client, LOGGER, config_dict, non_queued_dl, queue_dict_lock
from bot.helper.mirror_utils.status_utils.qbit_status import QbittorrentStatus
from bot.helper.telegram_helper.message_utils import sendMessage, deleteMessage, sendStatusMessage
from bot.helper.ext_utils.bot_utils import bt_selection_buttons, sync_to_async
from bot.helper.ext_utils.task_manager import is_queued


async def add_qb_torrent(link: str, path: str, listener, ratio: float, seed_time: int) -> Tuple[bool, str]:
    client = await get_client()
    ADD_TIME = time()
    try:
        url = link
        tpath = None
        if await aio_os.path.exists(link):
            url = None
            tpath = link

        added_to_queue, event = await is_queued(listener.uid)

        async with httpx.AsyncClient() as client_:
            response = await client_.head(url, headers={'user-agent': 'Wget/1.12'})
            if response.status_code != 200:
                await sendMessage(listener.message, "This Torrent already added or unsupported/invalid link/file.")
                return

        op = await client.torrents_add(url, tpath, path, is_paused=added_to_queue, tags=f'{listener.uid}',
                                       ratio_limit=ratio, seeding_time_limit=seed_time)

        if op.lower() == "ok.":
            tor_info = await client.torrents_info(tag=f'{listener.uid}')
            if not tor_info:
                while True:
                    tor_info = await client.torrents_info(tag=f'{listener.uid}')
                    if tor_info:
                        break
                    elif time() - ADD_TIME >= 120:
                        msg = "Not added! Check if the link is valid or not. If it's torrent file then report, this happens if torrent file size above 10mb."
                        await sendMessage(listener.message, msg)
                        return
            tor_info = tor_info[0]
            ext_hash = tor_info.hash
        else:
            await sendMessage(listener.message, "This Torrent already added or unsupported/invalid link/file.")
            return

        async with download_dict_lock:
            download_dict[listener.uid] = QbittorrentStatus(
                listener, queued=added_to_queue)

        await onDownloadStart(f'{listener.uid}')

        if added_to_queue:
            LOGGER.info(
                f"Added to Queue/Download: {tor_info.name} - Hash: {ext_hash}")
        else:
            async with queue_dict_lock:
                non_queued_dl.add(listener.uid)
            LOGGER.info(
                f"QbitDownload started: {tor_info.name} - Hash: {ext_hash}")

        await listener.onDownloadStart()

        if config_dict['BASE_URL'] and listener.select:
            if link.startswith('magnet:'):
                metamsg = "Downloading Metadata, wait then you can select files. Use torrent file to avoid this wait."
                meta = await sendMessage(listener.message, metamsg)
                while True:
                    tor_info = await client.torrents_info(tag=f'{listener.uid}')
                    if not tor_info:
                        await deleteMessage(meta)
                        return
                    try:
                        tor_info = tor_info[0]
                        if tor_info.state not in ["metaDL", "checkingResumeData", "pausedDL"]:
                            await deleteMessage(meta)
                            break
                    except:
                        await deleteMessage(meta)
                        return

            ext_hash = tor_info.hash
            if not added_to_queue:
                await client.torrents_pause(torrent_hashes=ext_hash)
            SBUTTONS = bt_selection_buttons(ext_hash)
            msg = "Your download paused. Choose files then press Done Selecting button to start downloading."
            await sendMessage(listener.message, msg, SBUTTONS)
        else:
            await sendStatusMessage(listener.message)

        if added_to_queue:
            await event.wait()

            async with download_dict_lock:
                if listener.uid not in download_dict:
                    return
                download_dict[listener.uid].queued = False

            await client.torrents_resume(torrent_hashes=ext_hash)
            LOGGER.info(
                f'Start Queued Download from Qbittorrent: {tor_info.name} - Hash: {ext_hash}')

            async with queue_dict_lock:
                non_queued_dl.add(listener.uid)
    except Exception as e:
        await sendMessage(listener.message, str(e))
    finally:
        if await aio_os.path.exists(link):
            await aioopen(link, mode='w').close()

    return added_to_queue, ext_hash
