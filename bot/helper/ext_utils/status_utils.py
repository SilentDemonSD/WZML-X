import contextlib
from asyncio import iscoroutinefunction
from html import escape
from time import time
from subprocess import run as srun
from mega import MegaApi
from pkg_resources import DistributionNotFound, get_distribution
from psutil import cpu_percent, disk_usage, virtual_memory

from bot import (
    DOWNLOAD_DIR,
    botStartTime,
    config_dict,
    get_qb_client,
    status_dict,
    task_dict,
    task_dict_lock,
    bot_cache,
    aria2,
)
from bot.helper.ext_utils.bot_utils import sync_to_async
from bot.helper.tele_swi_helper.bot_commands import BotCommands
from bot.helper.tele_swi_helper.button_build import ButtonMaker
from bot.helper.themes import BotTheme

SIZE_UNITS = ["B", "KB", "MB", "GB", "TB", "PB"]


class MirrorStatus:
    STATUS_UPLOADING = "Upload"
    STATUS_DOWNLOADING = "Download"
    STATUS_CLONING = "Clone"
    STATUS_QUEUEDL = "QueueDL"
    STATUS_QUEUEUP = "QueueUp"
    STATUS_PAUSED = "Pause"
    STATUS_ARCHIVING = "Archive"
    STATUS_EXTRACTING = "Extract"
    STATUS_SPLITTING = "Split"
    STATUS_CHECKING = "CheckUp"
    STATUS_SEEDING = "Seed"
    STATUS_SAMVID = "SamVid" # TODO Replace ff & mkvtool status
    STATUS_CONVERTING = "Convert"


STATUSES = {
    "ALL": "All",
    "DL": MirrorStatus.STATUS_DOWNLOADING,
    "UP": MirrorStatus.STATUS_UPLOADING,
    "QD": MirrorStatus.STATUS_QUEUEDL,
    "QU": MirrorStatus.STATUS_QUEUEUP,
    "AR": MirrorStatus.STATUS_ARCHIVING,
    "EX": MirrorStatus.STATUS_EXTRACTING,
    "SD": MirrorStatus.STATUS_SEEDING,
    "CM": MirrorStatus.STATUS_CONVERTING,
    "CL": MirrorStatus.STATUS_CLONING,
    "SP": MirrorStatus.STATUS_SPLITTING,
    "CK": MirrorStatus.STATUS_CHECKING,
    "SV": MirrorStatus.STATUS_SAMVID,
    "PA": MirrorStatus.STATUS_PAUSED,
}



def get_all_versions():
    try:
        result = srun(["7z", "-version"], capture_output=True, text=True)
        vp = result.stdout.split("\n")[2].split(" ")[2]
    except FileNotFoundError:
        vp = ""
    try:
        result = srun(["ffmpeg", "-version"], capture_output=True, text=True)
        vf = result.stdout.split("\n")[0].split(" ")[2].split("ubuntu")[0]
    except FileNotFoundError:
        vf = ""
    try:
        result = srun(["rclone", "version"], capture_output=True, text=True)
        vr = result.stdout.split("\n")[0].split(" ")[1]
    except FileNotFoundError:
        vr = ""
    try:
        vpy = get_distribution("pyrogram").version
    except DistributionNotFound:
        try:
            vpy = get_distribution("pyrofork").version
        except DistributionNotFound:
            vpy = "2.xx.xx"
    bot_cache["eng_versions"] = {
        "p7zip": vp,
        "ffmpeg": vf,
        "rclone": vr,
        "aria": aria2.client.get_version()["version"],
        "aiohttp": get_distribution("aiohttp").version,
        "gapi": get_distribution("google-api-python-client").version,
        "mega": MegaApi("test").getVersion(),
        "qbit": get_qb_client().app.version,
        "pyro": vpy,
        "ytdlp": get_distribution("yt-dlp").version,
    }


class EngineStatus:
    def __init__(self):
        if not (version_cache := bot_cache.get("eng_versions")):
            get_all_versions()
            version_cache = bot_cache.get("eng_versions")
        self.STATUS_ARIA = f"Aria2 v{version_cache['aria']}"
        self.STATUS_AIOHTTP = f"AioHttp {version_cache['aiohttp']}"
        self.STATUS_GD = f"Google-API v{version_cache['gapi']}"
        self.STATUS_MEGA = f"MegaSDK v{version_cache['mega']}"
        self.STATUS_QB = f"qBit {version_cache['qbit']}"
        self.STATUS_TG = f"PyroMulti v{version_cache['pyro']}"
        self.STATUS_YT = f"yt-dlp v{version_cache['ytdlp']}"
        self.STATUS_EXT = "pExtract v2"
        self.STATUS_SPLIT_MERGE = f"ffmpeg v{version_cache['ffmpeg']}"
        self.STATUS_ZIP = f"p7zip v{version_cache['p7zip']}"
        self.STATUS_QUEUE = "Sleep v0"
        self.STATUS_RCLONE = f"RClone {version_cache['rclone']}"


