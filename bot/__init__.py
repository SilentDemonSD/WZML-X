#!/usr/bin/env python3
from tzlocal import get_localzone
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from pyrogram import Client as tgClient, enums
from pymongo import MongoClient
from asyncio import Lock
from dotenv import load_dotenv, dotenv_values
from threading import Thread
from time import sleep, time
from subprocess import Popen, run as srun
from os import remove as osremove, path as ospath, environ, getcwd
from aria2p import API as ariaAPI, Client as ariaClient
from qbittorrentapi import Client as qbClient
from faulthandler import enable as faulthandler_enable
from socket import setdefaulttimeout
from logging import getLogger, FileHandler, StreamHandler, INFO, basicConfig, error as log_error, info as log_info, warning as log_warning
from uvloop import install

faulthandler_enable()
install()
setdefaulttimeout(600)

botStartTime = time()

basicConfig(format="[%(asctime)s] [%(levelname)s] - %(message)s",
            datefmt="%d-%b-%y %I:%M:%S %p",
            handlers=[FileHandler('log.txt'), StreamHandler()],
            level=INFO)

LOGGER = getLogger(__name__)

load_dotenv('config.env', override=True)

Interval = []
QbInterval = []
QbTorrents = {}
DRIVES_NAMES = []
DRIVES_IDS = []
INDEX_URLS = []
GLOBAL_EXTENSION_FILTER = ['aria2', '!qB']
user_data = {}
extra_buttons = {}
shorteneres_list = []
aria2_options = {}
qbit_options = {}
queued_dl = {}
queued_up = {}
non_queued_dl = set()
non_queued_up = set()


def get_version():
    MAJOR = '1'
    MINOR = '0'
    PATCH = '1'
    return f"v{MAJOR}.{MINOR}.{PATCH}-x"


try:
    if bool(environ.get('_____REMOVE_THIS_LINE_____')):
        log_error('The README.md file there to be read! Exiting now!')
        exit()
except:
    pass

download_dict_lock = Lock()
status_reply_dict_lock = Lock()
queue_dict_lock = Lock()
qb_listener_lock = Lock()
status_reply_dict = {}
download_dict = {}
rss_dict = {}

BOT_TOKEN = environ.get('BOT_TOKEN', '')
if len(BOT_TOKEN) == 0:
    log_error("BOT_TOKEN variable is missing! Exiting now")
    exit(1)


bot_id = BOT_TOKEN.split(':', 1)[0]

DATABASE_URL = environ.get('DATABASE_URL', '')
if len(DATABASE_URL) == 0:
    DATABASE_URL = ''

if DATABASE_URL:
    conn = MongoClient(DATABASE_URL)
    db = conn.wzmlx
    current_config = dict(dotenv_values('config.env'))
    old_config = db.settings.deployConfig.find_one({'_id': bot_id})
    if old_config is None:
        db.settings.deployConfig.replace_one(
            {'_id': bot_id}, current_config, upsert=True)
    else:
        del old_config['_id']
    if old_config and old_config != current_config:
        db.settings.deployConfig.replace_one(
            {'_id': bot_id}, current_config, upsert=True)
    elif config_dict := db.settings.config.find_one({'_id': bot_id}):
        del config_dict['_id']
        for key, value in config_dict.items():
            environ[key] = str(value)
    if pf_dict := db.settings.files.find_one({'_id': bot_id}):
        del pf_dict['_id']
        for key, value in pf_dict.items():
            if value:
                file_ = key.replace('__', '.')
                with open(file_, 'wb+') as f:
                    f.write(value)
    if a2c_options := db.settings.aria2c.find_one({'_id': bot_id}):
        del a2c_options['_id']
        aria2_options = a2c_options
    if qbit_opt := db.settings.qbittorrent.find_one({'_id': bot_id}):
        del qbit_opt['_id']
        qbit_options = qbit_opt
    conn.close()
    BOT_TOKEN = environ.get('BOT_TOKEN', '')
    bot_id = BOT_TOKEN.split(':', 1)[0]
    DATABASE_URL = environ.get('DATABASE_URL', '')
else:
    config_dict = {}

