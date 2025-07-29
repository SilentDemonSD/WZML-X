from asyncio import gather, iscoroutinefunction
from html import escape
from re import findall
from time import time

from psutil import cpu_percent, disk_usage, virtual_memory

from ... import (
    DOWNLOAD_DIR,
    bot_cache,
    bot_start_time,
    status_dict,
    task_dict,
    task_dict_lock,
)
from ...core.config_manager import Config
from ..telegram_helper.button_build import ButtonMaker

SIZE_UNITS = ["B", "KB", "MB", "GB", "TB", "PB"]


class MirrorStatus:
    STATUS_UPLOAD = "Upload"
    STATUS_DOWNLOAD = "Download"
    STATUS_CLONE = "Clone"
    STATUS_QUEUEDL = "QueueDl"
    STATUS_QUEUEUP = "QueueUp"
    STATUS_PAUSED = "Pause"
    STATUS_ARCHIVE = "Archive"
    STATUS_EXTRACT = "Extract"
    STATUS_SPLIT = "Split"
    STATUS_CHECK = "CheckUp"
    STATUS_SEED = "Seed"
    STATUS_SAMVID = "SamVid"
    STATUS_CONVERT = "Convert"
    STATUS_FFMPEG = "FFmpeg"
    STATUS_YT = "YouTube"
    STATUS_METADATA = "Metadata"


class EngineStatus:
    def __init__(self):
        self.STATUS_ARIA2 = f"Aria2 v{bot_cache['eng_versions']['aria2']}"
        self.STATUS_AIOHTTP = f"AioHttp v{bot_cache['eng_versions']['aiohttp']}"
        self.STATUS_GDAPI = f"Google-API v{bot_cache['eng_versions']['gapi']}"
        self.STATUS_QBIT = f"qBit v{bot_cache['eng_versions']['qBittorrent']}"
        self.STATUS_TGRAM = f"Pyro v{bot_cache['eng_versions']['pyrofork']}"
        self.STATUS_MEGA = f"MegaAPI v{bot_cache['eng_versions']['mega']}"
        self.STATUS_YTDLP = f"yt-dlp v{bot_cache['eng_versions']['yt-dlp']}"
        self.STATUS_FFMPEG = f"ffmpeg v{bot_cache['eng_versions']['ffmpeg']}"
        self.STATUS_7Z = f"7z v{bot_cache['eng_versions']['7z']}"
        self.STATUS_RCLONE = f"RClone v{bot_cache['eng_versions']['rclone']}"
        self.STATUS_SABNZBD = f"SABnzbd+ v{bot_cache['eng_versions']['SABnzbd+']}"
        self.STATUS_QUEUE = "QSystem v2"
        self.STATUS_JD = "JDownloader v2"
        self.STATUS_YT = "Youtube-Api"
        self.STATUS_METADATA = "Metadata"


STATUSES = {
    "ALL": "All",
    "DL": MirrorStatus.STATUS_DOWNLOAD,
    "UP": MirrorStatus.STATUS_UPLOAD,
    "QD": MirrorStatus.STATUS_QUEUEDL,
    "QU": MirrorStatus.STATUS_QUEUEUP,
    "AR": MirrorStatus.STATUS_ARCHIVE,
    "EX": MirrorStatus.STATUS_EXTRACT,
    "SD": MirrorStatus.STATUS_SEED,
    "CL": MirrorStatus.STATUS_CLONE,
    "CM": MirrorStatus.STATUS_CONVERT,
    "SP": MirrorStatus.STATUS_SPLIT,
    "SV": MirrorStatus.STATUS_SAMVID,
    "FF": MirrorStatus.STATUS_FFMPEG,
    "PA": MirrorStatus.STATUS_PAUSED,
    "CK": MirrorStatus.STATUS_CHECK,
}


async def get_task_by_gid(gid: str):
    async with task_dict_lock:
        for tk in task_dict.values():
            if hasattr(tk, "seeding"):
                await tk.update()
            if tk.gid() == gid:
                return tk
        return None


async def get_specific_tasks(status, user_id):
    if status == "All":
        if user_id:
            return [tk for tk in task_dict.values() if tk.listener.user_id == user_id]
        else:
            return list(task_dict.values())
    tasks_to_check = (
        [tk for tk in task_dict.values() if tk.listener.user_id == user_id]
        if user_id
        else list(task_dict.values())
    )
    coro_tasks = []
    coro_tasks.extend(tk for tk in tasks_to_check if iscoroutinefunction(tk.status))
    coro_statuses = await gather(*[tk.status() for tk in coro_tasks])
    result = []
    coro_index = 0
    for tk in tasks_to_check:
        if tk in coro_tasks:
            st = coro_statuses[coro_index]
            coro_index += 1
        else:
            st = tk.status()
        if (st == status) or (
            status == MirrorStatus.STATUS_DOWNLOAD and st not in STATUSES.values()
        ):
            result.append(tk)
    return result


