#!/usr/bin/env python3
import contextlib
from asyncio import sleep
from time import time

from aiofiles.os import path as aiopath
from aiofiles.os import remove as aioremove

from bot import LOGGER, Intervals, aria2, config_dict, task_dict, task_dict_lock
from bot.helper.ext_utils.bot_utils import (
    bt_selection_buttons,
    getTaskByGid,
    new_thread,
    sync_to_async,
)
from bot.helper.ext_utils.files_utils import clean_unwanted
from bot.helper.ext_utils.task_manager import limit_checker, stop_duplicate_check
from bot.helper.mirror_leech_utils.status_utils.aria2_status import Aria2Status
from bot.helper.tele_swi_helper.message_utils import (
    deleteMessage,
    sendMessage,
    update_status_message,
)


@new_thread
async def _onDownloadStarted(api, gid):
    download = await sync_to_async(api.get_download, gid)
    if download.options.follow_torrent == "false":
        return
    if download.is_metadata:
        LOGGER.info(f"onDownloadStarted: {gid} METADATA")
        await sleep(1)
        if task := await getTaskByGid(gid):
            task.listener.isTorrent = True
            if task.listener.select:
                metamsg = "Downloading Metadata, wait then you can select files. Use torrent file to avoid this wait."
                meta = await sendMessage(task.listener.message, metamsg)
                while 1:
                    await sleep(0.5)
                    if download.is_removed or download.followed_by_ids:
                        await deleteMessage(meta)
                        break
                    download = download.live
        return
    else:
        LOGGER.info(f"onDownloadStarted: {download.name} - Gid: {gid}")
        await sleep(1)

    if (task := await getTaskByGid(gid)) and any(
        [
            config_dict["DIRECT_LIMIT"],
            config_dict["TORRENT_LIMIT"],
            config_dict["LEECH_LIMIT"],
            config_dict["STORAGE_THRESHOLD"],
            config_dict["DAILY_TASK_LIMIT"],
            config_dict["DAILY_MIRROR_LIMIT"],
            config_dict["DAILY_LEECH_LIMIT"],
        ]
    ):
        download = await sync_to_async(api.get_download, gid)
        await sleep(2)
        download = download.live

        size = download.total_length
        LOGGER.info(f"Task Size : {size}")
        if limit_exceeded := await limit_checker(size, task.listener):
            await task.listener.onDownloadError(limit_exceeded)
            await sync_to_async(api.remove, [download], force=True, files=True)
            return

        task.listener.name = download.name
        msg, button = await stop_duplicate_check(task.listener)
        if msg:
            await task.listener.onDownloadError(msg, button)
            await sync_to_async(api.remove, [download], force=True, files=True)
            return


@new_thread
async def _onDownloadComplete(api, gid):
    try:
        download = await sync_to_async(api.get_download, gid)
    except Exception:
        return
    if download.options.follow_torrent == "false":
        return
    if download.followed_by_ids:
        new_gid = download.followed_by_ids[0]
        LOGGER.info(f"Gid changed from {gid} to {new_gid}")
        if task := await getTaskByGid(new_gid):
            task.listener.isTorrent = True
            if config_dict["BASE_URL"] and task.listener.select:
                if not task.queued:
                    await sync_to_async(api.client.force_pause, new_gid)
                SBUTTONS = bt_selection_buttons(new_gid)
                msg = "Your download paused. Choose files then press Done Selecting button to start downloading."
                await sendMessage(task.listener.message, msg, SBUTTONS)
    elif download.is_torrent:
        if task := await getTaskByGid(gid):
            task.listener.isTorrent = True
            if hasattr(task, "seeding") and task.seeding:
                LOGGER.info(f"Cancelling Seed: {download.name} onDownloadComplete")
                await task.listener.onUploadError(
                    f"Seeding stopped with Ratio: {task.ratio()} and Time: {task.seeding_time()}"
                )
                await sync_to_async(api.remove, [download], force=True, files=True)
    else:
        LOGGER.info(f"onDownloadComplete: {download.name} - Gid: {gid}")
        if task := await getTaskByGid(gid):
            await task.listener.onDownloadComplete()
            if Intervals["stopAll"]:
                return
            await sync_to_async(api.remove, [download], force=True, files=True)


@new_thread
async def _onBtDownloadComplete(api, gid):
    seed_start_time = time()
    await sleep(1)
    download = await sync_to_async(api.get_download, gid)
    # if download.options.follow_torrent == "false":
    #    return
    LOGGER.info(f"onBtDownloadComplete: {download.name} - Gid: {gid}")
    if task := await getTaskByGid(gid):
        task.listener.isTorrent = True
        if task.listener.select:
            res = download.files
            for file_o in res:
                f_path = file_o.path
                if not file_o.selected and await aiopath.exists(f_path):
                    with contextlib.suppress(Exception):
                        await aioremove(f_path)
            await clean_unwanted(download.dir)
        if task.listener.seed:
            try:
                await sync_to_async(
                    api.set_options, {"max-upload-limit": "0"}, [download]
                )
            except Exception as e:
                LOGGER.error(
                    f"{e} You are not able to seed because you added global option seed-time=0 without adding specific seed_time for this torrent GID: {gid}"
                )
        else:
            try:
                await sync_to_async(api.client.force_pause, gid)
            except Exception as e:
                LOGGER.error(f"{e} GID: {gid}")
        await task.listener.onDownloadComplete()
        download = download.live
        if (
            task.listener.seed
            and download.is_complete
            and (task := await getTaskByGid(gid))
        ):
            LOGGER.info(f"Cancelling Seed: {download.name}")
            await task.listener.onUploadError(
                f"Seeding stopped with Ratio: {task.ratio()} and Time: {task.seeding_time()}"
            )
            await sync_to_async(api.remove, [download], force=True, files=True)
        elif (
            task.listener.seed
            and download.is_complete
            and not (task := await getTaskByGid(gid))
        ):
            pass
        elif task.listener.seed and not task.listener.isCancelled:
            async with task_dict_lock:
                if task.listener.mid not in task_dict:
                    await sync_to_async(api.remove, [download], force=True, files=True)
                    return
                task_dict[task.listener.mid] = Aria2Status(task.listener, gid, True)
                task_dict[task.listener.mid].start_time = seed_start_time
            LOGGER.info(f"Seeding started: {download.name} - Gid: {gid}")
            await update_status_message(task.listener.message.chat.id)
        else:
            await sync_to_async(api.remove, [download], force=True, files=True)


@new_thread
async def _onDownloadStopped(api, gid):
    await sleep(4)
    if task := await getTaskByGid(gid):
        await task.listener.onDownloadError("Dead torrent!")


@new_thread
async def _onDownloadError(api, gid):
    LOGGER.info(f"onDownloadError: {gid}")
    error = "None"
    with contextlib.suppress(Exception):
        download = await sync_to_async(api.get_download, gid)
        if download.options.follow_torrent == "false":
            return
        error = download.error_message
        LOGGER.info(f"Download Error: {error}")
    if task := await getTaskByGid(gid):
        await task.listener.onDownloadError(error)


def start_aria2_listener():
    aria2.listen_to_notifications(
        threaded=False,
        on_download_start=_onDownloadStarted,
        on_download_error=_onDownloadError,
        on_download_stop=_onDownloadStopped,
        on_download_complete=_onDownloadComplete,
        on_bt_download_complete=_onBtDownloadComplete,
        timeout=60,
    )
