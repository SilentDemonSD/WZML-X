#!/usr/bin/env python3
from typing import Any, AsyncContextManager, Dict, Optional

import asyncio
from time import time

from bot import download_dict, download_dict_lock, get_client, QbInterval, config_dict, QbTorrents, qb_listener_lock, LOGGER, bot_loop
from bot.helper.mirror_utils.status_utils.qbit_status import QbittorrentStatus
from bot.helper.telegram_helper.message_utils import update_all_messages
from bot.helper.ext_utils.bot_utils import get_readable_time, getDownloadByGid, new_task, sync_to_async
from bot.helper.ext_utils.fs_utils import clean_unwanted
from bot.helper.ext_utils.task_manager import limit_checker, stop_duplicate_check


async def __remove_torrent(client: Any, hash_: str, tag: str) -> None:
    try:
        await sync_to_async(client.torrents_delete, torrent_hashes=hash_, delete_files=True)
    except Exception as e:  # noqa
        LOGGER.error(f"Error deleting torrent {hash_}: {e}")

    async with qb_listener_lock:
        if tag in QbTorrents:
            del QbTorrents[tag]

    try:
        await sync_to_async(client.torrents_delete_tags, tags=tag)
    except Exception as e:  # noqa
        LOGGER.error(f"Error deleting tag {tag}: {e}")


@new_task
async def __onDownloadError(err: str, tor: Any, button: Optional[Any] = None) -> None:
    LOGGER.info(f"Cancelling Download: {tor.name}")
    ext_hash = tor.hash
    download = await getDownloadByGid(ext_hash[:12])

    if not hasattr(download, "client"):
        return

    listener = download.listener()
    client = download.client()

    try:
        await listener.onDownloadError(err, button)
    except Exception as e:  # noqa
        LOGGER.error(f"Error in onDownloadError: {e}")

    try:
        await sync_to_async(client.torrents_pause, torrent_hashes=ext_hash)
    except Exception as e:  # noqa
        LOGGER.error(f"Error pausing torrent {ext_hash}: {e}")

    await asyncio.sleep(0.3)
    await __remove_torrent(client, ext_hash, tor.tags)


@new_task
async def __onSeedFinish(tor: Any) -> None:
    ext_hash = tor.hash
    LOGGER.info(f"Cancelling Seed: {tor.name}")
    download = await getDownloadByGid(ext_hash[:12])

    if not hasattr(download, "client"):
        return

    listener = download.listener()
    client = download.client()

    try:
        msg = f"Seeding stopped with Ratio: {round(tor.ratio, 3)} and Time: {get_readable_time(tor.seeding_time)}"
        await listener.onUploadError(msg)
    except Exception as e:  # noqa
        LOGGER.error(f"Error in onUploadError: {e}")

    await __remove_torrent(client, ext_hash, tor.tags)


@new_task
async def __stop_duplicate(tor: Any) -> None:
    download = await getDownloadByGid(tor.hash[:12])

    if not hasattr(download, "listener"):
        return

    listener = download.listener()
    name = tor.content_path.rsplit("/", 1)[-1].rsplit(".!qB", 1)[0]

    try:
        msg, button = await stop_duplicate_check(name, listener)
    except Exception as e:  # noqa
        LOGGER.error(f"Error in stop_duplicate_check: {e}")
        return

    if msg:
        await __onDownloadError(msg, tor, button)


@new_task
async def __size_checked(tor: Any) -> None:
    download = await getDownloadByGid(tor.hash[:12])

    if hasattr(download, "listener"):
        listener = download.listener()
        size = tor.size

        try:
            limit_exceeded = await limit_checker(size, listener, True)
        except Exception as e:  # noqa
            LOGGER.error(f"Error in limit_checker: {e}")
            return

        if limit_exceeded:
            await __onDownloadError(limit_exceeded, tor)


