from re import match as re_match, findall as re_findall
from os import path as ospath, rename as osrename
from threading import Thread, Event
from time import time
from datetime import datetime
from math import ceil
from html import escape
from psutil import cpu_percent, disk_usage, net_io_counters, virtual_memory
from requests import head as rhead
from urllib.request import urlopen

from bot.helper.telegram_helper.bot_commands import BotCommands
from bot import download_dict, download_dict_lock, botStartTime, DOWNLOAD_DIR, user_data, config_dict
from bot.helper.telegram_helper.button_build import ButtonMaker

import shutil
import psutil
from telegram.error import RetryAfter
from telegram.ext import CallbackQueryHandler
from telegram.message import Message
from telegram.update import Update
from bot import *

MAGNET_REGEX = r"magnet:\?xt=urn:btih:[a-zA-Z0-9]*"

URL_REGEX = r"(?:(?:https?|ftp):\/\/)?[\w/\-?=%.]+\.[\w/\-?=%.]+"

COUNT = 0
PAGE_NO = 1
PAGES = 0


class MirrorStatus:
    if config_dict['EMOJI_THEME']:
        STATUS_UPLOADING = "📤 Upload"
        STATUS_DOWNLOADING = "📥 Download"
        STATUS_CLONING = "♻️ Clone"
        STATUS_WAITING = "💤 Queue"
        STATUS_PAUSED = "⛔️ Pause"
        STATUS_ARCHIVING = "🔐 Archive"
        STATUS_EXTRACTING = "📂 Extract"
        STATUS_SPLITTING = "✂️ Split"
        STATUS_CHECKING = "📝 CheckUp"
        STATUS_SEEDING = "🌧 Seed"
    else:
        STATUS_UPLOADING = "Upload"
        STATUS_DOWNLOADING = "Download"
        STATUS_CLONING = "Clone"
        STATUS_WAITING = "Queue"
        STATUS_PAUSED = "Pause"
        STATUS_ARCHIVING = "Archive"
        STATUS_EXTRACTING = "Extract"
        STATUS_SPLITTING = "Split"
        STATUS_CHECKING = "CheckUp"
        STATUS_SEEDING = "Seed"

class EngineStatus:
    STATUS_ARIA = "Aria2c📶"
    STATUS_GD = "Google Api♻️"
    STATUS_MEGA = "MegaSDK⭕️"
    STATUS_QB = "qBittorrent🦠"
    STATUS_TG = "Pyrogram💥"
    STATUS_YT = "YT-dlp🌟"
    STATUS_EXT = "Extract | pExtract⚔️"
    STATUS_SPLIT = "FFmpeg✂️"
    STATUS_ZIP = "p7zip🛠"

    
SIZE_UNITS = ['B', 'KB', 'MB', 'GB', 'TB', 'PB']

class setInterval:
    def __init__(self, interval, action):
        self.interval = interval
        self.action = action
        self.stopEvent = Event()
        thread = Thread(target=self.__setInterval)
        thread.start()

    def __setInterval(self):
        nextTime = time() + self.interval
        while not self.stopEvent.wait(nextTime - time()):
            self.action()
            nextTime = time() + self.interval

    def cancel(self):
        self.stopEvent.set()

def get_readable_file_size(size_in_bytes) -> str:
    if size_in_bytes is None:
        return '0B'
    index = 0
    while size_in_bytes >= 1024:
        size_in_bytes /= 1024
        index += 1
    try:
        return f'{round(size_in_bytes, 2)}{SIZE_UNITS[index]}'
    except IndexError:
        return 'File too large'

def getDownloadByGid(gid):
    with download_dict_lock:
        for dl in list(download_dict.values()):
            if dl.gid() == gid:
                return dl
    return None

def getAllDownload(req_status: str):
    with download_dict_lock:
        for dl in list(download_dict.values()):
            status = dl.status()
            if req_status in ['all', status]:
                return dl
    return None

def bt_selection_buttons(id_: str):
    gid = id_[:12] if len(id_) > 20 else id_

    pincode = ""
    for n in id_:
        if n.isdigit():
            pincode += str(n)
        if len(pincode) == 4:
            break

    buttons = ButtonMaker()
    BASE_URL = config_dict['BASE_URL']
    if config_dict['WEB_PINCODE']:
        buttons.buildbutton("Select Files", f"{BASE_URL}/app/files/{id_}")
        buttons.sbutton("Pincode", f"btsel pin {gid} {pincode}")
    else:
        buttons.buildbutton("Select Files", f"{BASE_URL}/app/files/{id_}?pin_code={pincode}")
    buttons.sbutton("Done Selecting", f"btsel done {gid} {id_}")
    return buttons.build_menu(2)