OWNER_ID = environ.get('OWNER_ID', '')
if len(OWNER_ID) == 0:
    log_error("OWNER_ID variable is missing! Exiting now")
    exit(1)
else:
    OWNER_ID = int(OWNER_ID)

TELEGRAM_API = environ.get('TELEGRAM_API', '')
if len(TELEGRAM_API) == 0:
    log_error("TELEGRAM_API variable is missing! Exiting now")
    exit(1)
else:
    TELEGRAM_API = int(TELEGRAM_API)

TELEGRAM_HASH = environ.get('TELEGRAM_HASH', '')
if len(TELEGRAM_HASH) == 0:
    log_error("TELEGRAM_HASH variable is missing! Exiting now")
    exit(1)

GDRIVE_ID = environ.get('GDRIVE_ID', '')
if len(GDRIVE_ID) == 0:
    GDRIVE_ID = ''

RCLONE_PATH = environ.get('RCLONE_PATH', '')
if len(RCLONE_PATH) == 0:
    RCLONE_PATH = ''

RCLONE_FLAGS = environ.get('RCLONE_FLAGS', '')
if len(RCLONE_FLAGS) == 0:
    RCLONE_FLAGS = ''

DEFAULT_UPLOAD = environ.get('DEFAULT_UPLOAD', '')
if DEFAULT_UPLOAD != 'rc' and DEFAULT_UPLOAD != 'ddl':
    DEFAULT_UPLOAD = 'gd'

DOWNLOAD_DIR = environ.get('DOWNLOAD_DIR', '')
if len(DOWNLOAD_DIR) == 0:
    DOWNLOAD_DIR = '/usr/src/app/downloads/'
elif not DOWNLOAD_DIR.endswith("/"):
    DOWNLOAD_DIR = f'{DOWNLOAD_DIR}/'

AUTHORIZED_CHATS = environ.get('AUTHORIZED_CHATS', '')
if len(AUTHORIZED_CHATS) != 0:
    aid = AUTHORIZED_CHATS.split()
    for id_ in aid:
        user_data[int(id_.strip())] = {'is_auth': True}

SUDO_USERS = environ.get('SUDO_USERS', '')
if len(SUDO_USERS) != 0:
    aid = SUDO_USERS.split()
    for id_ in aid:
        user_data[int(id_.strip())] = {'is_sudo': True}

EXTENSION_FILTER = environ.get('EXTENSION_FILTER', '')
if len(EXTENSION_FILTER) > 0:
    fx = EXTENSION_FILTER.split()
    for x in fx:
        if x.strip().startswith('.'):
            x = x.lstrip('.')
        GLOBAL_EXTENSION_FILTER.append(x.strip().lower())

IS_PREMIUM_USER = False
user = ''
USER_SESSION_STRING = environ.get('USER_SESSION_STRING', '')
if len(USER_SESSION_STRING) != 0:
    log_info("Creating client from USER_SESSION_STRING")
    user = tgClient('user', TELEGRAM_API, TELEGRAM_HASH, session_string=USER_SESSION_STRING,
                    parse_mode=enums.ParseMode.HTML).start()
    IS_PREMIUM_USER = user.me.is_premium

MEGA_EMAIL = environ.get('MEGA_EMAIL', '')
MEGA_PASSWORD = environ.get('MEGA_PASSWORD', '')
if len(MEGA_EMAIL) == 0 or len(MEGA_PASSWORD) == 0:
    log_warning('MEGA Credentials not provided!')
    MEGA_EMAIL = ''
    MEGA_PASSWORD = ''

UPTOBOX_TOKEN = environ.get('UPTOBOX_TOKEN', '')
if len(UPTOBOX_TOKEN) == 0:
    UPTOBOX_TOKEN = ''

INDEX_URL = environ.get('INDEX_URL', '').rstrip("/")
if len(INDEX_URL) == 0:
    INDEX_URL = ''

SEARCH_API_LINK = environ.get('SEARCH_API_LINK', '').rstrip("/")
if len(SEARCH_API_LINK) == 0:
    SEARCH_API_LINK = ''

LEECH_FILENAME_PREFIX = environ.get('LEECH_FILENAME_PREFIX', '')
if len(LEECH_FILENAME_PREFIX) == 0:
    LEECH_FILENAME_PREFIX = ''

