#!/usr/bin/env python3
from base64 import b64encode
from datetime import datetime
from os import path as ospath
from pkg_resources import get_distribution
from aiofiles import open as aiopen
from aiofiles.os import remove as aioremove, path as aiopath, mkdir
from re import match as re_match
from time import time
from html import escape
from uuid import uuid4
from subprocess import run as srun
from asyncio import create_subprocess_exec, create_subprocess_shell, run_coroutine_threadsafe, sleep
from asyncio.subprocess import PIPE
from functools import partial, wraps
from concurrent.futures import ThreadPoolExecutor

from aiohttp import ClientSession as aioClientSession
from psutil import virtual_memory, cpu_percent, disk_usage
from requests import get as rget
from mega import MegaApi
from pyrogram.enums import ChatType
from pyrogram.types import BotCommand
from pyrogram.errors import PeerIdInvalid

from bot.helper.ext_utils.db_handler import DbManger
from bot.helper.themes import BotTheme
from bot import OWNER_ID, bot_name, DATABASE_URL, LOGGER, get_client, aria2, download_dict, download_dict_lock, botStartTime, user_data, config_dict, bot_loop, extra_buttons, user
from bot.helper.telegram_helper.bot_commands import BotCommands
from bot.helper.telegram_helper.button_build import ButtonMaker
from bot.helper.ext_utils.telegraph_helper import telegraph
from bot.helper.ext_utils.shortners import short_url

THREADPOOL = ThreadPoolExecutor(max_workers=1000)

MAGNET_REGEX = r'magnet:\?xt=urn:(btih|btmh):[a-zA-Z0-9]*\s*'

URL_REGEX = r'^(?!\/)(rtmps?:\/\/|mms:\/\/|rtsp:\/\/|https?:\/\/|ftp:\/\/)?([^\/:]+:[^\/@]+@)?(www\.)?(?=[^\/:\s]+\.[^\/:\s]+)([^\/:\s]+\.[^\/:\s]+)(:\d+)?(\/[^#\s]*[\s\S]*)?(\?[^#\s]*)?(#.*)?$'

SIZE_UNITS = ['B', 'KB', 'MB', 'GB', 'TB', 'PB']

STATUS_START = 0
PAGES = 1
PAGE_NO = 1


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
    STATUS_UPLOADDDL = "Upload DDL"


class setInterval:
    def __init__(self, interval, action):
        self.interval = interval
        self.action = action
        self.task = bot_loop.create_task(self.__set_interval())

    async def __set_interval(self):
        while True:
            await sleep(self.interval)
            await self.action()

    def cancel(self):
        self.task.cancel()


def get_readable_file_size(size_in_bytes):
    if size_in_bytes is None:
        return '0B'
    index = 0
    while size_in_bytes >= 1024 and index < len(SIZE_UNITS) - 1:
        size_in_bytes /= 1024
        index += 1
    return f'{size_in_bytes:.2f}{SIZE_UNITS[index]}' if index > 0 else f'{size_in_bytes}B'


async def getDownloadByGid(gid):
    async with download_dict_lock:
        return next((dl for dl in download_dict.values() if dl.gid() == gid), None)


async def getAllDownload(req_status, user_id=None):
    dls = []
    async with download_dict_lock:
        for dl in list(download_dict.values()):
            if user_id and user_id != dl.message.from_user.id:
                continue
            status = dl.status()
            if req_status in ['all', status]:
                dls.append(dl)
    return dls


async def get_user_tasks(user_id, maxtask):
    if tasks := await getAllDownload('all', user_id):
        return len(tasks) >= maxtask


def bt_selection_buttons(id_):
    gid = id_[:12] if len(id_) > 20 else id_
    pincode = ''.join([n for n in id_ if n.isdigit()][:4])
    buttons = ButtonMaker()
    BASE_URL = config_dict['BASE_URL']
    if config_dict['WEB_PINCODE']:
        buttons.ubutton("Select Files", f"{BASE_URL}/app/files/{id_}")
        buttons.ibutton("Pincode", f"btsel pin {gid} {pincode}")
    else:
        buttons.ubutton("Select Files", f"{BASE_URL}/app/files/{id_}?pin_code={pincode}")
    buttons.ibutton("Cancel", f"btsel rm {gid} {id_}")
    buttons.ibutton("Done Selecting", f"btsel done {gid} {id_}")
    return buttons.build_menu(2)