async def get_all_tasks(req_status: str, user_id):
    async with task_dict_lock:
        return await get_specific_tasks(req_status, user_id)


def get_raw_file_size(size):
    num, unit = size.split()
    return int(float(num) * (1024 ** SIZE_UNITS.index(unit)))


def get_readable_file_size(size_in_bytes):
    if not size_in_bytes:
        return "0B"

    index = 0
    while size_in_bytes >= 1024 and index < len(SIZE_UNITS) - 1:
        size_in_bytes /= 1024
        index += 1

    return f"{size_in_bytes:.2f}{SIZE_UNITS[index]}"


def get_readable_time(seconds: int):
    periods = [("d", 86400), ("h", 3600), ("m", 60), ("s", 1)]
    result = ""
    for period_name, period_seconds in periods:
        if seconds >= period_seconds:
            period_value, seconds = divmod(seconds, period_seconds)
            result += f"{int(period_value)}{period_name}"
    return result


def get_raw_time(time_str: str) -> int:
    time_units = {"d": 86400, "h": 3600, "m": 60, "s": 1}
    return sum(
        int(value) * time_units[unit]
        for value, unit in findall(r"(\d+)([dhms])", time_str)
    )


def time_to_seconds(time_duration):
    try:
        parts = time_duration.split(":")
        if len(parts) == 3:
            hours, minutes, seconds = map(float, parts)
        elif len(parts) == 2:
            hours = 0
            minutes, seconds = map(float, parts)
        elif len(parts) == 1:
            hours = 0
            minutes = 0
            seconds = float(parts[0])
        else:
            return 0
        return hours * 3600 + minutes * 60 + seconds
    except Exception:
        return 0


def speed_string_to_bytes(size_text: str):
    size = 0
    size_text = size_text.lower()
    if "k" in size_text:
        size += float(size_text.split("k")[0]) * 1024
    elif "m" in size_text:
        size += float(size_text.split("m")[0]) * 1048576
    elif "g" in size_text:
        size += float(size_text.split("g")[0]) * 1073741824
    elif "t" in size_text:
        size += float(size_text.split("t")[0]) * 1099511627776
    elif "b" in size_text:
        size += float(size_text.split("b")[0])
    return size