async def getTaskByGid(gid: str):
    async with task_dict_lock:
        for tk in task_dict.values():
            if hasattr(tk, "seeding"):
                await sync_to_async(tk.update)
            if tk.gid() == gid:
                return tk
        return None


def getSpecificTasks(status, userId):
    if status == "All":
        if userId:
            return [tk for tk in task_dict.values() if tk.listener.userId == userId]
        else:
            return list(task_dict.values())
    elif userId:
        return [
            tk
            for tk in task_dict.values()
            if tk.listener.userId == userId
            and (
                (st := tk.status())
                and st == status
                or status == MirrorStatus.STATUS_DOWNLOADING
                and st not in STATUSES.values()
            )
        ]
    else:
        return [
            tk
            for tk in task_dict.values()
            if (st := tk.status())
            and st == status
            or status == MirrorStatus.STATUS_DOWNLOADING
            and st not in STATUSES.values()
        ]


async def getAllTasks(req_status: str, userId):
    async with task_dict_lock:
        return await sync_to_async(getSpecificTasks, req_status, userId)


async def checkUserTasks(userId, maxtask):
    if tasks := await sync_to_async(getSpecificTasks, "All", userId):
        return len(tasks) >= maxtask


def get_readable_file_size(size_in_bytes: int):
    if size_in_bytes is None:
        return "0B"
    index = 0
    while size_in_bytes >= 1024 and index < len(SIZE_UNITS) - 1:
        size_in_bytes /= 1024
        index += 1
    return (
        f"{size_in_bytes:.2f}{SIZE_UNITS[index]}"
        if index > 0
        else f"{size_in_bytes:.2f}B"
    )


def get_readable_time(seconds: int):
    periods = [("d", 86400), ("h", 3600), ("m", 60), ("s", 1)]
    result = ""
    for period_name, period_seconds in periods:
        if seconds >= period_seconds:
            period_value, seconds = divmod(seconds, period_seconds)
            result += f"{int(period_value)}{period_name}"
    return result


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
    cPart = int(p % 8 - 1)
    p_str = "■" * cFull
    if cPart >= 0:
        p_str += ["▤", "▥", "▦", "▧", "▨", "▩", "■"][cPart]
    p_str += "□" * (12 - cFull)
    return f"[{p_str}]"