LEECH_FILENAME_SUFFIX = environ.get('LEECH_FILENAME_SUFFIX', '')
if len(LEECH_FILENAME_SUFFIX) == 0:
    LEECH_FILENAME_SUFFIX = ''

LEECH_FILENAME_CAPTION = environ.get('LEECH_FILENAME_CAPTION', '')
if len(LEECH_FILENAME_CAPTION) == 0:
    LEECH_FILENAME_CAPTION = ''

LEECH_FILENAME_REMNAME = environ.get('LEECH_FILENAME_REMNAME', '')
if len(LEECH_FILENAME_REMNAME) == 0:
    LEECH_FILENAME_REMNAME = ''

SEARCH_PLUGINS = environ.get('SEARCH_PLUGINS', '')
if len(SEARCH_PLUGINS) == 0:
    SEARCH_PLUGINS = ''

MAX_SPLIT_SIZE = 4194304000 if IS_PREMIUM_USER else 2097152000

LEECH_SPLIT_SIZE = environ.get('LEECH_SPLIT_SIZE', '')
if len(LEECH_SPLIT_SIZE) == 0 or int(LEECH_SPLIT_SIZE) > MAX_SPLIT_SIZE:
    LEECH_SPLIT_SIZE = MAX_SPLIT_SIZE
else:
    LEECH_SPLIT_SIZE = int(LEECH_SPLIT_SIZE)

STATUS_UPDATE_INTERVAL = environ.get('STATUS_UPDATE_INTERVAL', '')
if len(STATUS_UPDATE_INTERVAL) == 0:
    STATUS_UPDATE_INTERVAL = 10
else:
    STATUS_UPDATE_INTERVAL = int(STATUS_UPDATE_INTERVAL)

AUTO_DELETE_MESSAGE_DURATION = environ.get('AUTO_DELETE_MESSAGE_DURATION', '')
if len(AUTO_DELETE_MESSAGE_DURATION) == 0:
    AUTO_DELETE_MESSAGE_DURATION = 30
else:
    AUTO_DELETE_MESSAGE_DURATION = int(AUTO_DELETE_MESSAGE_DURATION)

YT_DLP_OPTIONS = environ.get('YT_DLP_OPTIONS', '')
if len(YT_DLP_OPTIONS) == 0:
    YT_DLP_OPTIONS = ''

SEARCH_LIMIT = environ.get('SEARCH_LIMIT', '')
SEARCH_LIMIT = 0 if len(SEARCH_LIMIT) == 0 else int(SEARCH_LIMIT)

LEECH_LOG_ID = environ.get('LEECH_LOG_ID', '')
LEECH_LOG_ID = '' if len(LEECH_LOG_ID) == 0 else int(LEECH_LOG_ID)

STATUS_LIMIT = environ.get('STATUS_LIMIT', '')
STATUS_LIMIT = 10 if len(STATUS_LIMIT) == 0 else int(STATUS_LIMIT)

CMD_SUFFIX = environ.get('CMD_SUFFIX', '')

RSS_CHAT_ID = environ.get('RSS_CHAT_ID', '')
RSS_CHAT_ID = '' if len(RSS_CHAT_ID) == 0 else int(RSS_CHAT_ID)

RSS_DELAY = environ.get('RSS_DELAY', '')
RSS_DELAY = 900 if len(RSS_DELAY) == 0 else int(RSS_DELAY)

TORRENT_TIMEOUT = environ.get('TORRENT_TIMEOUT', '')
TORRENT_TIMEOUT = '' if len(TORRENT_TIMEOUT) == 0 else int(TORRENT_TIMEOUT)

QUEUE_ALL = environ.get('QUEUE_ALL', '')
QUEUE_ALL = '' if len(QUEUE_ALL) == 0 else int(QUEUE_ALL)

QUEUE_DOWNLOAD = environ.get('QUEUE_DOWNLOAD', '')
QUEUE_DOWNLOAD = '' if len(QUEUE_DOWNLOAD) == 0 else int(QUEUE_DOWNLOAD)

