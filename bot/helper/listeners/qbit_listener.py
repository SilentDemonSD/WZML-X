#!/usr/bin/env python3
import asyncio
import aiohttp
import time
from typing import Any, Dict, Union

import logging as LOGGER
from bot.helper.mirror_utils.status_utils.qbit_status import QbittorrentStatus
from bot.helper.telegram_helper.message_utils import update_all_messages
from bot.helper.ext_utils.bot_utils import get_readable_time, getDownloadByGid
from bot.helper.ext_utils.fs_utils import clean_unwanted
from bot.helper.ext_utils.task_manager import limit_checker, stop_duplicate_check

async def remove_torrent(client: Any, hash_: str, tag: str) -> None:
    """Remove torrent from qBittorrent and update internal data structures."""
    await client.torrents_delete(hash_, delete_files=True)
    async with qb_listener_lock:
        if tag in QbTorrents:
            del QbTorrents[tag]
    await client.torrents_delete_tags(tags=tag)


async def on_download_error(err: str, tor: Any, button: Any = None) -> None:
    """Handle download errors and perform necessary actions."""
    LOGGER.info(f"Cancelling Download: {tor.name}")
    ext_hash = tor.hash
    download = await getDownloadByGid(ext_hash[:12])
    if hasattr(download, 'client'):
        listener = download.listener()
        await listener.onDownloadError(err, button)
        await client.torrents_pause(ext_hash)
        await asyncio.sleep(0.3)
        await remove_torrent(client, ext_hash, tor.tags)


async def on_seed_finish(tor: Any) -> None:
    """Handle seed finish and perform necessary actions."""
    ext_hash = tor.hash
    LOGGER.info(f"Cancelling Seed: {tor.name}")
    download = await getDownloadByGid(ext_hash[:12])
    if hasattr(download, 'listener'):
        listener = download.listener()
        msg = f"Seeding stopped with Ratio: {round(tor.ratio, 3)} and Time: {get_readable_time(tor.seeding_time)}"
        await listener.onUploadError(msg)
        await remove_torrent(download.client(), ext_hash, tor.tags)


async def stop_duplicate(tor: Any) -> None:
    """Stop duplicate torrents and perform necessary actions."""
    download = await getDownloadByGid(tor.hash[:12])
    if hasattr(download, 'listener'):
        listener = download.listener()
        name = tor.content_path.rsplit('/', 1)[-1].rsplit('.!qB', 1)[0]
        msg, button = await stop_duplicate_check(name, listener)
        if msg:
            await on_download_error(msg, tor, button)


async def size_checked(tor: Any) -> None:
    """Check if torrent size exceeds limits and perform necessary actions."""
    download = await getDownloadByGid(tor.hash[:12])
    if hasattr(download, 'listener'):
        listener = download.listener()
        size = tor.size
        if limit_exceeded := await limit_checker(size, listener, isTorrent=True):
            await on_download_error(limit_exceeded, tor)


async def on_download_complete(tor: Any) -> None:
    """Handle download completion and perform necessary actions."""
    ext_hash = tor.hash
    tag = tor.tags
    await asyncio.sleep(2)
    download = await getDownloadByGid(ext_hash[:12])
    if hasattr(download, 'client'):
        listener = download.listener()
        client = download.client()
        if not listener.seed:
            await client.torrents_pause(ext_hash)
        if listener.select:
            await clean_unwanted(listener.dir)
        await listener.onDownloadComplete()
        client = await get_client()
        if listener.seed:
            async with download_dict_lock:
                if listener.uid in download_dict:
                    removed = False
                    download_dict[listener.uid] = QbittorrentStatus(listener, True)
                else:
                    removed = True
            if removed:
                await remove_torrent(client, ext_hash, tag)
                return
            async with qb_listener_lock:
                if tag in QbTorrents:
                    QbTorrents[tag]['seeding'] = True
                else:
                    return
            await update_all_messages()
            LOGGER.info(f"Seeding started: {tor.name} - Hash: {ext_hash}")
            await client.auth_log_out()
        else:
            await remove_torrent(client, ext_hash, tag)


async def qb_listener():
    """qBittorrent listener for various torrent states."""
    async with aiohttp.ClientSession() as session:
        try:
            client = await get_client(session)
            tasks = [
                asyncio.create_task(size_checked(tor_info)),
                asyncio.create_task(stop_duplicate(tor_info)),
                asyncio.create_task(on_download_error("Dead Torrent!", tor_info))
                if TORRENT_TIMEOUT and time() - tor_info.added_on >= TORRENT_TIMEOUT else None,
                asyncio.create_task(sync_to_async(client.torrents_reannounce, torrent_hashes=tor_info.hash))
                if state == "metaDL" or state == "stalledDL" else None,
                asyncio.create_task(on_download_complete(tor_info))
                if tor_info.completion_on != 0 and state not in ['checkingUP', 'checkingDL', 'checkingResumeData'] else None,
                asyncio.create_task(on_seed_finish(tor_info))
                if state in ['pausedUP', 'pausedDL'] and QbTorrents[tag].get('seeding') else None,
            ]
            await asyncio.gather(*tasks)
        except Exception as e:
            LOGGER.error(str(e))
            client = await get_client(session)
    QbInterval.clear()


if __name__ == "__main__":
    bot_loop.run_until_complete(qb_listener())
