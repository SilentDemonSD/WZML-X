from asyncio import Event
from time import time

from ... import (
    LOGGER,
    bot_cache,
    non_queued_dl,
    non_queued_up,
    queue_dict_lock,
    queued_dl,
    queued_up,
    user_data,
)
from ...core.config_manager import Config
from ..mirror_leech_utils.gdrive_utils.search import GoogleDriveSearch
from ..telegram_helper.filters import CustomFilters
from ..telegram_helper.tg_utils import check_botpm, forcesub, verify_token
from .bot_utils import get_telegraph_list, sync_to_async
from .files_utils import get_base_name, check_storage_threshold
from .links_utils import is_gdrive_id
from .status_utils import get_readable_time, get_readable_file_size, get_specific_tasks


async def stop_duplicate_check(listener):
    if (
        isinstance(listener.up_dest, int)
        or listener.is_leech
        or listener.select
        or not is_gdrive_id(listener.up_dest)
        or (listener.up_dest.startswith("mtp:") and listener.stop_duplicate)
        or not listener.stop_duplicate
        or listener.same_dir
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
            GoogleDriveSearch(stop_dup=True, no_multi=listener.is_clone).drive_list,
            name,
            listener.up_dest,
            listener.user_id,
        )
        if telegraph_content:
            msg = f"File/Folder is already available in Drive.\nHere are {contents_no} list results:"
            button = await get_telegraph_list(telegraph_content)
            return msg, button

    return False, None