QUEUE_UPLOAD = environ.get('QUEUE_UPLOAD', '')
QUEUE_UPLOAD = '' if len(QUEUE_UPLOAD) == 0 else int(QUEUE_UPLOAD)

INCOMPLETE_TASK_NOTIFIER = environ.get('INCOMPLETE_TASK_NOTIFIER', '')
INCOMPLETE_TASK_NOTIFIER = INCOMPLETE_TASK_NOTIFIER.lower() == 'true'

STOP_DUPLICATE = environ.get('STOP_DUPLICATE', '')
STOP_DUPLICATE = STOP_DUPLICATE.lower() == 'true'

IS_TEAM_DRIVE = environ.get('IS_TEAM_DRIVE', '')
IS_TEAM_DRIVE = IS_TEAM_DRIVE.lower() == 'true'

USE_SERVICE_ACCOUNTS = environ.get('USE_SERVICE_ACCOUNTS', '')
USE_SERVICE_ACCOUNTS = USE_SERVICE_ACCOUNTS.lower() == 'true'

WEB_PINCODE = environ.get('WEB_PINCODE', '')
WEB_PINCODE = WEB_PINCODE.lower() == 'true'

AS_DOCUMENT = environ.get('AS_DOCUMENT', '')
AS_DOCUMENT = AS_DOCUMENT.lower() == 'true'

EQUAL_SPLITS = environ.get('EQUAL_SPLITS', '')
EQUAL_SPLITS = EQUAL_SPLITS.lower() == 'true'

MEDIA_GROUP = environ.get('MEDIA_GROUP', '')
MEDIA_GROUP = MEDIA_GROUP.lower() == 'true'

BASE_URL_PORT = environ.get('BASE_URL_PORT', '')
BASE_URL_PORT = 80 if len(BASE_URL_PORT) == 0 else int(BASE_URL_PORT)

BASE_URL = environ.get('BASE_URL', '').rstrip("/")
if len(BASE_URL) == 0:
    log_warning('BASE_URL not provided!')
    BASE_URL = ''

UPSTREAM_REPO = environ.get('UPSTREAM_REPO', '')
if len(UPSTREAM_REPO) == 0:
    UPSTREAM_REPO = ''

UPSTREAM_BRANCH = environ.get('UPSTREAM_BRANCH', '')
if len(UPSTREAM_BRANCH) == 0:
    UPSTREAM_BRANCH = 'master'

RCLONE_SERVE_URL = environ.get('RCLONE_SERVE_URL', '')
if len(RCLONE_SERVE_URL) == 0:
    RCLONE_SERVE_URL = ''

RCLONE_SERVE_PORT = environ.get('RCLONE_SERVE_PORT', '')
RCLONE_SERVE_PORT = 8080 if len(
    RCLONE_SERVE_PORT) == 0 else int(RCLONE_SERVE_PORT)

RCLONE_SERVE_USER = environ.get('RCLONE_SERVE_USER', '')
if len(RCLONE_SERVE_USER) == 0:
    RCLONE_SERVE_USER = ''

RCLONE_SERVE_PASS = environ.get('RCLONE_SERVE_PASS', '')
if len(RCLONE_SERVE_PASS) == 0:
    RCLONE_SERVE_PASS = ''

STORAGE_THRESHOLD = environ.get('STORAGE_THRESHOLD', '')
STORAGE_THRESHOLD = '' if len(
    STORAGE_THRESHOLD) == 0 else float(STORAGE_THRESHOLD)

TORRENT_LIMIT = environ.get('TORRENT_LIMIT', '')
TORRENT_LIMIT = '' if len(TORRENT_LIMIT) == 0 else float(TORRENT_LIMIT)

DIRECT_LIMIT = environ.get('DIRECT_LIMIT', '')
DIRECT_LIMIT = '' if len(DIRECT_LIMIT) == 0 else float(DIRECT_LIMIT)

YTDLP_LIMIT = environ.get('YTDLP_LIMIT', '')
YTDLP_LIMIT = '' if len(YTDLP_LIMIT) == 0 else float(YTDLP_LIMIT)

