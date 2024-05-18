#!/usr/bin/env python3
from asyncio import Event, sleep
from time import time

from bot import (
    LOGGER,
    bot_cache,
    config_dict,
    non_queued_dl,
    non_queued_up,
    queue_dict_lock,
    queued_dl,
    queued_up,
    task_dict,
    user_data,
)
from bot.helper.ext_utils.bot_utils import (
    checking_access,
    get_readable_file_size,
    get_readable_time,
    get_telegraph_list,
    get_user_tasks,
    getdailytasks,
    sync_to_async,
)
from bot.helper.ext_utils.files_utils import check_storage_threshold, get_base_name
from bot.helper.ext_utils.links_utils import is_gdrive_id
from bot.helper.mirror_leech_utils.gdrive_utils.search import gdSearch
from bot.helper.tele_swi_helper.filters import CustomFilters
from bot.helper.tele_swi_helper.message_utils import check_botpm, forcesub
from bot.helper.themes import BotTheme


async def stop_duplicate_check(listener):
    if (
        isinstance(listener.upDest, int)
        or listener.isLeech
        or listener.select
        or not is_gdrive_id(listener.upDest)
        or (listener.upDest.startswith("mtp:") and listener.stopDuplicate)
        or not listener.stopDuplicate
        or listener.sameDir
    ):
        return False, None

    name = listener.name
    LOGGER.info(f"Checking File/Folder if already in Drive: {name}")
    if listener.compress:
        name = f"{name}.zip"
    elif listener.extract:
        try:
            name = get_base_name(name)
        except Exception:
            name = None
    if name is not None:
        telegraph_content, contents_no = await sync_to_async(
            gdSearch(stopDup=True, noMulti=listener.isClone).drive_list,
            name,
            listener.upDest,
            listener.userId,
        )
        if telegraph_content:
            msg = BotTheme("STOP_DUPLICATE", content=contents_no)
            button = await get_telegraph_list(telegraph_content)
            return msg, button

    return False, None


async def timeval_check(user_id):
    bot_cache.setdefault("time_interval", {})
    if (time_interval := bot_cache["time_interval"].get(user_id, False)) and (
        time() - time_interval
    ) < (UTI := config_dict["USER_TIME_INTERVAL"]):
        return UTI - (time() - time_interval)
    bot_cache["time_interval"][user_id] = time()
    return None


async def check_running_tasks(listener, state="dl"):
    all_limit = config_dict["QUEUE_ALL"]
    state_limit = (
        config_dict["QUEUE_DOWNLOAD"] if state == "dl" else config_dict["QUEUE_UPLOAD"]
    )
    event = None
    is_over_limit = False
    async with queue_dict_lock:
        if state == "up" and listener.mid in non_queued_dl:
            non_queued_dl.remove(listener.mid)
        if (
            (all_limit or state_limit)
            and not listener.forceRun
            and not (listener.forceUpload and state == "up")
            and not (listener.forceDownload and state == "dl")
        ):
            dl_count = len(non_queued_dl)
            up_count = len(non_queued_up)
            t_count = dl_count if state == "dl" else up_count
            is_over_limit = (
                all_limit
                and dl_count + up_count >= all_limit
                and (not state_limit or t_count >= state_limit)
            ) or (state_limit and t_count >= state_limit)
            if is_over_limit:
                event = Event()
                if state == "dl":
                    queued_dl[listener.mid] = event
                else:
                    queued_up[listener.mid] = event
        if not is_over_limit:
            if state == "up":
                non_queued_up.add(listener.mid)
            else:
                non_queued_dl.add(listener.mid)

    return is_over_limit, event


async def start_dl_from_queued(mid: int):
    queued_dl[mid].set()
    del queued_dl[mid]
    await sleep(0.7)


async def start_up_from_queued(mid: int):
    queued_up[mid].set()
    del queued_up[mid]
    await sleep(0.7)


