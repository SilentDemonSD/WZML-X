#!/usr/bin/env python3
import asyncio
from time import time
from typing import Any, Dict, Union

import aiohttp
from bot import download_dict, download_dict_lock, get_client, QbInterval, config_dict, QbTorrents, qb_listener_lock, LOGGER, bot_loop
from bot.helper.mirror_utils.status_utils.qbit_status import QbittorrentStatus
from bot.helper.telegram_helper.message_utils import update_all_messages
from bot.helper.ext_utils.bot_utils import get_readable_time, getDownloadByGid, new_task, sync_to_async
from bot.helper.ext_utils.fs_utils import clean_unwanted
from bot.helper.ext_utils.task_manager import limit_checker, stop_duplicate_check

async def remove_torrent(client: Any, hash_: str, tag: str) -> None:
    """Remove torrent from qBittorrent and update internal data structures."""
    await sync_to_async(client.torrents_delete, torrent_hashes=hash_, delete_files=True)
    async with qb_listener_lock:
        if tag in QbTorrents:
            del QbTorrents[tag]
    await sync_to_async(client.torrents_delete_tags, tags=tag)


async def on_download_error(err: str, tor: Any, button: Any = None) -> None:
    """Handle download errors and perform necessary actions."""
    LOGGER.info(f"Cancelling Download: {tor.name}")
    ext_hash = tor.hash
    download = await getDownloadByGid(ext_hash[:12])
    if hasattr(download, 'client'):
        listener = download.listener()
        client = download.client()
        await listener.onDownloadError(err, button)
        await sync_to_async(client.torrents_pause, torrent_hashes=ext_hash)
        await asyncio.sleep(0.3)
        await remove_torrent(client, ext_hash, tor.tags)


async def on_seed_finish(tor: Any) -> None:
    """Handle seed finish and perform necessary actions."""
    ext_hash = tor.hash
    LOGGER.info(f"Cancelling Seed: {tor.name}")
    download = await getDownloadByGid(ext_hash[:12])
    if hasattr(download, 'client'):
        listener = download.listener()
        client = download.client()
        msg = f"Seeding stopped with Ratio: {round(tor.ratio, 3)} and Time: {get_readable_time(tor.seeding_time)}"
        await listener.onUploadError(msg)
        await remove_torrent(client, ext_hash, tor.tags)


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
            await sync_to_async(client.torrents_pause, torrent_hashes=ext_hash)
        if listener.select:
            await clean_unwanted(listener.dir)
        await listener.onDownloadComplete()
        client = await sync_to_async(get_client)
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
            await sync_to_async(client.auth_log_out)
        else:
            await remove_torrent(client, ext_hash, tag)


async def qb_listener():
    """qBittorrent listener for various torrent states."""
    async with aiohttp.ClientSession() as session:
        client = await get_client(session)
        while True:
            async with qb_listener_lock:
                try:
                    if not QbTorrents:
                        break
                    torrents_info = await sync_to_async(client.torrents_info)
                    for tor_info in torrents_info:
                        tag = tor_info.tags
                        if tag not in QbTorrents:
                            continue
                        state = tor_info.state
                        if state == "metaDL":
                            TORRENT_TIMEOUT = config_dict.get('TORRENT_TIMEOUT')
                            if TORRENT_TIMEOUT and time() - tor_info.added_on >= TORRENT_TIMEOUT:
                                await on_download_error("Dead Torrent!", tor_info)
                            else:
                                await sync_to_async(client.torrents_reannounce, torrent_hashes=tor_info.hash)
                        elif state == "downloading":
                            if config_dict.get('STOP_DUPLICATE') and not QbTorrents[tag].get('stop_dup_check'):
                                QbTorrents[tag]['stop_dup_check'] = True
                                await stop_duplicate(tor_info)
                            if any(
                                    [
                                        config_dict.get('STORAGE_THRESHOLD'),
                                        config_dict.get('TORRENT_LIMIT'),
                                        config_dict.get('LEECH_LIMIT'),
                                        config_dict.get('DAILY_LEECH_LIMIT'),
                                        config_dict.get('DAILY_MIRROR_LIMIT'),
                                        config_dict.get('DAILY_TASK_LIMIT')
                                    ]
                            ) and not QbTorrents[tag].get('size_checked'):
                                QbTorrents[tag]['size_checked'] = True
                                await size_checked(tor_info)
                        elif state == "stalledDL":
                            TORRENT_TIMEOUT = config_dict.get('TORRENT_TIMEOUT')
                            if not QbTorrents[tag].get('rechecked') and 0.99989999999999999 < tor_info.progress < 1:
                                msg = f"Force recheck - Name: {tor_info.name} Hash: "
                                msg += f"{tor_info.hash} Downloaded Bytes: {tor_info.downloaded} "
                                msg += f"Size: {tor_info.size} Total Size: {tor_info.total_size}"
                                LOGGER.warning(msg)
                                await sync_to_async(client.torrents_recheck, torrent_hashes=tor_info.hash)
                                QbTorrents[tag]['rechecked'] = True
                            elif TORRENT_TIMEOUT and time() - QbTorrents[tag]['stalled_time'] >= TORRENT_TIMEOUT:
                                await on_download_error("Dead Torrent!", tor_info)
                            else:
                                await sync_to_async(client.torrents_reannounce, torrent_hashes=tor_info.hash)
                        elif state == "missingFiles":
                            await sync_to_async(client.torrents_recheck, torrent_hashes=tor_info.hash)
                        elif state == "error":
                            await on_download_error(
                                "No enough space for this torrent on device", tor_info)
                        elif tor_info.completion_on != 0 and not QbTorrents[tag].get('uploaded') and \
                                state not in ['checkingUP', 'checkingDL', 'checkingResumeData']:
                            QbTorrents[tag]['uploaded'] = True
                            await on_download_complete(tor_info)
                        elif state in ['pausedUP', 'pausedDL'] and QbTorrents[tag].get('seeding'):
                            QbTorrents[tag]['seeding'] = False
                            await on_seed_finish(tor_info)
                except Exception as e:
                    LOGGER.error(str(e))
                    client = await sync_to_async(get_client, session)
    QbInterval.clear()


async def on_download_start(tag: str) -> None:
    """Start listening for a specific tag."""
    async with qb_listener_lock:
        if tag not in QbTorrents:
            QbTorrents[tag] = {
                'stalled_time': time(),
                'stop_dup_check': False,
                'rechecked': False,
                'uploaded': False,
                'seeding': False,
                'size_checked': False
            }
        if not QbInterval:
            periodic = bot_loop.create_task(qb_listener())
            QbInterval.append(periodic)