GDRIVE_LIMIT = environ.get('GDRIVE_LIMIT', '')
GDRIVE_LIMIT = '' if len(GDRIVE_LIMIT) == 0 else float(GDRIVE_LIMIT)

CLONE_LIMIT = environ.get('CLONE_LIMIT', '')
CLONE_LIMIT = '' if len(CLONE_LIMIT) == 0 else float(CLONE_LIMIT)

MEGA_LIMIT = environ.get('MEGA_LIMIT', '')
MEGA_LIMIT = '' if len(MEGA_LIMIT) == 0 else float(MEGA_LIMIT)

LEECH_LIMIT = environ.get('LEECH_LIMIT', '')
LEECH_LIMIT = '' if len(LEECH_LIMIT) == 0 else float(LEECH_LIMIT)

USER_MAX_TASKS = environ.get('USER_MAX_TASKS', '')
USER_MAX_TASKS = '' if len(USER_MAX_TASKS) == 0 else int(USER_MAX_TASKS)

PLAYLIST_LIMIT = environ.get('PLAYLIST_LIMIT', '')
PLAYLIST_LIMIT = '' if len(PLAYLIST_LIMIT) == 0 else int(PLAYLIST_LIMIT)

FSUB_IDS = environ.get('FSUB_IDS', '')
if len(FSUB_IDS) == 0:
    FSUB_IDS = ''

MIRROR_LOG_ID = environ.get('MIRROR_LOG_ID', '')
if len(MIRROR_LOG_ID) == 0:
    MIRROR_LOG_ID = ''

BOT_PM = environ.get('BOT_PM', '')
BOT_PM = BOT_PM.lower() == 'true'

DAILY_TASK_LIMIT = environ.get('DAILY_TASK_LIMIT', '')
DAILY_TASK_LIMIT = '' if len(DAILY_TASK_LIMIT) == 0 else int(DAILY_TASK_LIMIT)

DAILY_MIRROR_LIMIT = environ.get('DAILY_MIRROR_LIMIT', '')
DAILY_MIRROR_LIMIT = '' if len(
    DAILY_MIRROR_LIMIT) == 0 else float(DAILY_MIRROR_LIMIT)

DAILY_LEECH_LIMIT = environ.get('DAILY_LEECH_LIMIT', '')
DAILY_LEECH_LIMIT = '' if len(
    DAILY_LEECH_LIMIT) == 0 else float(DAILY_LEECH_LIMIT)

DISABLE_DRIVE_LINK = environ.get('DISABLE_DRIVE_LINK', '')
DISABLE_DRIVE_LINK = DISABLE_DRIVE_LINK.lower() == 'true'

BOT_THEME = environ.get('BOT_THEME', '')
if len(BOT_THEME) == 0:
    BOT_THEME = 'minimal'

IMAGES = environ.get('IMAGES', '')
IMAGES = (IMAGES.replace("'", '').replace('"', '').replace(
    '[', '').replace(']', '').replace(",", "")).split()


IMG_SEARCH = environ.get('IMG_SEARCH', '')
IMG_SEARCH = (IMG_SEARCH.replace("'", '').replace('"', '').replace(
    '[', '').replace(']', '').replace(",", "")).split()

IMG_PAGE = environ.get('IMG_PAGE', '')
IMG_PAGE = 1 if not IMG_PAGE else int(IMG_PAGE)

AUTHOR_NAME = environ.get('AUTHOR_NAME', '')
if len(AUTHOR_NAME) == 0:
    AUTHOR_NAME = 'WZML-X'

AUTHOR_URL = environ.get('AUTHOR_URL', '')
if len(AUTHOR_URL) == 0:
    AUTHOR_URL = 'https://t.me/WZML_X'

TITLE_NAME = environ.get('TITLE_NAME', '')
if len(TITLE_NAME) == 0:
    TITLE_NAME = 'WeebZone-X'

GD_INFO = environ.get('GD_INFO', '')
if len(GD_INFO) == 0:
    GD_INFO = 'Uploaded by WZML-X'

SAVE_MSG = environ.get('SAVE_MSG', '')
SAVE_MSG = SAVE_MSG.lower() == 'true'

SET_COMMANDS = environ.get('SET_COMMANDS', '')
SET_COMMANDS = SET_COMMANDS.lower() == 'true'