def get_user_task(user_id):
    user_task = 0
    for task in list(download_dict.values()):
        userid = task.message.from_user.id
        if userid == user_id: user_task += 1
    return user_task

def progress_bar(percentage):
    """Returns a progress bar for download"""
    if isinstance(percentage, str):
        return "N/A"
    try:
        percentage = int(percentage)
    except Exception:
        percentage = 0
    comp = "▰"
    ncomp = "▱"
    return "".join(comp if i <= percentage // 10 else ncomp for i in range(1, 11))

def timeformatter(milliseconds: int) -> str:
    seconds, milliseconds = divmod(int(milliseconds), 1000)
    minutes, seconds = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    days, hours = divmod(hours, 24)
    tmp = ((str(days) + " days, ") if days else "") + \
        ((str(hours) + " hours, ") if hours else "") + \
        ((str(minutes) + " min, ") if minutes else "") + \
        ((str(seconds) + " sec, ") if seconds else "") + \
        ((str(milliseconds) + " millisec, ") if milliseconds else "")
    return tmp[:-2]

def get_progress_bar_string(status):
    completed = status.processed_bytes() / 8
    total = status.size_raw() / 8
    p = 0 if total == 0 else round(completed * 100 / total)
    p = min(max(p, 0), 100)
    cFull = p // 8
    cPart = p % 8 - 1
    p_str = config_dict['FINISHED_PROGRESS_STR'] * cFull
    if cPart >= 0:
        p_str += config_dict['MULTI_WORKING_PROGRESS_STR'][cPart]
    p_str += config_dict['UN_FINISHED_PROGRESS_STR']  * (12 - cFull)
    p_str = f"[{p_str}]"
    return p_str


def get_readable_message():
    with download_dict_lock:
        msg = f""
        if STATUS_LIMIT := config_dict['STATUS_LIMIT']:
            tasks = len(download_dict)
            global pages
            globals()['PAGES'] = ceil(tasks/STATUS_LIMIT)
            if PAGE_NO > PAGES and PAGES != 0:
                globals()['COUNT'] -= STATUS_LIMIT
                globals()['PAGE_NO'] -= 1
        for index, download in enumerate(list(download_dict.values())[COUNT:], start=1):
            msg += f"<b>╭ <a href='{download.message.link}'>{download.status()}</a>: </b>"
            msg += f"<code>{escape(str(download.name()))}</code>"
            if download.status() not in [MirrorStatus.STATUS_SEEDING, MirrorStatus.STATUS_SPLITTING]:
                if config_dict['EMOJI_THEME']:
                    msg += f"\n<b>├</b>{get_progress_bar_string(download)} {download.progress()}"
                    msg += f"\n<b>├🔄 Process:</b> {get_readable_file_size(download.processed_bytes())} of {download.size()}"
                    msg += f"\n<b>├⚡ Speed:</b> {download.speed()}"
                    msg += f"\n<b>├⏳ ETA:</b> {download.eta()}"
                    msg += f"<b> | Elapsed: </b>{get_readable_time(time() - download.message.date.timestamp())}"
                    msg += f"\n<b>├⛓️ Engine :</b> {download.eng()}"

                else:
                    msg += f"\n<b>├</b>{get_progress_bar_string(download)} {download.progress()}"
                    msg += f"\n<b>├ Process:</b> {get_readable_file_size(download.processed_bytes())} of {download.size()}"
                    msg += f"\n<b>├ Speed:</b> {download.speed()}"
                    msg += f"\n<b>├ ETA:</b> {download.eta()}"
                    msg += f"<b> | Elapsed: </b>{get_readable_time(time() - download.message.date.timestamp())}"
                    msg += f"\n<b>├ Engine :</b> {download.eng()}"

                if hasattr(download, 'seeders_num'):
                    try:
                        if config_dict['EMOJI_THEME']:
                            msg += f"\n<b>├🌱 Seeders:</b> {download.seeders_num()} | <b>🐌 Leechers:</b> {download.leechers_num()}"
                            msg += f"\n<b>├🧿 Select:</b> <code>/{BotCommands.BtSelectCommand} {download.gid()}</code>"
                        else:
                            msg += f"\n<b>├ Seeders:</b> {download.seeders_num()} | <b>Leechers:</b> {download.leechers_num()}"
                            msg += f"\n<b>├ Select:</b> <code>/{BotCommands.BtSelectCommand} {download.gid()}</code>"
                    except:
                        pass
                if download.message.chat.type != 'private':
                    try:
                        chatid = str(download.message.chat.id)[4:]
                        if config_dict['EMOJI_THEME']:
                            msg += f'\n<b>├🌐 Source: </b><a href="https://t.me/c/{chatid}/{download.message.message_id}">{download.message.from_user.first_name}</a> | <b>Id :</b> <code>{download.message.from_user.id}</code>'
                            msg += f"\n<b>╰❌ </b><code>/{BotCommands.CancelMirror} {download.gid()}</code>"
                        else:
                            msg += f'\n<b>├ Source: </b><a href="https://t.me/c/{chatid}/{download.message.message_id}">{download.message.from_user.first_name}</a> | <b>Id :</b> <code>{download.message.from_user.id}</code>'
                            msg += f"\n<b>╰ Cancel: </b><code>/{BotCommands.CancelMirror} {download.gid()}</code>"                 
                    except:
                        pass
                else:
                    if config_dict['EMOJI_THEME']:
                        msg += f'\n<b>├👤 User:</b> ️<code>{download.message.from_user.first_name}</code> | <b>Id:</b> <code>{download.message.from_user.id}</code>'
                        msg += f"\n<b>╰❌ </b><code>/{BotCommands.CancelMirror} {download.gid()}</code>"
                    else:
                        msg += f'\n<b>├ User:</b> ️<code>{download.message.from_user.first_name}</code> | <b>Id:</b> <code>{download.message.from_user.id}</code>'
                        msg += f"\n<b>╰ Cancel: </b><code>/{BotCommands.CancelMirror} {download.gid()}</code>"

            elif download.status() == MirrorStatus.STATUS_SEEDING:
                if config_dict['EMOJI_THEME']:
                    msg += f"\n<b>├📦 Size: </b>{download.size()}"
                    msg += f"\n<b>├⛓️ Engine:</b> <code>qBittorrent v4.4.2</code>"
                    msg += f"\n<b>├⚡ Speed: </b>{download.upload_speed()}"
                    msg += f"\n<b>├🔺 Uploaded: </b>{download.uploaded_bytes()}"
                    msg += f"\n<b>├📎 Ratio: </b>{download.ratio()}"
                    msg += f" | <b>⏲️ Time: </b>{download.seeding_time()}"
                    msg += f"\n<b>├⏳ Elapsed: </b>{get_readable_time(time() - download.message.date.timestamp())}"
                    msg += f"\n<b>╰❌ </b><code>/{BotCommands.CancelMirror} {download.gid()}</code>"
                else:
                    msg += f"\n<b>├ Size: </b>{download.size()}"
                    msg += f"\n<b>├ Engine:</b> <code>qBittorrent v4.4.2</code>"
                    msg += f"\n<b>├ Speed: </b>{download.upload_speed()}"
                    msg += f"\n<b>├ Uploaded: </b>{download.uploaded_bytes()}"
                    msg += f"\n<b>├ Ratio: </b>{download.ratio()}"
                    msg += f" | <b> Time: </b>{download.seeding_time()}"
                    msg += f"\n<b>├ Elapsed: </b>{get_readable_time(time() - download.message.date.timestamp())}"
                    msg += f"\n<b>╰ </b><code>/{BotCommands.CancelMirror} {download.gid()}</code>"
            else:
                if config_dict['EMOJI_THEME']:
                    msg += f"\n<b>├⛓️ Engine :</b> {download.eng()}"
                    msg += f"\n<b>╰📐 Size: </b>{download.size()}"
                else:
                    msg += f"\n<b>├ Engine :</b> {download.eng()}"
                    msg += f"\n<b>╰ Size: </b>{download.size()}"
            msg += f"\n<b>_________________________________</b>"
            msg += "\n\n"
            if index == STATUS_LIMIT:
                break
        if len(msg) == 0:
            return None, None
        dl_speed = 0
        up_speed = 0
        for download in list(download_dict.values()):
            spd = download.speed()
            if download.status() == MirrorStatus.STATUS_DOWNLOADING:
                spd = download.speed()
                if 'K' in spd:
                    dl_speed += float(spd.split('K')[0]) * 1024
                elif 'M' in spd:
                    dl_speed += float(spd.split('M')[0]) * 1048576
            elif download.status() == MirrorStatus.STATUS_UPLOADING:
                spd = download.speed()
                if 'KB/s' in spd:
                    up_speed += float(spd.split('K')[0]) * 1024
                elif 'MB/s' in spd:
                    up_speed += float(spd.split('M')[0]) * 1048576
            elif download.status() == MirrorStatus.STATUS_SEEDING:
                spd = download.upload_speed()
                if 'K' in spd:
                    up_speed += float(spd.split('K')[0]) * 1024
                elif 'M' in spd:
                    up_speed += float(spd.split('M')[0]) * 1048576
        if config_dict['EMOJI_THEME']:
            bmsg = f"<b>🖥 CPU:</b> {cpu_percent()}% | <b>💿 FREE:</b> {get_readable_file_size(disk_usage(DOWNLOAD_DIR).free)}"
            bmsg += f"\n<b>🎮 RAM:</b> {virtual_memory().percent}% | <b>🟢 UPTIME:</b> {get_readable_time(time() - botStartTime)}"
            bmsg += f"\n<b>🔻 DL:</b> {get_readable_file_size(dl_speed)}/s | <b>🔺 UL:</b> {get_readable_file_size(up_speed)}/s"
        else:
            bmsg = f"<b>CPU:</b> {cpu_percent()}% | <b>FREE:</b> {get_readable_file_size(disk_usage(DOWNLOAD_DIR).free)}"
            bmsg += f"\n<b>RAM:</b> {virtual_memory().percent}% | <b>UPTIME:</b> {get_readable_time(time() - botStartTime)}"
            bmsg += f"\n<b>🔻 DL:</b> {get_readable_file_size(dl_speed)}/s | <b>🔺 UL:</b> {get_readable_file_size(up_speed)}/s"
        
        buttons = ButtonMaker()
        buttons.sbutton("Refresh", "status refresh")
        buttons.sbutton("Statistics", str(THREE))
        buttons.sbutton("Close", "status close")
        sbutton = buttons.build_menu(3)
        
        if STATUS_LIMIT and tasks > STATUS_LIMIT:
            msg += f"<b>Tasks:</b> {tasks}\n"
            buttons = ButtonMaker()
            if config_dict['EMOJI_THEME']:
                buttons.sbutton("⏪Previous", "status pre")
                buttons.sbutton(f"{PAGE_NO}/{PAGES}", str(THREE))
                buttons.sbutton("Next⏩", "status nex")
                buttons.sbutton("Refresh", "status refresh")
                buttons.sbutton("Close", "status close")
            else:
                buttons.sbutton("Previous", "status pre")
                buttons.sbutton(f"{PAGE_NO}/{PAGES}", str(THREE))
                buttons.sbutton("Next", "status nex")
                buttons.sbutton("Refresh", "status refresh")
                buttons.sbutton("Close", "status close")
            button = buttons.build_menu(3)
            return msg + bmsg, button
        return msg + bmsg, sbutton

def turn(data):
    STATUS_LIMIT = config_dict['STATUS_LIMIT']
    try:
        with download_dict_lock:
            global COUNT, PAGE_NO
            if data[1] == "nex":
                if PAGE_NO == PAGES:
                    COUNT = 0
                    PAGE_NO = 1
                else:
                    COUNT += STATUS_LIMIT
                    PAGE_NO += 1
            elif data[1] == "pre":
                if PAGE_NO == 1:
                    COUNT = STATUS_LIMIT * (PAGES - 1)
                    PAGE_NO = PAGES
                else:
                    COUNT -= STATUS_LIMIT
                    PAGE_NO -= 1
        return True
    except:
        return False

def get_readable_time(seconds: int) -> str:
    result = ''
    (days, remainder) = divmod(seconds, 86400)
    days = int(days)
    if days != 0:
        result += f'{days}d'
    (hours, remainder) = divmod(remainder, 3600)
    hours = int(hours)
    if hours != 0:
        result += f'{hours}h'
    (minutes, seconds) = divmod(remainder, 60)
    minutes = int(minutes)
    if minutes != 0:
        result += f'{minutes}m'
    seconds = int(seconds)
    result += f'{seconds}s'
    return result

def is_url(url: str):
    url = re_findall(URL_REGEX, url)
    return bool(url)

def is_gdrive_link(url: str):
    return "drive.google.com" in url

def is_gdtot_link(url: str):
    url = re_match(r'https?://.+\.gdtot\.\S+', url)
    return bool(url)

def is_unified_link(url: str):
    url1 = re_match(r'https?://(anidrive|driveroot|driveflix|indidrive|drivehub)\.in/\S+', url)
    url = re_match(r'https?://(appdrive|driveapp|driveace|gdflix|drivelinks|drivebit|drivesharer|drivepro)\.\S+', url)
    if bool(url1) == True:
        return bool(url1)
    elif bool(url) == True:
        return bool(url)
    else:
        return False

def is_udrive_link(url: str):
    if 'drivehub.ws' in url:
        return 'drivehub.ws' in url
    else:
        url = re_match(r'https?://(hubdrive|katdrive|kolop|drivefire|drivebuzz)\.\S+', url)
        return bool(url)
    
def is_sharer_link(url: str):
    url = re_match(r'https?://(sharer)\.pw/\S+', url)
    return bool(url)

def is_sharedrive_link(url: str):
    url = re_match(r'https?://(sharedrive)\.\S+', url)
    return bool(url)

def is_filepress_link(url: str):
    url = re_match(r'https?://(filepress|filebee)\.\S+', url)
    return bool(url)

def is_mega_link(url: str):
    return "mega.nz" in url or "mega.co.nz" in url

def get_mega_link_type(url: str):
    if "folder" in url:
        return "folder"
    elif "file" in url:
        return "file"
    elif "/#F!" in url:
        return "folder"
    return "file"

def is_magnet(url: str):
    magnet = re_findall(MAGNET_REGEX, url)
    return bool(magnet)

def new_thread(fn):
    """To use as decorator to make a function call threaded.
    Needs import
    from threading import Thread"""

    def wrapper(*args, **kwargs):
        thread = Thread(target=fn, args=args, kwargs=kwargs)
        thread.start()
        return thread

    return wrapper

def get_content_type(link: str) -> str:
    try:
        res = rhead(link, allow_redirects=True, timeout=5, headers = {'user-agent': 'Wget/1.12'})
        content_type = res.headers.get('content-type')
    except:
        try:
            res = urlopen(link, timeout=5)
            info = res.info()
            content_type = info.get_content_type()
        except:
            content_type = None
    return content_type

def change_filename(file_, user_id_, dirpath=None, up_path=None, all_edit=True, mirror_type=False):
    user_dict = user_data.get(user_id_, False)
    if mirror_type:
        PREFIX = user_dict.get('mprefix') if user_dict and user_dict.get('mprefix') else ''
        REMNAME = user_dict.get('mremname') if user_dict and user_dict.get('mremname') else ''
        SUFFIX = user_dict.get('msuffix') if user_dict and user_dict.get('msuffix') else ''
    else:
        PREFIX = user_dict.get('prefix') if user_dict and user_dict.get('prefix') else ''
        REMNAME = user_dict.get('remname') if user_dict and user_dict.get('remname') else ''
        SUFFIX = user_dict.get('suffix') if user_dict and user_dict.get('suffix') else ''

    FSTYLE = user_dict.get('cfont')[1] if user_dict and user_dict.get('cfont') else ''
    CAPTION = user_dict.get('caption') if user_dict and user_dict.get('caption') else ''

    #MysteryStyle ~ Tele-LeechX
    if file_.startswith('www'):
        file_ = ' '.join(file_.split()[1:])
    if REMNAME:
        if not REMNAME.startswith('|'):
            REMNAME = f"|{REMNAME}"
        slit = REMNAME.split("|")
        __newFileName = file_
        for rep in range(1, len(slit)):
            args = slit[rep].split(":")
            if len(args) == 3:
                __newFileName = __newFileName.replace(args[0], args[1], int(args[2]))
            elif len(args) == 2:
                __newFileName = __newFileName.replace(args[0], args[1])
            elif len(args) == 1:
                __newFileName = __newFileName.replace(args[0], '')
        file_ = __newFileName
        LOGGER.info("Remname : "+file_)
    if PREFIX:
        if not file_.startswith(PREFIX):
            file_ = f"{PREFIX}{file_}"
    if SUFFIX and not mirror_type:
        sufLen = len(SUFFIX)
        fileDict = file_.split('.')
        _extIn = 1 + len(fileDict[-1])
        _extOutName = '.'.join(fileDict[:-1]).replace('.', ' ').replace('-', ' ')
        _newExtFileName = f"{_extOutName}{SUFFIX}.{fileDict[-1]}"
        if len(_extOutName) > (64 - (sufLen + _extIn)):
            _newExtFileName = (
                _extOutName[: 64 - (sufLen + _extIn)]
                + f"{SUFFIX}.{fileDict[-1]}"
            )
        file_ = _newExtFileName
    elif SUFFIX:
        file_ = f"{ospath.splitext(file_)[0]}{SUFFIX}{ospath.splitext(file_)[1]}"

    if (PREFIX or REMNAME or SUFFIX) and all_edit:
        new_path = ospath.join(dirpath, file_)
        osrename(up_path, new_path)
        up_path = new_path

    cap_mono = ""
    cfont = config_dict['CAPTION_FONT'] if not FSTYLE else FSTYLE
    if CAPTION and all_edit:
        CAPTION = CAPTION.replace('\|', '%%')
        slit = CAPTION.split("|")
        cap_mono = slit[0].format(
            filename = file_,
            size = get_readable_file_size(ospath.getsize(up_path))
        )
        if len(slit) > 1:
            for rep in range(1, len(slit)):
                args = slit[rep].split(":")
                if len(args) == 3:
                   cap_mono = cap_mono.replace(args[0], args[1], int(args[2]))
                elif len(args) == 2:
                    cap_mono = cap_mono.replace(args[0], args[1])
                elif len(args) == 1:
                    cap_mono = cap_mono.replace(args[0], '')
        cap_mono = cap_mono.replace('%%', '|')
    elif all_edit:
        cap_mono = file_ if FSTYLE == 'r' else f"<{cfont}>{file_}</{cfont}>"

    return up_path, file_, cap_mono

def update_user_ldata(id_, key, value):
    if id_ in user_data:
        user_data[id_][key] = value
    else:
        user_data[id_] = {key: value}

def is_sudo(user_id):
    if user_id in user_data:
        return user_data[user_id].get('is_sudo')
    return False

def is_paid(user_id):
    if user_id in user_data and user_data[user_id].get('is_paid'):
        ex_date = user_data[user_id].get('expiry_date')
        if ex_date:
            odate = datetime.strptime(ex_date, '%d-%m-%Y')
            ndate = datetime.today()
            if odate.year <= ndate.year:
                if odate.month <= ndate.month:
                    if odate.day < ndate.day:
                        return False
        return True
    else: return False

ONE, TWO, THREE = range(3)
def pop_up_stats(update, context):
    query = update.callback_query
    stats = bot_sys_stats()
    query.answer(text=stats, show_alert=True)
def bot_sys_stats():
    sent = get_readable_file_size(net_io_counters().bytes_recv)
    recv = get_readable_file_size(net_io_counters().bytes_sent)
    num_active = 0
    num_upload = 0
    num_seeding = 0
    num_zip = 0
    num_unzip = 0
    num_split = 0
    tasks = len(download_dict)
    cpu = cpu_percent()
    mem = virtual_memory().percent
    disk = disk_usage("/").percent
    for stats in list(download_dict.values()):
        if stats.status() == MirrorStatus.STATUS_DOWNLOADING:
            num_active += 1
        if stats.status() == MirrorStatus.STATUS_UPLOADING:
            num_upload += 1
        if stats.status() == MirrorStatus.STATUS_SEEDING:
            num_seeding += 1
        if stats.status() == MirrorStatus.STATUS_ARCHIVING:
            num_zip += 1
        if stats.status() == MirrorStatus.STATUS_EXTRACTING:
            num_unzip += 1
        if stats.status() == MirrorStatus.STATUS_SPLITTING:
            num_split += 1
    return f"""
Made with ❤️ by {config_dict['CREDIT_NAME']}

Tasks: {tasks}

CPU: {progress_bar(cpu)} {cpu}%
RAM: {progress_bar(mem)} {mem}%
DISK: {progress_bar(disk)} {disk}%

SENT: {sent} | RECV: {recv}

DLs: {num_active} | ULs: {num_upload} | SEEDING: {num_seeding}
ZIP: {num_zip} | UNZIP: {num_unzip} | SPLIT: {num_split}
"""
    return stats
dispatcher.add_handler(
    CallbackQueryHandler(pop_up_stats, pattern="^" + str(THREE) + "$")
)