@new_task
async def __onDownloadComplete(tor: Any) -> None:
    ext_hash = tor.hash
    tag = tor.tags

    await asyncio.sleep(2)
    download = await getDownloadByGid(ext_hash[:12])

    if not hasattr(download, "client"):
        return

    listener = download.listener()
    client = download.client()

    if not hasattr(listener, "seed"):
        try:
            await sync_to_async(client.torrents_pause, torrent_hashes=ext_hash)
        except Exception as e:  # noqa
            LOGGER.error(f"Error pausing torrent {ext_hash}: {e}")

    if hasattr(listener, "select"):
        try:
            await clean_unwanted(listener.dir)
        except Exception as e:  # noqa
            LOGGER.error(f"Error cleaning unwanted files: {e}")

    try:
        await listener.onDownloadComplete()
    except Exception as e:  # noqa
        LOGGER.error(f"Error in onDownloadComplete: {e}")

    try:
        client = await sync_to_async(get_client)
    except Exception as e:  # noqa
        LOGGER.error(f"Error getting client: {e}")
        return

    if hasattr(listener, "seed"):
        try:
            async with download_dict_lock:
                if listener.uid in download_dict:
                    removed = False
                    download_dict[listener.uid] = QbittorrentStatus(listener, True)
                else:
                    removed = True
        except Exception as e:  # noqa
            LOGGER.error(f"Error updating download dict: {e}")
            return

        if removed:
            try:
                await __remove_torrent(client, ext_hash, tag)
            except Exception as e:  # noqa
                LOGGER.error(f"Error removing torrent {ext_hash}: {e}")
                return

        try:
            async with qb_listener_lock:
                if tag in QbTorrents:
                    QbTorrents[tag]["seeding"] = True
                else:
                    return
        except Exception as e:  # noqa
            LOGGER.error(f"Error updating QbTorrents: {e}")
            return

        try:
            await update_all_messages()
        except Exception as e:  # noqa
            LOGGER.error(f"Error updating all messages: {e}")
            return

        LOGGER.info(f"Seeding started: {tor.name} - Hash: {ext_hash}")

        try:
            await sync_to_async(client.auth_log_out)
        except Exception as e:  # noqa
            LOGGER.error(f"Error logging out client: {e}")
            return

    else:
        try:
            await __remove_torrent(client, ext_hash, tag)
        except Exception as e:  # noqa
            LOGGER.error(f"Error removing torrent {ext_hash}: {e}")
            return


async def __qb_listener() -> None:
    try:
        client = await sync_to_async(get_client)
    except Exception as e:  # noqa
        LOGGER.error(f"Error getting client: {e}")
        return

    while True:
        try:
            async with qb_listener_lock:
                if not QbTorrents:
                    break

                for tor_info in await sync_to_async(client.torrents_info):
                    tag = tor_info.tags

                    if tag not in QbTorrents:
                        continue

                    state = tor_info.state

                    if state == "metaDL":
                        TORRENT_TIMEOUT = config_dict.get("TORRENT_TIMEOUT")

                        if TORRENT_TIMEOUT and time() - tor_info.added_on >= TORRENT_TIMEOUT:
                            try:
                                await __onDownloadError("Dead Torrent!", tor_info)
                            except Exception as e:  # noqa
                                LOGGER.error(f"Error in onDownloadError: {e}")

                        else:
                            try:
                                await sync_to_async(client.torrents_reannounce, torrent_hashes=tor_info.hash)
                            except Exception as e:  # noqa
                                LOGGER.error(f"Error reannouncing torrent {tor_info.hash}: {e}")

                    elif state == "downloading":
                        try:
                            QbTorrents[tag]["stalled_time"] = time()
                        except Exception as e:  # noqa
                            LOGGER.error(f"Error updating stalled time: {e}")

                        if config_dict.get("STOP_DUPLICATE") and not QbTorrents[tag].get("stop_dup_check"):
                            QbTorrents[tag]["stop_dup_check"] = True
                            __stop_duplicate(tor_info)

                        if any(
                            [
                                config_dict.get("STORAGE_THRESHOLD"),
                                config_dict.get("TORRENT_LIMIT"),
                                config_dict.get("LEECH_LIMIT"),
                            ]
                        ) and not QbTorrents[tag].get("size_checked"):
                            QbTorrents[tag]["size_checked"] = True
                            __size_checked(tor_info)

                    elif state == "stalledDL":
                        TORRENT_TIMEOUT = config_dict.get("TORRENT_TIMEOUT")

                        if not QbTorrents[tag].get("rechecked") and 0.99989999999999999 < tor_info.progress < 1:
                            msg = f"Force recheck - Name: {tor_info.name} Hash: "
                            msg += f"{tor_info.hash} Downloaded Bytes: {tor_info.downloaded} "
                            msg += f"Size: {tor_info.size} Total Size: {tor_info.total_size}"
                            LOGGER.warning(msg)

                            try:
                                await sync_to_async(client.torrents_recheck, torrent_hashes=tor_info.hash)
                            except Exception as e:  # noqa
                                LOGGER.error(f"Error rechecking torrent {tor_info.hash}: {e}")

                            QbTorrents[tag]["rechecked"] = True

                        elif TORRENT_TIMEOUT