TOKEN_TIMEOUT = environ.get('TOKEN_TIMEOUT', '')
TOKEN_TIMEOUT = int(TOKEN_TIMEOUT) if TOKEN_TIMEOUT.isdigit() else ''

LOGIN_PASS = environ.get('LOGIN_PASS', '')
if len(LOGIN_PASS) == 0:
    LOGIN_PASS = None

IMDB_TEMPLATE = environ.get('IMDB_TEMPLATE', '')
if len(IMDB_TEMPLATE) == 0:
    IMDB_TEMPLATE = '''<b>Title: </b> {title} [{year}]
<b>Also Known As:</b> {aka}
<b>Rating ⭐️:</b> <i>{rating}</i>
<b>Release Info: </b> <a href="{url_releaseinfo}">{release_date}</a>
<b>Genre: </b>{genres}
<b>IMDb URL:</b> {url}
<b>Language: </b>{languages}
<b>Country of Origin : </b> {countries}

<b>Story Line: </b><code>{plot}</code>

<a href="{url_cast}">Read More ...</a>'''

ANIME_TEMPLATE = environ.get('ANIME_TEMPLATE', '')
if len(ANIME_TEMPLATE) == 0:
    ANIME_TEMPLATE = '''<b>{ro_title}</b>({na_title})
<b>Format</b>: <code>{format}</code>
<b>Status</b>: <code>{status}</code>
<b>Start Date</b>: <code>{startdate}</code>
<b>End Date</b>: <code>{enddate}</code>
<b>Season</b>: <code>{season}</code>
<b>Country</b>: {country}
<b>Episodes</b>: <code>{episodes}</code>
<b>Duration</b>: <code>{duration}</code>
<b>Average Score</b>: <code>{avgscore}</code>
<b>Genres</b>: {genres}
<b>Hashtag</b>: {hashtag}
<b>Studios</b>: {studios}

<b>Description</b>: <i>{description}</i>'''