async def start_from_queued():
    if all_limit := config_dict["QUEUE_ALL"]:
        dl_limit = config_dict["QUEUE_DOWNLOAD"]
        up_limit = config_dict["QUEUE_UPLOAD"]
        async with queue_dict_lock:
            dl = len(non_queued_dl)
            up = len(non_queued_up)
            all_ = dl + up
            if all_ < all_limit:
                f_tasks = all_limit - all_
                if queued_up and (not up_limit or up < up_limit):
                    for index, mid in enumerate(list(queued_up.keys()), start=1):
                        f_tasks = all_limit - all_
                        await start_up_from_queued(mid)
                        f_tasks -= 1
                        if f_tasks == 0 or (up_limit and index >= up_limit - up):
                            break
                if queued_dl and (not dl_limit or dl < dl_limit) and f_tasks != 0:
                    for index, mid in enumerate(list(queued_dl.keys()), start=1):
                        await start_dl_from_queued(mid)
                        if (dl_limit and index >= dl_limit - dl) or index == f_tasks:
                            break
        return

    if up_limit := config_dict["QUEUE_UPLOAD"]:
        async with queue_dict_lock:
            up = len(non_queued_up)
            if queued_up and up < up_limit:
                f_tasks = up_limit - up
                for index, mid in enumerate(list(queued_up.keys()), start=1):
                    await start_up_from_queued(mid)
                    if index == f_tasks:
                        break
    else:
        async with queue_dict_lock:
            if queued_up:
                for mid in list(queued_up.keys()):
                    await start_up_from_queued(mid)

    if dl_limit := config_dict["QUEUE_DOWNLOAD"]:
        async with queue_dict_lock:
            dl = len(non_queued_dl)
            if queued_dl and dl < dl_limit:
                f_tasks = dl_limit - dl
                for index, mid in enumerate(list(queued_dl.keys()), start=1):
                    await start_dl_from_queued(mid)
                    if index == f_tasks:
                        break
    else:
        async with queue_dict_lock:
            if queued_dl:
                for mid in list(queued_dl.keys()):
                    await start_dl_from_queued(mid)