async def get_telegraph_list(telegraph_content):
    path = [(await telegraph.create_page(title=f"{config_dict['TITLE_NAME']} Drive Search", content=content))["path"] for content in telegraph_content]
    if len(path) > 1:
        await telegraph.edit_telegraph(path, telegraph_content)
    buttons = ButtonMaker()
    buttons.ubutton("🔎 VIEW", f"https://telegra.ph/{path[0]}")
    buttons = extra_btns(buttons)
    return buttons.build_menu(1)

def handleIndex(index, dic):
    while True:
        if abs(index) >= len(dic):
            if index < 0: index = len(dic) - abs(index)
            elif index > 0: index = index - len(dic)
        else: break
    return index

def get_progress_bar_string(pct):
    pct = float(str(pct).strip('%'))
    p = min(max(pct, 0), 100)
    cFull = int(p // 8)
    cPart = int(p % 8 - 1)
    p_str = '■' * cFull
    if cPart >= 0:
        p_str += ['▤', '▥', '▦', '▧', '▨', '▩', '■'][cPart]
    p_str += '□' * (12 - cFull)
    return f"[{p_str}]"


def get_p7zip_version():
    try:
        result = srun(['7z', '-version'], capture_output=True, text=True)
        return result.stdout.split('\n')[2].split(' ')[2]
    except FileNotFoundError:
        return ''


def get_ffmpeg_version():
    try:
        result = srun(['ffmpeg', '-version'], capture_output=True, text=True)
        return result.stdout.split('\n')[0].split(' ')[2].split('ubuntu')[0]
    except FileNotFoundError:
        return ''


def get_rclone_version():
    try:
        result = srun(['rclone', 'version'], capture_output=True, text=True)
        return result.stdout.split('\n')[0].split(' ')[1]
    except FileNotFoundError:
        return ''


class EngineStatus:
    STATUS_ARIA = f"Aria2 v{aria2.client.get_version()['version']}"
    STATUS_GD = f"Google-API v{get_distribution('google-api-python-client').version}"
    STATUS_MEGA = f"MegaSDK v{MegaApi('test').getVersion()}"
    STATUS_QB = f"qBit {get_client().app.version}"
    STATUS_TG = f"Pyrogram v{get_distribution('pyrogram').version}"
    STATUS_YT = f"yt-dlp v{get_distribution('yt-dlp').version}"
    STATUS_EXT = "pExtract v2"
    STATUS_SPLIT_MERGE = f"ffmpeg v{get_ffmpeg_version()}"
    STATUS_ZIP = f"p7zip v{get_p7zip_version()}"
    STATUS_QUEUE = "Sleep v0"
    STATUS_RCLONE = f"RClone {get_rclone_version()}"


def get_readable_message():
    msg = ""
    button = None
    STATUS_LIMIT = config_dict['STATUS_LIMIT']
    tasks = len(download_dict)
    globals()['PAGES'] = (tasks + STATUS_LIMIT - 1) // STATUS_LIMIT
    if PAGE_NO > PAGES and PAGES != 0:
        globals()['STATUS_START'] = STATUS_LIMIT * (PAGES - 1)
        globals()['PAGE_NO'] = PAGES
    for download in list(download_dict.values())[STATUS_START:STATUS_LIMIT+STATUS_START]:
        msg_link = download.message.link if download.message.chat.type in [
            ChatType.SUPERGROUP, ChatType.CHANNEL] and not config_dict['DELETE_LINKS'] else ''
        msg += BotTheme('STATUS_NAME', Name="Task is being Processed!" if config_dict['SAFE_MODE'] else escape(f'{download.name()}'))
        if download.status() not in [MirrorStatus.STATUS_SPLITTING, MirrorStatus.STATUS_SEEDING]:
            if download.status() != MirrorStatus.STATUS_UPLOADDDL:
                msg += BotTheme('BAR', Bar=f"{get_progress_bar_string(download.progress())} {download.progress()}")
                msg += BotTheme('PROCESSED', Processed=f"{download.processed_bytes()} of {download.size()}")
            msg += BotTheme('STATUS', Status=download.status(), Url=msg_link)
            if download.status() != MirrorStatus.STATUS_UPLOADDDL:
                msg += BotTheme('ETA', Eta=download.eta())
                msg += BotTheme('SPEED', Speed=download.speed())
            msg += BotTheme('ELAPSED', Elapsed=get_readable_time(time() - download.message.date.timestamp()))
            msg += BotTheme('ENGINE', Engine=download.eng())
            msg += BotTheme('STA_MODE', Mode=download.upload_details['mode'])
            if hasattr(download, 'seeders_num'):
                try:
                    msg += BotTheme('SEEDERS', Seeders=download.seeders_num())
                    msg += BotTheme('LEECHERS', Leechers=download.leechers_num())
                except:
                    pass
        elif download.status() == MirrorStatus.STATUS_SEEDING:
            msg += BotTheme('STATUS', Status=download.status(), Url=msg_link)
            msg += BotTheme('SEED_SIZE', Size=download.size())
            msg += BotTheme('SEED_SPEED', Speed=download.upload_speed())
            msg += BotTheme('UPLOADED', Upload=download.uploaded_bytes())
            msg += BotTheme('RATIO', Ratio=download.ratio())
            msg += BotTheme('TIME', Time=download.seeding_time())
            msg += BotTheme('SEED_ENGINE', Engine=download.eng())
        else:
            msg += BotTheme('STATUS', Status=download.status(), Url=msg_link)
            msg += BotTheme('STATUS_SIZE', Size=download.size())
            msg += BotTheme('NON_ENGINE', Engine=download.eng())

        msg += BotTheme('USER',
                        User=download.message.from_user.mention(style="html"))
        msg += BotTheme('ID', Id=download.message.from_user.id)
        if (download.eng()).startswith("qBit"):
            msg += BotTheme('BTSEL', Btsel=f"/{BotCommands.BtSelectCommand}_{download.gid()}")
        msg += BotTheme('CANCEL', Cancel=f"/{BotCommands.CancelMirror}_{download.gid()}")

    if len(msg) == 0:
        return None, None

    dl_speed = 0

    def convert_speed_to_bytes_per_second(spd):
        if 'K' in spd:
            return float(spd.split('K')[0]) * 1024
        elif 'M' in spd:
            return float(spd.split('M')[0]) * 1048576
        else:
            return 0

    dl_speed = 0
    up_speed = 0
    for download in download_dict.values():
        tstatus = download.status()
        spd = download.speed() if tstatus != MirrorStatus.STATUS_SEEDING else download.upload_speed()
        speed_in_bytes_per_second = convert_speed_to_bytes_per_second(spd)
        if tstatus == MirrorStatus.STATUS_DOWNLOADING:
            dl_speed += speed_in_bytes_per_second
        elif tstatus == MirrorStatus.STATUS_UPLOADING or tstatus == MirrorStatus.STATUS_SEEDING:
            up_speed += speed_in_bytes_per_second

    msg += BotTheme('FOOTER')
    buttons = ButtonMaker()
    buttons.ibutton(BotTheme('REFRESH', Page=f"{PAGE_NO}/{PAGES}"), "status ref")
    if tasks > STATUS_LIMIT:
        if config_dict['BOT_MAX_TASKS']:
            msg += BotTheme('BOT_TASKS', Tasks=tasks, Ttask=config_dict['BOT_MAX_TASKS'], Free=config_dict['BOT_MAX_TASKS']-tasks)
        else:
            msg += BotTheme('TASKS', Tasks=tasks)
        buttons = ButtonMaker()
        buttons.ibutton(BotTheme('PREVIOUS'), "status pre")
        buttons.ibutton(BotTheme('REFRESH', Page=f"{PAGE_NO}/{PAGES}"), "status ref")
        buttons.ibutton(BotTheme('NEXT'), "status nex")
    button = buttons.build_menu(3)
    msg += BotTheme('Cpu', cpu=cpu_percent())
    msg += BotTheme('FREE', free=get_readable_file_size(disk_usage(config_dict['DOWNLOAD_DIR']).free), free_p=round(100-disk_usage(config_dict['DOWNLOAD_DIR']).percent, 1))
    msg += BotTheme('Ram', ram=virtual_memory().percent)
    msg += BotTheme('uptime', uptime=get_readable_time(time() - botStartTime))
    msg += BotTheme('DL', DL=get_readable_file_size(dl_speed))
    msg += BotTheme('UL', UL=get_readable_file_size(up_speed))
    return msg, button


async def turn_page(data):
    STATUS_LIMIT = config_dict['STATUS_LIMIT']
    global STATUS_START, PAGE_NO
    async with download_dict_lock:
        if data[1] == "nex":
            if PAGE_NO == PAGES:
                STATUS_START = 0
                PAGE_NO = 1
            else:
                STATUS_START += STATUS_LIMIT
                PAGE_NO += 1
        elif data[1] == "pre":
            if PAGE_NO == 1:
                STATUS_START = STATUS_LIMIT * (PAGES - 1)
                PAGE_NO = PAGES
            else:
                STATUS_START -= STATUS_LIMIT
                PAGE_NO -= 1


def get_readable_time(seconds):
    periods = [('d', 86400), ('h', 3600), ('m', 60), ('s', 1)]
    result = ''
    for period_name, period_seconds in periods:
        if seconds >= period_seconds:
            period_value, seconds = divmod(seconds, period_seconds)
            result += f'{int(period_value)}{period_name}'
    return result


def is_magnet(url):
    return bool(re_match(MAGNET_REGEX, url))


def is_url(url):
    return bool(re_match(URL_REGEX, url))


def is_gdrive_link(url):
    return "drive.google.com" in url


def is_telegram_link(url):
    return url.startswith(('https://t.me/', 'tg://openmessage?user_id='))


def is_share_link(url):
    return bool(re_match(r'https?:\/\/.+\.gdtot\.\S+|https?:\/\/(filepress|filebee|appdrive|gdflix)\.\S+', url))


def is_mega_link(url):
    return "mega.nz" in url or "mega.co.nz" in url


def is_rclone_path(path):
    return bool(re_match(r'^(mrcc:)?(?!magnet:)(?![- ])[a-zA-Z0-9_\. -]+(?<! ):(?!.*\/\/).*$|^rcl$', path))


def get_mega_link_type(url):
    return "folder" if "folder" in url or "/#F!" in url else "file"


def arg_parser(items, arg_base):
    if not items:
        return arg_base
    bool_arg_set = {'-b', '-e', '-z', '-s', '-j', '-d'}
    t = len(items)
    i = 0
    arg_start = -1

    while i + 1 <= t:
        part = items[i].strip()
        if part in arg_base:
            if arg_start == -1:
                arg_start = i
            if i + 1 == t and part in bool_arg_set or part in ['-s', '-j']:
                arg_base[part] = True
            else:
                sub_list = []
                for j in range(i + 1, t):
                    item = items[j].strip()
                    if item in arg_base:
                        if part in bool_arg_set and not sub_list:
                            arg_base[part] = True
                        break
                    sub_list.append(item.strip())
                    i += 1
                if sub_list:
                    arg_base[part] = " ".join(sub_list)
        i += 1

    link = []
    if items[0].strip() not in arg_base:
        if arg_start == -1:
            link.extend(item.strip() for item in items)
        else:
            link.extend(items[r].strip() for r in range(arg_start))
        if link:
            arg_base['link'] = " ".join(link)
    return arg_base


async def get_content_type(url):
    try:
        async with aioClientSession(trust_env=True) as session:
            async with session.get(url, verify_ssl=False) as response:
                return response.headers.get('Content-Type')
    except:
        return None


def update_user_ldata(id_, key=None, value=None):
    exception_keys = ['is_sudo', 'is_auth', 'dly_tasks']
    if not key and not value:
        if id_ in user_data:
            updated_data = {}
            for k, v in user_data[id_].items():
                if k in exception_keys:
                    updated_data[k] = v
            user_data[id_] = updated_data
        return
    user_data.setdefault(id_, {})
    user_data[id_][key] = value


async def download_image_url(url):
    path = "Images/"
    if not await aiopath.isdir(path):
        await mkdir(path)
    image_name = url.split('/')[-1]
    des_dir = ospath.join(path, image_name)
    async with aioClientSession() as session:
        async with session.get(url) as response:
            if response.status == 200:
                async with aiopen(des_dir, 'wb') as file:
                    async for chunk in response.content.iter_chunked(1024):
                        await file.write(chunk)
                LOGGER.info(f"Image Downloaded Successfully as {image_name}")
            else:
                LOGGER.error(f"Failed to Download Image from {url}")
    return des_dir


async def cmd_exec(cmd, shell=False):
    if shell:
        proc = await create_subprocess_shell(cmd, stdout=PIPE, stderr=PIPE)
    else:
        proc = await create_subprocess_exec(*cmd, stdout=PIPE, stderr=PIPE)
    stdout, stderr = await proc.communicate()
    stdout = stdout.decode().strip()
    stderr = stderr.decode().strip()
    return stdout, stderr, proc.returncode


def new_task(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        return bot_loop.create_task(func(*args, **kwargs))
    return wrapper


async def sync_to_async(func, *args, wait=True, **kwargs):
    pfunc = partial(func, *args, **kwargs)
    future = bot_loop.run_in_executor(THREADPOOL, pfunc)
    return await future if wait else future


def async_to_sync(func, *args, wait=True, **kwargs):
    future = run_coroutine_threadsafe(func(*args, **kwargs), bot_loop)
    return future.result() if wait else future


def new_thread(func):
    @wraps(func)
    def wrapper(*args, wait=False, **kwargs):
        future = run_coroutine_threadsafe(func(*args, **kwargs), bot_loop)
        return future.result() if wait else future
    return wrapper


async def getdailytasks(user_id, increase_task=False, upleech=0, upmirror=0, check_mirror=False, check_leech=False):
    task, lsize, msize = 0, 0, 0
    if user_id in user_data and user_data[user_id].get('dly_tasks'):
        userdate, task, lsize, msize = user_data[user_id]['dly_tasks']
        nowdate = datetime.today()
        if userdate.year <= nowdate.year and userdate.month <= nowdate.month and userdate.day < nowdate.day:
            task, lsize, msize = 0, 0, 0
            if increase_task:
                task = 1
            elif upleech != 0:
                lsize += upleech
            elif upmirror != 0:
                msize += upmirror
        else:
            if increase_task:
                task += 1
            elif upleech != 0:
                lsize += upleech
            elif upmirror != 0:
                msize += upmirror
    else:
        if increase_task:
            task += 1
        elif upleech != 0:
            lsize += upleech
        elif upmirror != 0:
            msize += upmirror
    update_user_ldata(user_id, 'dly_tasks', [
                      datetime.today(), task, lsize, msize])
    if DATABASE_URL:
        await DbManger().update_user_data(user_id)
    if check_leech:
        return lsize
    elif check_mirror:
        return msize
    return task


def checking_access(user_id, button=None):
    if not config_dict['TOKEN_TIMEOUT'] or bool(user_id == OWNER_ID or user_id in user_data and user_data[user_id].get('is_sudo')):
        return None, button
    user_data.setdefault(user_id, {})
    data = user_data[user_id]
    expire = data.get('time')
    if config_dict['LOGIN_PASS'] is not None and data.get('token', '') == config_dict['LOGIN_PASS']:
        return None, button
    isExpired = (expire is None or expire is not None and (time() - expire) > config_dict['TOKEN_TIMEOUT'])
    if isExpired:
        token = data['token'] if expire is None and 'token' in data else str(uuid4())
        if expire is not None:
            del data['time']
        data['token'] = token
        user_data[user_id].update(data)
        if button is None:
            button = ButtonMaker()
        encrypt_url = b64encode(f"{token}&&{user_id}".encode()).decode()
        button.ubutton('Generate New Token', short_url(f'https://t.me/{bot_name}?start={encrypt_url}'))
        return 'Temp Token is expired, generate a new temp token and try again.', button
    return None, button


def extra_btns(buttons):
    if extra_buttons:
        for btn_name, btn_url in extra_buttons.items():
            buttons.ubutton(btn_name, btn_url)
    return buttons

async def set_commands(client):
    if config_dict['SET_COMMANDS']:
        try:
            await client.set_bot_commands([
            BotCommand(BotCommands.MirrorCommand[0], f'or /{BotCommands.MirrorCommand[1]} Mirror [links/media/rclone_path]'),
            BotCommand(BotCommands.LeechCommand[0], f'or /{BotCommands.LeechCommand[1]} Leech [links/media/rclone_path]'),
            BotCommand(BotCommands.QbMirrorCommand[0], f'or /{BotCommands.QbMirrorCommand[1]} Mirror magnet/torrent using qBittorrent'),
            BotCommand(BotCommands.QbLeechCommand[0], f'or /{BotCommands.QbLeechCommand[1]} Leech magnet/torrent using qBittorrent'),
            BotCommand(BotCommands.YtdlCommand[0], f'or /{BotCommands.YtdlCommand[1]} Mirror yt-dlp supported links via bot'),
            BotCommand(BotCommands.YtdlLeechCommand[0], f'or /{BotCommands.YtdlLeechCommand[1]} Leech yt-dlp supported links via bot'),
            BotCommand(BotCommands.CloneCommand[0], f'or /{BotCommands.CloneCommand[1]} Copy file/folder to Drive (GDrive/RClone)'),
            BotCommand(BotCommands.CountCommand, '[drive_url]: Count file/folder of Google Drive/RClone Drives'),
            BotCommand(BotCommands.StatusCommand[0], f'or /{BotCommands.StatusCommand[1]} Get Bot All Status Stats Message'),
            BotCommand(BotCommands.StatsCommand[0], f'or /{BotCommands.StatsCommand[1]}Check Bot & System stats'),
            BotCommand(BotCommands.BtSelectCommand, 'Select files to download only torrents/magnet qbit/aria2c'),
            BotCommand(BotCommands.CancelMirror, 'Cancel a Task of yours!'),
            BotCommand(BotCommands.CancelAllCommand[0], f'Cancel all Tasks in whole Bots.'),
            BotCommand(BotCommands.ListCommand, 'Search in Drive(s)'),
            BotCommand(BotCommands.SearchCommand, 'Search in Torrent via qBit clients!'),
            BotCommand(BotCommands.HelpCommand, 'Get detailed help about the WZML-X Bot'),
            BotCommand(BotCommands.UserSetCommand[0], f"or /{BotCommands.UserSetCommand[1]} User's Personal Settings (Open in PM)"),
            BotCommand(BotCommands.IMDBCommand, 'Search Movies/Series on IMDB.com and fetch details'),
            BotCommand(BotCommands.AniListCommand, 'Search Animes on AniList.com and fetch details'),
            BotCommand(BotCommands.MyDramaListCommand, 'Search Dramas on MyDramaList.com and fetch details'),
            BotCommand(BotCommands.SpeedCommand[0], f'or /{BotCommands.SpeedCommand[1]} Check Server Up & Down Speed & Details'),
            BotCommand(BotCommands.MediaInfoCommand[0], f'or /{BotCommands.MediaInfoCommand[1]} Generate Mediainfo for Replied Media or DL links'),
            BotCommand(BotCommands.BotSetCommand[0], f"or /{BotCommands.BotSetCommand[1]} Bot's Personal Settings (Owner or Sudo Only)"),
            BotCommand(BotCommands.RestartCommand[0], f'or /{BotCommands.RestartCommand[1]} Restart & Update the Bot (Owner or Sudo Only)'),
            ])
            LOGGER.info('Bot Commands have been Set & Updated')
        except Exception as err:
            LOGGER.error(err)


def is_valid_token(url, token):
    resp = rget(url=f"{url}getAccountDetails?token={token}&allDetails=true").json()
    if resp["status"] == "error-wrongToken":
        raise Exception("Invalid Gofile Token, Get your Gofile token from --> https://gofile.io/myProfile")