config_dict = {'ANIME_TEMPLATE': ANIME_TEMPLATE,
               'AS_DOCUMENT': AS_DOCUMENT,
               'AUTHORIZED_CHATS': AUTHORIZED_CHATS,
               'AUTO_DELETE_MESSAGE_DURATION': AUTO_DELETE_MESSAGE_DURATION,
               'BASE_URL': BASE_URL,
               'BASE_URL_PORT': BASE_URL_PORT,
               'BOT_TOKEN': BOT_TOKEN,
               'CMD_SUFFIX': CMD_SUFFIX,
               'DATABASE_URL': DATABASE_URL,
               'DEFAULT_UPLOAD': DEFAULT_UPLOAD,
               'DOWNLOAD_DIR': DOWNLOAD_DIR,
               'STORAGE_THRESHOLD': STORAGE_THRESHOLD,
               'TORRENT_LIMIT': TORRENT_LIMIT,
               'DIRECT_LIMIT': DIRECT_LIMIT,
               'YTDLP_LIMIT': YTDLP_LIMIT,
               'GDRIVE_LIMIT': GDRIVE_LIMIT,
               'CLONE_LIMIT': CLONE_LIMIT,
               'MEGA_LIMIT': MEGA_LIMIT,
               'LEECH_LIMIT': LEECH_LIMIT,
               'FSUB_IDS': FSUB_IDS,
               'USER_MAX_TASKS': USER_MAX_TASKS,
               'PLAYLIST_LIMIT': PLAYLIST_LIMIT,
               'DAILY_TASK_LIMIT': DAILY_TASK_LIMIT,
               'DAILY_MIRROR_LIMIT': DAILY_MIRROR_LIMIT,
               'DAILY_LEECH_LIMIT': DAILY_LEECH_LIMIT,
               'MIRROR_LOG_ID': MIRROR_LOG_ID,
               'LEECH_LOG_ID': LEECH_LOG_ID,
               'BOT_PM': BOT_PM,
               'DISABLE_DRIVE_LINK': DISABLE_DRIVE_LINK,
               'BOT_THEME': BOT_THEME,
               'IMAGES': IMAGES,
               'IMG_SEARCH': IMG_SEARCH,
               'IMG_PAGE': IMG_PAGE,
               'IMDB_TEMPLATE': IMDB_TEMPLATE,
               'AUTHOR_NAME': AUTHOR_NAME,
               'AUTHOR_URL': AUTHOR_URL,
               'TITLE_NAME': TITLE_NAME,
               'GD_INFO': GD_INFO,
               'EQUAL_SPLITS': EQUAL_SPLITS,
               'EXTENSION_FILTER': EXTENSION_FILTER,
               'GDRIVE_ID': GDRIVE_ID,
               'INCOMPLETE_TASK_NOTIFIER': INCOMPLETE_TASK_NOTIFIER,
               'INDEX_URL': INDEX_URL,
               'IS_TEAM_DRIVE': IS_TEAM_DRIVE,
               'LEECH_FILENAME_PREFIX': LEECH_FILENAME_PREFIX,
               'LEECH_FILENAME_SUFFIX': LEECH_FILENAME_SUFFIX,
               'LEECH_FILENAME_CAPTION': LEECH_FILENAME_CAPTION,
               'LEECH_FILENAME_REMNAME': LEECH_FILENAME_REMNAME,
               'LEECH_SPLIT_SIZE': LEECH_SPLIT_SIZE,
               'LOGIN_PASS': LOGIN_PASS,
               'TOKEN_TIMEOUT': TOKEN_TIMEOUT,
               'MEDIA_GROUP': MEDIA_GROUP,
               'MEGA_EMAIL': MEGA_EMAIL,
               'MEGA_PASSWORD': MEGA_PASSWORD,
               'OWNER_ID': OWNER_ID,
               'QUEUE_ALL': QUEUE_ALL,
               'QUEUE_DOWNLOAD': QUEUE_DOWNLOAD,
               'QUEUE_UPLOAD': QUEUE_UPLOAD,
               'RCLONE_FLAGS': RCLONE_FLAGS,
               'RCLONE_PATH': RCLONE_PATH,
               'RCLONE_SERVE_URL': RCLONE_SERVE_URL,
               'RCLONE_SERVE_USER': RCLONE_SERVE_USER,
               'RCLONE_SERVE_PASS': RCLONE_SERVE_PASS,
               'RCLONE_SERVE_PORT': RCLONE_SERVE_PORT,
               'RSS_CHAT_ID': RSS_CHAT_ID,
               'RSS_DELAY': RSS_DELAY,
               'SAVE_MSG': SAVE_MSG,
               'SEARCH_API_LINK': SEARCH_API_LINK,
               'SEARCH_LIMIT': SEARCH_LIMIT,
               'SEARCH_PLUGINS': SEARCH_PLUGINS,
               'SET_COMMANDS': SET_COMMANDS,
               'STATUS_LIMIT': STATUS_LIMIT,
               'STATUS_UPDATE_INTERVAL': STATUS_UPDATE_INTERVAL,
               'STOP_DUPLICATE': STOP_DUPLICATE,
               'SUDO_USERS': SUDO_USERS,
               'TELEGRAM_API': TELEGRAM_API,
               'TELEGRAM_HASH': TELEGRAM_HASH,
               'TORRENT_TIMEOUT': TORRENT_TIMEOUT,
               'UPSTREAM_REPO': UPSTREAM_REPO,
               'UPSTREAM_BRANCH': UPSTREAM_BRANCH,
               'UPTOBOX_TOKEN': UPTOBOX_TOKEN,
               'USER_SESSION_STRING': USER_SESSION_STRING,
               'USE_SERVICE_ACCOUNTS': USE_SERVICE_ACCOUNTS,
               'WEB_PINCODE': WEB_PINCODE,
               'YT_DLP_OPTIONS': YT_DLP_OPTIONS}

if GDRIVE_ID:
    DRIVES_NAMES.append("Main")
    DRIVES_IDS.append(GDRIVE_ID)
    INDEX_URLS.append(INDEX_URL)