# TODO fix isssues
async def limit_checker(
    size,
    listener,
    isTorrent=False,
    isMega=False,
    isDriveLink=False,
    isYtdlp=False,
    isPlayList=None,
):
    LOGGER.info("Checking Size Limit of link/file/folder/tasks...")
    user_id = listener.message.from_user.id
    if await CustomFilters.sudo("", listener.message):
        return
    limit_exceeded = ""
    if listener.isClone:
        if CLONE_LIMIT := config_dict["CLONE_LIMIT"]:
            limit = CLONE_LIMIT * 1024**3
            if size > limit:
                limit_exceeded = f"Clone limit is {get_readable_file_size(limit)}."
    elif isMega:
        if MEGA_LIMIT := config_dict["MEGA_LIMIT"]:
            limit = MEGA_LIMIT * 1024**3
            if size > limit:
                limit_exceeded = f"Mega limit is {get_readable_file_size(limit)}"
    elif isDriveLink:
        if GDRIVE_LIMIT := config_dict["GDRIVE_LIMIT"]:
            limit = GDRIVE_LIMIT * 1024**3
            if size > limit:
                limit_exceeded = (
                    f"Google drive limit is {get_readable_file_size(limit)}"
                )
    elif isYtdlp:
        if YTDLP_LIMIT := config_dict["YTDLP_LIMIT"]:
            limit = YTDLP_LIMIT * 1024**3
            if size > limit:
                limit_exceeded = f"Ytdlp limit is {get_readable_file_size(limit)}"
        if isPlayList != 0 and (PLAYLIST_LIMIT := config_dict["PLAYLIST_LIMIT"]):
            if isPlayList > PLAYLIST_LIMIT:
                limit_exceeded = f"Playlist limit is {PLAYLIST_LIMIT}"
    elif isTorrent:
        if TORRENT_LIMIT := config_dict["TORRENT_LIMIT"]:
            limit = TORRENT_LIMIT * 1024**3
            if size > limit:
                limit_exceeded = f"Torrent limit is {get_readable_file_size(limit)}"
    elif DIRECT_LIMIT := config_dict["DIRECT_LIMIT"]:
        limit = DIRECT_LIMIT * 1024**3
        if size > limit:
            limit_exceeded = f"Direct limit is {get_readable_file_size(limit)}"

    if not limit_exceeded:
        if (LEECH_LIMIT := config_dict["LEECH_LIMIT"]) and listener.isLeech:
            limit = LEECH_LIMIT * 1024**3
            if size > limit:
                limit_exceeded = f"Leech limit is {get_readable_file_size(limit)}"

        if (
            STORAGE_THRESHOLD := config_dict["STORAGE_THRESHOLD"]
        ) and not listener.isClone:
            arch = any([listener.compress, listener.extract])
            limit = STORAGE_THRESHOLD * 1024**3
            acpt = await sync_to_async(check_storage_threshold, size, limit, arch)
            if not acpt:
                limit_exceeded = (
                    f"You must leave {get_readable_file_size(limit)} free storage."
                )

        if config_dict["DAILY_TASK_LIMIT"] and config_dict[
            "DAILY_TASK_LIMIT"
        ] <= await getdailytasks(user_id):
            limit_exceeded = f"Daily Total Task Limit: {config_dict['DAILY_TASK_LIMIT']}\nYou have exhausted all your Daily Task Limits."
        else:
            ttask = await getdailytasks(user_id, increase_task=True)
            LOGGER.info(f"User: {user_id} | Daily Tasks: {ttask}")
        if (
            DAILY_MIRROR_LIMIT := config_dict["DAILY_MIRROR_LIMIT"]
        ) and not listener.isLeech:
            limit = DAILY_MIRROR_LIMIT * 1024**3
            if size >= (
                limit - await getdailytasks(user_id, check_mirror=True)
            ) or limit <= await getdailytasks(user_id, check_mirror=True):
                limit_exceeded = f"Daily Mirror Limit is {get_readable_file_size(limit)}\nYou have exhausted all your Daily Mirror Limit."
            elif not listener.isLeech:
                msize = await getdailytasks(user_id, upmirror=size, check_mirror=True)
                LOGGER.info(
                    f"User : {user_id} | Daily Mirror Size : {get_readable_file_size(msize)}"
                )
        if (DAILY_LEECH_LIMIT := config_dict["DAILY_LEECH_LIMIT"]) and listener.isLeech:
            limit = DAILY_LEECH_LIMIT * 1024**3
            if size >= (
                limit - await getdailytasks(user_id, check_leech=True)
            ) or limit <= await getdailytasks(user_id, check_leech=True):
                limit_exceeded = f"Daily Leech Limit is {get_readable_file_size(limit)}\nYou have exhausted all your Daily Leech Limit."
            elif listener.isLeech:
                lsize = await getdailytasks(user_id, upleech=size, check_leech=True)
                LOGGER.info(
                    f"User : {user_id} | Daily Leech Size : {get_readable_file_size(lsize)}"
                )
    if limit_exceeded:
        if size:
            return f"{limit_exceeded}.\nYour List/File/Folder size is {get_readable_file_size(size)}."
        elif isPlayList != 0:
            return f"{limit_exceeded}.\nYour playlist has {isPlayList} files."


async def task_utils(message):
    LOGGER.info("Running Task Manager ...")
    msg = []
    button = None
    if await CustomFilters.sudo("", message):
        return msg, button
    user_id = message.from_user.id
    token_msg, button = await checking_access(user_id, button)
    if token_msg is not None:
        msg.append(token_msg)
    if message.chat.type != message.chat.type.BOT:
        if ids := config_dict["FSUB_IDS"]:
            _msg, button = await forcesub(message, ids, button)
            if _msg:
                msg.append(_msg)
        user_dict = user_data.get(user_id, {})
        if config_dict["BOT_PM"] or user_dict.get("bot_pm") or config_dict["SAFE_MODE"]:
            _msg, button = await check_botpm(message, button)
            if _msg:
                msg.append(_msg)
    if (uti := config_dict["USER_TIME_INTERVAL"]) != 0 and (
        ut := await timeval_check(user_id)
    ):
        msg.append(
            f"Please Wait {get_readable_time(ut)}, Users have time interval Restrictions for {get_readable_time(uti)}."
        )
    if (bmax_tasks := config_dict["BOT_MAX_TASKS"]) and len(task_dict) >= bmax_tasks:
        msg.append(
            f"Bot Max Tasks limit exceeded.\nBot max tasks limit is {bmax_tasks}.\nPlease wait for the completion of other tasks."
        )
    if (maxtask := config_dict["USER_MAX_TASKS"]) and await get_user_tasks(
        message.from_user.id, maxtask
    ):
        msg.append(f"Your tasks limit exceeded for {maxtask} tasks")
    return msg, button