async def get_readable_message(sid, is_user, page_no=1, status="All", page_step=1):
    msg = ""
    button = None

    tasks = await sync_to_async(getSpecificTasks, status, sid if is_user else None)

    STATUS_LIMIT = config_dict["STATUS_LIMIT"]
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
        msg_link = (
            task.listener.message.link
            if task.listener.isSuperChat
            and not config_dict["DELETE_LINKS"]
            else ""
        )
        elapsed = time() - task.listener.message.date.timestamp()
        tstatus = await sync_to_async(task.status) if status == "All" else status
        # index + start_position
        msg += BotTheme(
            "STATUS_NAME",
            Name="Task is being Processed!"
            if config_dict["SAFE_MODE"]
            and elapsed >= config_dict["STATUS_UPDATE_INTERVAL"]
            else escape(f"{task.name()}"),
        )
        if tstatus not in [
            MirrorStatus.STATUS_SPLITTING,
            MirrorStatus.STATUS_SEEDING,
            MirrorStatus.STATUS_SAMVID,
            MirrorStatus.STATUS_CONVERTING,
            MirrorStatus.STATUS_QUEUEUP,
        ]:
            progress = (
                await task.progress()
                if iscoroutinefunction(task.progress)
                else task.progress()
            )
            msg += BotTheme(
                "BAR",
                Bar=f"{get_progress_bar_string(progress)} {progress}",
            )
            msg += BotTheme(
                "PROCESSED",
                Processed=f"{task.processed_bytes()} of {task.size()}",
            )
            msg += BotTheme("STATUS", Status=tstatus, Url=msg_link)
            msg += BotTheme("ETA", Eta=task.eta())
            msg += BotTheme("SPEED", Speed=task.speed())
            msg += BotTheme("ELAPSED", Elapsed=get_readable_time(elapsed))
            msg += BotTheme("ENGINE", Engine=task.eng())
            msg += BotTheme("STA_MODE", Mode=task.upload_details["mode"])
            if hasattr(task, "seeders_num"):
                with contextlib.suppress(Exception):
                    msg += BotTheme("SEEDERS", Seeders=task.seeders_num())
                    msg += BotTheme("LEECHERS", Leechers=task.leechers_num())
        elif tstatus == MirrorStatus.STATUS_SEEDING:
            msg += BotTheme("STATUS", Status=tstatus, Url=msg_link)
            msg += BotTheme("SEED_SIZE", Size=task.size())
            msg += BotTheme("SEED_SPEED", Speed=task.seed_speed())
            msg += BotTheme("UPLOADED", Upload=task.uploaded_bytes())
            msg += BotTheme("RATIO", Ratio=task.ratio())
            msg += BotTheme("TIME", Time=task.seeding_time())
            msg += BotTheme("SEED_ENGINE", Engine=task.eng())
        else:
            msg += BotTheme("STATUS", Status=task.status(), Url=msg_link)
            msg += BotTheme("STATUS_SIZE", Size=task.size())
            msg += BotTheme("NON_ENGINE", Engine=task.eng())
        
        msg += BotTheme("USER", User=task.message.from_user.mention(style="html"))
        msg += BotTheme("ID", Id=task.message.from_user.id)
        if (task.eng()).startswith("qBit"):
            msg += BotTheme(
                "BTSEL", Btsel=f"/{BotCommands.BtSelectCommand}_{task.gid()}"
            )
        msg += BotTheme(
            "CANCEL", Cancel=f"/{BotCommands.CancelMirror}_{task.gid()}"
        )

    if len(msg) == 0:
        if status == "All":
            return None, None
        else:
            msg = f"No Active {status} Tasks!\n\n"
    msg += BotTheme("FOOTER")
    buttons = ButtonMaker()
    buttons.ibutton(BotTheme("REFRESH", Page=f"{page_no}/{pages}"), f"status {sid} ref")
    if not is_user:
        buttons.ibutton("📜", f"status {sid} ov", position="header")
    if tasks_no > STATUS_LIMIT:
        if config_dict["BOT_MAX_TASKS"]:
            msg += BotTheme(
                "BOT_TASKS",
                Tasks=tasks,
                Ttask=config_dict["BOT_MAX_TASKS"],
                Free=config_dict["BOT_MAX_TASKS"] - tasks,
            )
        else:
            msg += BotTheme("TASKS", Tasks=tasks)
        #msg += f"<b>Page:</b> {page_no}/{pages} | <b>Tasks:</b> {tasks_no} | <b>Step:</b> {page_step}\n"
        buttons.reset()
        buttons.ibutton(BotTheme("PREVIOUS"), f"status {sid} pre", position="header")
        buttons.ibutton(BotTheme("REFRESH", Page=f"{page_no}/{pages}"), f"status {sid} ref")
        buttons.ibutton(BotTheme("NEXT"), f"status {sid} nex", position="header")
        if tasks_no > 30:
            for i in [1, 2, 4, 6, 8, 10, 15]:
                buttons.ibutton(i, f"status {sid} ps {i}", position="footer")
    if status != "All" or tasks_no > 20:
        for label, status_value in list(STATUSES.items())[:9]:
            if status_value != status:
                buttons.ibutton(label, f"status {sid} st {status_value}")
    buttons.ibutton("♻️", f"status {sid} ref", position="header")
    button = buttons.build_menu(3)
    msg += BotTheme("Cpu", cpu=cpu_percent())
    msg += BotTheme(
        "FREE",
        free=get_readable_file_size(disk_usage(config_dict["DOWNLOAD_DIR"]).free),
        free_p=round(100 - disk_usage(config_dict["DOWNLOAD_DIR"]).percent, 1),
    )
    msg += BotTheme("Ram", ram=virtual_memory().percent)
    msg += BotTheme("uptime", uptime=get_readable_time(time() - botStartTime))
    #msg += BotTheme("DL", DL=get_readable_file_size(dl_speed))
    #msg += BotTheme("UL", UL=get_readable_file_size(up_speed))
    return msg, button