if ospath.exists('list_drives.txt'):
    with open('list_drives.txt', 'r+') as f:
        lines = f.readlines()
        for line in lines:
            temp = line.strip().split()
            DRIVES_IDS.append(temp[1])
            DRIVES_NAMES.append(temp[0].replace("_", " "))
            if len(temp) > 2:
                INDEX_URLS.append(temp[2])
            else:
                INDEX_URLS.append('')

if ospath.exists('buttons.txt'):
    with open('buttons.txt', 'r+') as f:
        lines = f.readlines()
        for line in lines:
            temp = line.strip().split()
            if len(extra_buttons.keys()) == 4:
                break
            if len(temp) == 2:
                extra_buttons[temp[0].replace("_", " ")] = temp[1]

if ospath.exists('shorteners.txt'):
    with open('shorteners.txt', 'r+') as f:
        lines = f.readlines()
        for line in lines:
            temp = line.strip().split()
            if len(temp) == 2:
                shorteneres_list.append({'domain': temp[0],'api_key': temp[1]})

if BASE_URL:
    Popen(
        f"gunicorn web.wserver:app --bind 0.0.0.0:{BASE_URL_PORT} --worker-class gevent", shell=True)

srun(["qbittorrent-nox", "-d", f"--profile={getcwd()}"])
if not ospath.exists('.netrc'):
    with open('.netrc', 'w'):
        pass
srun(["chmod", "600", ".netrc"])
srun(["cp", ".netrc", "/root/.netrc"])
srun(["chmod", "+x", "aria.sh"])
srun("./aria.sh", shell=True)
if ospath.exists('accounts.zip'):
    if ospath.exists('accounts'):
        srun(["rm", "-rf", "accounts"])
    srun(["7z", "x", "-o.", "-aoa", "accounts.zip", "accounts/*.json"])
    srun(["chmod", "-R", "777", "accounts"])
    osremove('accounts.zip')
if not ospath.exists('accounts'):
    config_dict['USE_SERVICE_ACCOUNTS'] = False
sleep(0.5)

aria2 = ariaAPI(ariaClient(host="http://localhost", port=6800, secret=""))


def get_client():
    return qbClient(host="localhost", port=8090, VERIFY_WEBUI_CERTIFICATE=False, REQUESTS_ARGS={'timeout': (30, 60)})


def aria2c_init():
    try:
        log_info("Initializing Aria2c")
        link = "https://linuxmint.com/torrents/lmde-5-cinnamon-64bit.iso.torrent"
        dire = DOWNLOAD_DIR.rstrip("/")
        aria2.add_uris([link], {'dir': dire})
        sleep(3)
        downloads = aria2.get_downloads()
        sleep(10)
        aria2.remove(downloads, force=True, files=True, clean=True)
    except Exception as e:
        log_error(f"Aria2c initializing error: {e}")


Thread(target=aria2c_init).start()
sleep(1.5)

aria2c_global = ['bt-max-open-files', 'download-result', 'keep-unfinished-download-result', 'log', 'log-level',
                 'max-concurrent-downloads', 'max-download-result', 'max-overall-download-limit', 'save-session',
                 'max-overall-upload-limit', 'optimize-concurrent-downloads', 'save-cookies', 'server-stat-of']

if not aria2_options:
    aria2_options = aria2.client.get_global_option()
else:
    a2c_glo = {op: aria2_options[op]
               for op in aria2c_global if op in aria2_options}
    aria2.set_global_options(a2c_glo)

qb_client = get_client()
if not qbit_options:
    qbit_options = dict(qb_client.app_preferences())
    del qbit_options['listen_port']
    for k in list(qbit_options.keys()):
        if k.startswith('rss'):
            del qbit_options[k]
else:
    qb_opt = {**qbit_options}
    for k, v in list(qb_opt.items()):
        if v in ["", "*"]:
            del qb_opt[k]
    qb_client.app_set_preferences(qb_opt)

log_info("Creating client from BOT_TOKEN")
bot = tgClient('bot', TELEGRAM_API, TELEGRAM_HASH, bot_token=BOT_TOKEN, workers=1000,
               parse_mode=enums.ParseMode.HTML).start()
bot_loop = bot.loop
bot_name = bot.me.username
scheduler = AsyncIOScheduler(timezone=str(
    get_localzone()), event_loop=bot_loop)