def get_progress_bar_string(pct):
    pct = float(str(pct).strip("%"))
    p = min(max(pct, 0), 100)
    cFull = int(p // 8)
    p_str = "⬢" * cFull
    p_str += "⬡" * (12 - cFull)
    return f"[{p_str}]"


async def get_readable_message(sid, is_user, page_no=1, status="All", page_step=1):
    msg = ""
    button = None

    tasks = await get_specific_tasks(status, sid if is_user else None)

    STATUS_LIMIT = Config.STATUS_LIMIT
    tasks_no = len(tasks)
    pages = (max(tasks_no, 1) + STATUS_LIMIT - 1) // STATUS_LIMIT
    if page_no > pages:
        page_no = (page_no - 1) % pages + 1
        status_dict[sid]["page_no"] = page_no
    elif page_no < 1:
        page_no = pages - (abs(page_no) % pages)
        status_dict[sid]["page_no"] = page_no
    start_position = (page_no - 1) * STATUS_LIMIT

    for index, task in enumerate(
        tasks[start_position : STATUS_LIMIT + start_position], start=1
    ):
        if status != "All":
            tstatus = status
        elif iscoroutinefunction(task.status):
            tstatus = await task.status()
        else:
            tstatus = task.status()
        msg += f"<b>{index + start_position}.</b> "
        msg += f"<b><i>{escape(f'{task.name()}')}</i></b>"
        if task.listener.subname:
            msg += f"\n┖ <b>Sub Name</b> → <i>{task.listener.subname}</i>"
        elapsed = time() - task.listener.message.date.timestamp()

        msg += f"\n\n<b>Task By {task.listener.message.from_user.mention(style='html')} </b> ( #ID{task.listener.message.from_user.id} )"
        if task.listener.is_super_chat:
            msg += f" <i>[<a href='{task.listener.message.link}'>Link</a>]</i>"

        if (
            tstatus not in [MirrorStatus.STATUS_SEED, MirrorStatus.STATUS_QUEUEUP]
            and task.listener.progress
        ):
            progress = task.progress()
            msg += f"\n┟ {get_progress_bar_string(progress)} <i>{progress}</i>"
            if task.listener.subname:
                subsize = f" / {get_readable_file_size(task.listener.subsize)}"
                ac = len(task.listener.files_to_proceed)
                count = f"( {task.listener.proceed_count} / {ac or '?'} )"
            else:
                subsize = ""
                count = ""
            msg += f"\n┠ <b>Processed</b> → <i>{task.processed_bytes()}{subsize} of {task.size()}</i>"
            if count:
                msg += f"\n┠ <b>Count:</b> → <b>{count}</b>"
            msg += f"\n┠ <b>Status</b> → <b>{tstatus}</b>"
            msg += f"\n┠ <b>Speed</b> → <i>{task.speed()}</i>"
            msg += f"\n┠ <b>Time</b> → <i>{task.eta()} of {get_readable_time(elapsed + get_raw_time(task.eta()))} ( {get_readable_time(elapsed)} )</i>"
            if tstatus == MirrorStatus.STATUS_DOWNLOAD and (
                task.listener.is_torrent or task.listener.is_qbit
            ):
                try:
                    msg += f"\n┠ <b>Seeders</b> → {task.seeders_num()} | <b>Leechers</b> → {task.leechers_num()}"
                except Exception:
                    pass
            # TODO: Add Connected Peers
        elif tstatus == MirrorStatus.STATUS_SEED:
            msg += f"\n┠ <b>Size</b> → <i>{task.size()}</i> | <b>Uploaded</b>  → <i>{task.uploaded_bytes()}</i>"
            msg += f"\n┠ <b>Status</b> → <b>{tstatus}</b>"
            msg += f"\n┠ <b>Speed</b> → <i>{task.seed_speed()}</i>"
            msg += f"\n┠ <b>Ratio</b> → <i>{task.ratio()}</i>"
            msg += f"\n┠ <b>Time</b> → <i>{task.seeding_time()}</i> | <b>Elapsed</b> → <i>{get_readable_time(elapsed)}</i>"
        else:
            msg += f"\n┠ <b>Size</b> → <i>{task.size()}</i>"
        msg += f"\n┠ <b>Engine</b> → <i>{task.engine}</i>"
        msg += f"\n┠ <b>In Mode</b> → <i>{task.listener.mode[0]}</i>"
        msg += f"\n┠ <b>Out Mode</b> → <i>{task.listener.mode[1]}</i>"
        # TODO: Add Bt Sel
        from ..telegram_helper.bot_commands import BotCommands
        msg += f"\n<b>┖ Stop</b> → <i>/{BotCommands.CancelTaskCommand[1]}_{task.gid()}</i>\n\n"

    if len(msg) == 0:
        if status == "All":
            return None, None
        else:
            msg = f"No Active {status} Tasks!\n\n"

    msg += "⌬ <b><u>Bot Stats</u></b>"
    buttons = ButtonMaker()
    if not is_user:
        buttons.data_button("📜 TStats", f"status {sid} ov", position="header")
    if len(tasks) > STATUS_LIMIT:
        msg += f"<b>Page:</b> {page_no}/{pages} | <b>Tasks:</b> {tasks_no} | <b>Step:</b> {page_step}\n"
        buttons.data_button("<<", f"status {sid} pre", position="header")
        buttons.data_button(">>", f"status {sid} nex", position="header")
        if tasks_no > 30:
            for i in [1, 2, 4, 6, 8, 10, 15]:
                buttons.data_button(i, f"status {sid} ps {i}", position="footer")
    if status != "All" or tasks_no > 20:
        for label, status_value in list(STATUSES.items()):
            if status_value != status:
                buttons.data_button(label, f"status {sid} st {status_value}")
    buttons.data_button("♻️ Refresh", f"status {sid} ref", position="header")
    button = buttons.build_menu(8)
    msg += f"\n┟ <b>CPU</b> → {cpu_percent()}% | <b>F</b> → {get_readable_file_size(disk_usage(DOWNLOAD_DIR).free)} [{round(100 - disk_usage(DOWNLOAD_DIR).percent, 1)}%]"
    msg += f"\n┖ <b>RAM</b> → {virtual_memory().percent}% | <b>UP</b> → {get_readable_time(time() - bot_start_time)}"
    return msg, button