async def check_running_tasks(listener, state="dl"):
    all_limit = Config.QUEUE_ALL
    state_limit = Config.QUEUE_DOWNLOAD if state == "dl" else Config.QUEUE_UPLOAD
    event = None
    is_over_limit = False
    async with queue_dict_lock:
        if state == "up" and listener.mid in non_queued_dl:
            non_queued_dl.remove(listener.mid)
        if (
            (all_limit or state_limit)
            and not listener.force_run
            and not (listener.force_upload and state == "up")
            and not (listener.force_download and state == "dl")
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
    non_queued_dl.add(mid)


async def start_up_from_queued(mid: int):
    queued_up[mid].set()
    del queued_up[mid]
    non_queued_up.add(mid)


async def start_from_queued():
    if all_limit := Config.QUEUE_ALL:
        dl_limit = Config.QUEUE_DOWNLOAD
        up_limit = Config.QUEUE_UPLOAD
        async with queue_dict_lock:
            dl = len(non_queued_dl)
            up = len(non_queued_up)
            all_ = dl + up
            if all_ < all_limit:
                f_tasks = all_limit - all_
                if queued_up and (not up_limit or up < up_limit):
                    for index, mid in enumerate(list(queued_up.keys()), start=1):
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

    if up_limit := Config.QUEUE_UPLOAD:
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

    if dl_limit := Config.QUEUE_DOWNLOAD:
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


async def limit_checker(listener, yt_playlist=0):
    LOGGER.info("Checking Size Limit...")
    if await CustomFilters.sudo("", listener.message):
        LOGGER.info("SUDO User. Skipping Size Limit...")
        return

    user_id, size = listener.user_id, listener.size

    async def recurr_limits(limits):
        nonlocal yt_playlist, size
        limit_exceeded = ""
        for condition, attr, name in limits:
            if condition and (limit := getattr(Config, attr, 0)):
                if attr == "PLAYLIST_LIMIT":
                    if yt_playlist >= limit:
                        limit_exceeded = f"┠ <b>{name} Limit Count</b> → {limit}"
                else:
                    byte_limit = limit * 1024**3
                    if size >= byte_limit:
                        limit_exceeded = f"┠ <b>{name} Limit</b> → {get_readable_file_size(byte_limit)}"

                LOGGER.info(
                    f"{name} Limit Breached: {listener.name} & Size: {get_readable_file_size(size)}"
                )
                break
        return limit_exceeded

    limits = [
        (listener.is_torrent or listener.is_qbit, "TORRENT_LIMIT", "Torrent"),
        (listener.is_mega, "MEGA_LIMIT", "Mega"),
        (listener.is_gdrive, "GD_DL_LIMIT", "GDriveDL"),
        (listener.is_clone, "CLONE_LIMIT", "Clone"),
        (listener.is_jd, "JD_LIMIT", "JDownloader"),
        (listener.is_nzb, "NZB_LIMIT", "SABnzbd"),
        (listener.is_rclone, "RC_DL_LIMIT", "RCloneDL"),
        (listener.is_ytdlp, "YTDLP_LIMIT", "YT-DLP"),
        (bool(yt_playlist), "PLAYLIST_LIMIT", "Playlist"),
        (True, "DIRECT_LIMIT", "Direct"),
    ]
    limit_exceeded = await recurr_limits(limits)

    if not limit_exceeded:
        extra_limits = [
            (listener.is_leech, "LEECH_LIMIT", "Leech"),
            (listener.compress, "ARCHIVE_LIMIT", "Archive"),
            (listener.extract, "EXTRACT_LIMIT", "Extract"),
        ]
        limit_exceeded = await recurr_limits(extra_limits)

        if Config.STORAGE_LIMIT and not listener.is_clone:
            limit = Config.STORAGE_LIMIT * 1024**3
            if not await check_storage_threshold(
                size, limit, any([listener.compress, listener.extract])
            ):
                limit_exceeded = f"┠ <b>Threshold Storage Limit</b> → {get_readable_file_size(limit)}"

    if limit_exceeded:
        return limit_exceeded + f"\n┖ <b>Task By</b> → {listener.tag}"


"""
class UsageChecks: # TODO: Dynamic Check for All Task

class DailyUsageChecks:
"""


async def user_interval_check(user_id):
    bot_cache.setdefault("time_interval", {})
    if (time_interval := bot_cache["time_interval"].get(user_id, False)) and (
        time() - time_interval
    ) < (UTI := Config.USER_TIME_INTERVAL):
        return UTI - (time() - time_interval)
    bot_cache["time_interval"][user_id] = time()
    return None


async def pre_task_check(message):
    LOGGER.info("Running Pre Task Checks ...")
    msg = []
    button = None
    if await CustomFilters.sudo("", message):
        return msg, button
    user_id = (message.from_user or message.sender_chat).id
    if Config.RSS_CHAT and user_id == int(Config.RSS_CHAT):
        return msg, button
    if message.chat.type != message.chat.type.BOT:
        if ids := Config.FORCE_SUB_IDS:
            _msg, button = await forcesub(message, ids, button)
            if _msg:
                msg.append(_msg)
        user_dict = user_data.get(user_id, {})
        if Config.BOT_PM or user_dict.get("BOT_PM"):  # or config_dict['SAFE_MODE']:
            _msg, button = await check_botpm(message, button)
            if _msg:
                msg.append(_msg)
    if (uti := Config.USER_TIME_INTERVAL) and (
        ut := await user_interval_check(user_id)
    ):
        msg.append(
            f"┠ <b>Waiting Time</b> → {get_readable_time(ut)}\n┠ <i>User's Time Interval Restrictions</i> → {get_readable_time(uti)}"
        )
    if (bmax_tasks := Config.BOT_MAX_TASKS) and len(
        await get_specific_tasks("All", False)
    ) >= int(bmax_tasks):
        msg.append(
            f"┠ Max Concurrent Bot's Tasks Limit exceeded.\n┠ Bot Tasks Limit : {bmax_tasks} task"
        )
    if (maxtask := Config.USER_MAX_TASKS) and len(
        await get_specific_tasks("All", user_id)
    ) >= int(maxtask):
        msg.append(
            f"┠ Max Concurrent User's Task(s) Limit exceeded! \n┠ User Task Limit : {maxtask} tasks"
        )

    token_msg, button = await verify_token(user_id, button)
    if token_msg is not None:
        msg.append(token_msg)

    if msg:
        username = message.from_user.mention
        final_msg = f"⌬ <b>Task Checks :</b>\n│\n┟ <b>Name</b> → {username}\n┃\n"
        for i, m_part in enumerate(msg, 1):
            final_msg += f"{m_part}\n"
        if button is not None:
            button = button.build_menu(2)
        return final_msg, button

    return None, None
