import re
from PIL import Image
from os import environ, remove
from logging import getLogger, FileHandler, StreamHandler, INFO, basicConfig, error as log_error, info as log_info, warning as log_warning
from socket import setdefaulttimeout
from urllib.request import urlretrieve
from faulthandler import enable as faulthandler_enable
from telegram.ext import Updater as tgUpdater
from qbittorrentapi import Client as qbClient
from aria2p import API as ariaAPI, Client as ariaClient
from os import remove as osremove, path as ospath, environ
from requests import get as rget
from json import loads as jsonloads
from subprocess import Popen, run as srun, check_output
from time import sleep, time
from threading import Thread, Lock
from dotenv import load_dotenv
from pyrogram import Client, enums
from asyncio import get_event_loop

main_loop = get_event_loop()

faulthandler_enable()

setdefaulttimeout(600)

botStartTime = time()

basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    handlers=[FileHandler('log.txt'), StreamHandler()],
                    level=INFO)

LOGGER = getLogger(__name__)




PRE_DICT = {}
SUF_DICT = {}
CAP_DICT = {}
LEECH_DICT = {}
REM_DICT = {}
TIME_GAP_STORE = {}
CFONT_DICT = {}

load_dotenv('config.env', override=True)

NETRC_URL = environ.get('NETRC_URL', '')
if len(NETRC_URL) != 0:
    try:
        res = rget(NETRC_URL)
        if res.status_code == 200:
            with open('.netrc', 'wb+') as f:
                f.write(res.content)
        else:
            log_error(f"Failed to download .netrc {res.status_code}")
    except Exception as e:
        log_error(f"NETRC_URL: {e}")

SERVER_PORT = environ.get('SERVER_PORT', '')
if len(SERVER_PORT) == 0:
    SERVER_PORT = 80

BASE_URL = environ.get('BASE_URL_OF_BOT', '').rstrip("/")
if len(BASE_URL) == 0:
    log_warning('BASE_URL_OF_BOT not provided!')
    BASE_URL = None

if BASE_URL is not None:
    Popen(f"gunicorn web.wserver:app --bind 0.0.0.0:{SERVER_PORT}", shell=True)

srun(["qbittorrent-nox", "-d", "--profile=."])
if not ospath.exists('.netrc'):
    srun(["touch", ".netrc"])
srun(["cp", ".netrc", "/root/.netrc"])
srun(["chmod", "600", ".netrc"])
srun(["chmod", "+x", "aria.sh"])
srun("./aria.sh", shell=True)
sleep(0.5)

Interval = []
QbInterval = []
DRIVES_NAMES = []
DRIVES_IDS = []
INDEX_URLS = []
user_data = {}
EXTENSION_FILTER = {'.aria2'}

try:
    if bool(environ.get('_____REMOVE_THIS_LINE_____')):
        log_error('The README.md file there to be read! Exiting now!')
        exit()
except:
    pass

aria2 = ariaAPI(ariaClient(host="http://localhost", port=6800, secret=""))

def get_client():
    return qbClient(host="localhost", port=8090, VERIFY_WEBUI_CERTIFICATE=False, REQUESTS_ARGS={'timeout': (30, 60)})


download_dict_lock = Lock()
status_reply_dict_lock = Lock()
# Key: update.effective_chat.id
# Value: telegram.Message
status_reply_dict = {}
# Key: update.message.message_id
# Value: An object of Status
download_dict = {}
# key: rss_title
# value: [rss_feed, last_link, last_title, filter]
rss_dict = {}


BOT_TOKEN = environ.get('BOT_TOKEN', '')
if len(BOT_TOKEN) == 0:
    log_error("BOT_TOKEN variable is missing! Exiting now")
    exit(1)

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

PARENT_ID = environ.get('GDRIVE_FOLDER_ID', '')
if len(PARENT_ID) == 0:
    PARENT_ID = None

DOWNLOAD_DIR = environ.get('DOWNLOAD_DIR', '')
if len(DOWNLOAD_DIR) == 0:
    DOWNLOAD_DIR = '/usr/src/app/downloads/'
else:
    if not DOWNLOAD_DIR.endswith("/"):
        DOWNLOAD_DIR = DOWNLOAD_DIR + '/'

DOWNLOAD_STATUS_UPDATE_INTERVAL = environ.get('DOWNLOAD_STATUS_UPDATE_INTERVAL', '')
if len(DOWNLOAD_STATUS_UPDATE_INTERVAL) == 0:
    DOWNLOAD_STATUS_UPDATE_INTERVAL = 10
else:
    DOWNLOAD_STATUS_UPDATE_INTERVAL = int(DOWNLOAD_STATUS_UPDATE_INTERVAL)

AUTO_DELETE_MESSAGE_DURATION = environ.get('AUTO_DELETE_MESSAGE_DURATION', '')
if len(AUTO_DELETE_MESSAGE_DURATION) == 0:
    AUTO_DELETE_MESSAGE_DURATION = 30
else:
    AUTO_DELETE_MESSAGE_DURATION = int(AUTO_DELETE_MESSAGE_DURATION)

AUTO_DELETE_UPLOAD_MESSAGE_DURATION = environ.get('AUTO_DELETE_UPLOAD_MESSAGE_DURATION', '')
if len(AUTO_DELETE_UPLOAD_MESSAGE_DURATION) == 0:
    AUTO_DELETE_UPLOAD_MESSAGE_DURATION = -1
else:
    AUTO_DELETE_UPLOAD_MESSAGE_DURATION = int(AUTO_DELETE_UPLOAD_MESSAGE_DURATION)


try:
    TGH_THUMB = getConfig('TGH_THUMB')
    if len(TGH_THUMB) == 0:
        raise KeyError
    photo_dir = 'downloads/' + TGH_THUMB.split('/')[-1]
    urlretrieve(TGH_THUMB, photo_dir)
    Image.open(photo_dir).convert("RGB").save('Thumbnails/weeb.jpg', "JPEG")
    remove(photo_dir)
except:
    TGH_THUMB = ''

aid = environ.get('AUTHORIZED_CHATS', '')
if len(aid) != 0:
    aid = aid.split()
    for id_ in aid:
        user_data[id_.strip()] = {'is_auth': True}

aid = environ.get('SUDO_USERS', '')
if len(aid) != 0:
    aid = aid.split()
    for id_ in aid:
        user_data[id_.strip()] = {'is_sudo': True}

aid = environ.get('PAID_USERS', '')
if len(aid) != 0:
    aid = aid.split()
    for id_ in aid:
        user_data[id_.strip()] = {'is_paid': True}

aid = environ.get('LOG_LEECH', '')
if len(aid) != 0:
    aid = aid.split()
    for id_ in aid:
        user_data[id_.strip()] = {'is_log_leech': True}

aid = environ.get('LEECH_LOG', '')
if len(aid) != 0:
    aid = aid.split()
    for id_ in aid:
        user_data[id_.strip()] = {'is_leech_log': True}

aid = environ.get('MIRROR_LOGS', '')
if len(aid) != 0:
    aid = aid.split()
    for id_ in aid:
        user_data[id_.strip()] = {'is_mirror_log': True}

aid = environ.get('LINK_LOGS', '')
if len(aid) != 0:
    aid = aid.split()
    for id_ in aid:
        user_data[id_.strip()] = {'is_link_log': True}

fx = environ.get('EXTENSION_FILTER', '')
if len(fx) > 0:
    fx = fx.split(' ')
    for x in fx:
        EXTENSION_FILTER.add(x.strip().lower())



LOGGER.info("Generating SESSION_STRING")
app = Client(name='pyrogram', api_id=(TELEGRAM_API), api_hash=TELEGRAM_HASH, bot_token=BOT_TOKEN, parse_mode=enums.ParseMode.HTML, no_updates=True)

def aria2c_init():
    try:
        log_info("Initializing Aria2c")
        link = "https://linuxmint.com/torrents/lmde-5-cinnamon-64bit.iso.torrent"
        dire = DOWNLOAD_DIR.rstrip("/")
        aria2.add_uris([link], {'dir': dire})
        sleep(3)
        downloads = aria2.get_downloads()
        sleep(20)
        for download in downloads:
            aria2.remove([download], force=True, files=True)
    except Exception as e:
        log_error(f"Aria2c initializing error: {e}")
Thread(target=aria2c_init).start()
sleep(1.5)

MEGA_API_KEY = environ.get('MEGA_API_KEY', '')
if len(MEGA_API_KEY) == 0:
    log_warning('MEGA API KEY not provided!')
    MEGA_API_KEY = None

MEGA_EMAIL_ID = environ.get('MEGA_EMAIL_ID', '')
MEGA_PASSWORD = environ.get('MEGA_PASSWORD', '')
if len(MEGA_EMAIL_ID) == 0 or len(MEGA_PASSWORD) == 0:
    log_warning('MEGA Credentials not provided!')
    MEGA_EMAIL_ID = None
    MEGA_PASSWORD = None

DB_URI = environ.get('DATABASE_URL', '')
if len(DB_URI) == 0:
    DB_URI = None

tgBotMaxFileSize = 2097151000

TG_SPLIT_SIZE = environ.get('TG_SPLIT_SIZE', '')
if len(TG_SPLIT_SIZE) == 0 or int(TG_SPLIT_SIZE) > tgBotMaxFileSize:
    TG_SPLIT_SIZE = tgBotMaxFileSize

try:
    USER_SESSION_STRING = environ.get('USER_SESSION_STRING', '')
    if len(USER_SESSION_STRING) == 0:
        raise KeyError
    premium_session = Client(name='premium_session', api_id=TELEGRAM_API, api_hash=TELEGRAM_HASH, session_string=USER_SESSION_STRING, parse_mode=enums.ParseMode.HTML, no_updates=True)
    if not premium_session:
        LOGGER.error("Cannot initialized User Session. Please regenerate USER_SESSION_STRING")
    else:
        premium_session.start()
        if (premium_session.get_me()).is_premium:
            if not LEECH_LOG:
                LOGGER.error("You must set LEECH_LOG for uploads. Eiting now.")
                try: premium_session.send_message(OWNER_ID, "You must set LEECH_LOG for uploads, Exiting Now...")
                except Exception as e: LOGGER.exception(e)
                premium_session.stop()
                app.stop()
                exit(1)
            TG_SPLIT_SIZE = 4194304000
            LOGGER.info("Telegram Premium detected! Leech limit is 4GB now.")
        elif (not DB_URI) or (not RSS_CHAT_ID):
            premium_session.stop()
            LOGGER.info(f"Not using rss. if you want to use fill RSS_CHAT_ID and DB_URI variables.")
except:
    USER_SESSION_STRING = None
    premium_session = None
LOGGER.info(f"TG_SPLIT_SIZE: {TG_SPLIT_SIZE}")

STATUS_LIMIT = environ.get('STATUS_LIMIT', '')
STATUS_LIMIT = None if len(STATUS_LIMIT) == 0 else int(STATUS_LIMIT)

UPTOBOX_TOKEN = environ.get('UPTOBOX_TOKEN', '')
if len(UPTOBOX_TOKEN) == 0:
    UPTOBOX_TOKEN = None

INDEX_URL = environ.get('INDEX_URL', '').rstrip("/")
if len(INDEX_URL) == 0:
    INDEX_URL = None
    INDEX_URLS.append(None)
else:
    INDEX_URLS.append(INDEX_URL)

SEARCH_API_LINK = environ.get('SEARCH_API_LINK', '').rstrip("/")
if len(SEARCH_API_LINK) == 0:
    SEARCH_API_LINK = None

SEARCH_LIMIT = environ.get('SEARCH_LIMIT', '')
SEARCH_LIMIT = 0 if len(SEARCH_LIMIT) == 0 else int(SEARCH_LIMIT)

CMD_INDEX = environ.get('CMD_INDEX', '')


TORRENT_TIMEOUT = environ.get('TORRENT_TIMEOUT', '')
TORRENT_TIMEOUT = None if len(TORRENT_TIMEOUT) == 0 else int(TORRENT_TIMEOUT)

TORRENT_DIRECT_LIMIT = environ.get('TORRENT_DIRECT_LIMIT', '')
TORRENT_DIRECT_LIMIT = None if len(TORRENT_DIRECT_LIMIT) == 0 else float(TORRENT_DIRECT_LIMIT)

CLONE_LIMIT = environ.get('CLONE_LIMIT', '')
CLONE_LIMIT = None if len(CLONE_LIMIT) == 0 else float(CLONE_LIMIT)

LEECH_LIMIT = environ.get('LEECH_LIMIT', '')
LEECH_LIMIT = None if len(LEECH_LIMIT) == 0 else float(LEECH_LIMIT)

MEGA_LIMIT = environ.get('MEGA_LIMIT', '')
MEGA_LIMIT = None if len(MEGA_LIMIT) == 0 else float(MEGA_LIMIT)

STORAGE_THRESHOLD = environ.get('STORAGE_THRESHOLD', '')
STORAGE_THRESHOLD = None if len(STORAGE_THRESHOLD) == 0 else float(STORAGE_THRESHOLD)

ZIP_UNZIP_LIMIT = environ.get('ZIP_UNZIP_LIMIT', '')
ZIP_UNZIP_LIMIT = None if len(ZIP_UNZIP_LIMIT) == 0 else float(ZIP_UNZIP_LIMIT)

TOTAL_TASKS_LIMIT = environ.get('TOTAL_TASKS_LIMIT', '')
TOTAL_TASKS_LIMIT = None if len(TOTAL_TASKS_LIMIT) == 0 else int(TOTAL_TASKS_LIMIT)

USER_TASKS_LIMIT = environ.get('USER_TASKS_LIMIT', '')
USER_TASKS_LIMIT = None if len(USER_TASKS_LIMIT) == 0 else int(USER_TASKS_LIMIT)


try:
    RSS_USER_SESSION_STRING = getConfig('RSS_USER_SESSION_STRING')
    if len(RSS_USER_SESSION_STRING) == 0:
        raise KeyError
    rss_session = Client(name='rss_session', api_id=(TELEGRAM_API), api_hash=TELEGRAM_HASH, session_string=RSS_USER_SESSION_STRING, parse_mode=enums.ParseMode.HTML, no_updates=True)
except:
    USER_SESSION_STRING = None
    rss_session = None

RSS_COMMAND = environ.get('RSS_COMMAND', '')
if len(RSS_COMMAND) == 0:
    RSS_COMMAND = None

RSS_CHAT_ID = environ.get('RSS_CHAT_ID', '')
RSS_CHAT_ID = None if len(RSS_CHAT_ID) == 0 else int(RSS_CHAT_ID)

RSS_DELAY = environ.get('RSS_DELAY', '')
RSS_DELAY = 900 if len(RSS_DELAY) == 0 else int(RSS_DELAY)

SEARCH_PLUGINS = environ.get('SEARCH_PLUGINS', '')
if len(SEARCH_PLUGINS) == 0:
    SEARCH_PLUGINS = None
else:
    SEARCH_PLUGINS = jsonloads(SEARCH_PLUGINS)

INCOMPLETE_TASK_NOTIFIER = environ.get('INCOMPLETE_TASK_NOTIFIER', '')
INCOMPLETE_TASK_NOTIFIER = INCOMPLETE_TASK_NOTIFIER.lower() == 'true'

STOP_DUPLICATE = environ.get('STOP_DUPLICATE', '')
STOP_DUPLICATE = STOP_DUPLICATE.lower() == 'true'

VIEW_LINK = environ.get('VIEW_LINK', '')
VIEW_LINK = VIEW_LINK.lower() == 'true'

SET_BOT_COMMANDS = environ.get('SET_BOT_COMMANDS', '')
SET_BOT_COMMANDS = SET_BOT_COMMANDS.lower() == 'true'

IS_TEAM_DRIVE = environ.get('IS_TEAM_DRIVE', '')
IS_TEAM_DRIVE = IS_TEAM_DRIVE.lower() == 'true'

USE_SERVICE_ACCOUNTS = environ.get('USE_SERVICE_ACCOUNTS', '')
USE_SERVICE_ACCOUNTS = USE_SERVICE_ACCOUNTS.lower() == 'true'

WEB_PINCODE = environ.get('WEB_PINCODE', '')
WEB_PINCODE = WEB_PINCODE.lower() == 'true'

IGNORE_PENDING_REQUESTS = environ.get('IGNORE_PENDING_REQUESTS', '')
IGNORE_PENDING_REQUESTS = IGNORE_PENDING_REQUESTS.lower() == 'true'

AS_DOCUMENT = environ.get('AS_DOCUMENT', '')
AS_DOCUMENT = AS_DOCUMENT.lower() == 'true'

EQUAL_SPLITS = environ.get('EQUAL_SPLITS', '')
EQUAL_SPLITS = EQUAL_SPLITS.lower() == 'true'

MIRROR_ENABLED = environ.get('MIRROR_ENABLED', '')
MIRROR_ENABLED = MIRROR_ENABLED.lower() == 'true'

LEECH_ENABLED = environ.get('LEECH_ENABLED', '')
LEECH_ENABLED = LEECH_ENABLED.lower() == 'true'

WATCH_ENABLED = environ.get('WATCH_ENABLED', '')
WATCH_ENABLED = WATCH_ENABLED.lower() == 'true'

CLONE_ENABLED = environ.get('CLONE_ENABLED', '')
CLONE_ENABLED = CLONE_ENABLED.lower() == 'true'

ANILIST_ENABLED = environ.get('ANILIST_ENABLED', '')
ANILIST_ENABLED = ANILIST_ENABLED.lower() == 'true'

WAYBACK_ENABLED = environ.get('WAYBACK_ENABLED', '')
WAYBACK_ENABLED = WAYBACK_ENABLED.lower() == 'true'

MEDIAINFO_ENABLED = environ.get('MEDIAINFO_ENABLED', '')
MEDIAINFO_ENABLED = MEDIAINFO_ENABLED.lower() == 'true'

TELEGRAPH_STYLE = environ.get('TELEGRAPH_STYLE', '')
TELEGRAPH_STYLE = TELEGRAPH_STYLE.lower() == 'true'

EMOJI_THEME = environ.get('EMOJI_THEME', '')
EMOJI_THEME = EMOJI_THEME.lower() == 'true'

DISABLE_DRIVE_LINK = environ.get('DISABLE_DRIVE_LINK', '')
DISABLE_DRIVE_LINK = DISABLE_DRIVE_LINK.lower() == 'true'

LEECH_LOG_INDEXING = environ.get('LEECH_LOG_INDEXING', '')
LEECH_LOG_INDEXING = LEECH_LOG_INDEXING.lower() == 'true'

BOT_PM = environ.get('BOT_PM', '')
BOT_PM = BOT_PM.lower() == 'true'

FORCE_BOT_PM = environ.get('FORCE_BOT_PM', '')
FORCE_BOT_PM = FORCE_BOT_PM.lower() == 'true'

SOURCE_LINK = environ.get('SOURCE_LINK', '')
SOURCE_LINK = SOURCE_LINK.lower() == 'true'

FSUB = environ.get('FSUB', '')
FSUB = FSUB.lower() == 'true'

PAID_SERVICE = environ.get('PAID_SERVICE', '')
PAID_SERVICE = PAID_SERVICE.lower() == 'true'

SHOW_LIMITS_IN_STATS = environ.get('SHOW_LIMITS_IN_STATS', '')
SHOW_LIMITS_IN_STATS = SHOW_LIMITS_IN_STATS.lower() == 'true'

START_BTN1_NAME = environ.get('START_BTN1_NAME', '')
START_BTN1_URL = environ.get('START_BTN1_URL', '')
if len(START_BTN1_NAME) == 0 or len(START_BTN1_URL) == 0:
    START_BTN1_NAME = 'Master'
    START_BTN1_URL = 'https://t.me/krn_adhikari'

START_BTN2_NAME = environ.get('START_BTN2_NAME', '')
START_BTN2_URL = environ.get('START_BTN2_URL', '')
if len(START_BTN2_NAME) == 0 or len(START_BTN2_URL) == 0:
    START_BTN2_NAME = 'Support Group'
    START_BTN2_URL = 'https://t.me/WeebZone_updates'

BUTTON_FOUR_NAME = environ.get('BUTTON_FOUR_NAME', '')
BUTTON_FOUR_URL = environ.get('BUTTON_FOUR_URL', '')
if len(BUTTON_FOUR_NAME) == 0 or len(BUTTON_FOUR_URL) == 0:
    BUTTON_FOUR_NAME = None
    BUTTON_FOUR_URL = None

BUTTON_FIVE_NAME = environ.get('BUTTON_FIVE_NAME', '')
BUTTON_FIVE_URL = environ.get('BUTTON_FIVE_URL', '')
if len(BUTTON_FIVE_NAME) == 0 or len(BUTTON_FIVE_URL) == 0:
    BUTTON_FIVE_NAME = None
    BUTTON_FIVE_URL = None

BUTTON_SIX_NAME = environ.get('BUTTON_SIX_NAME', '')
BUTTON_SIX_URL = environ.get('BUTTON_SIX_URL', '')
if len(BUTTON_SIX_NAME) == 0 or len(BUTTON_SIX_URL) == 0:
    BUTTON_SIX_NAME = None
    BUTTON_SIX_URL = None

SHORTENER = environ.get('SHORTENER', '')
SHORTENER_API = environ.get('SHORTENER_API', '')
if len(SHORTENER) == 0 or len(SHORTENER_API) == 0:
    SHORTENER = None
    SHORTENER_API = None

CRYPT = environ.get('CRYPT', '')
if len(CRYPT) == 0:
    CRYPT = None

UNIFIED_EMAIL = environ.get('UNIFIED_EMAIL', '')
if len(UNIFIED_EMAIL) == 0:
    UNIFIED_EMAIL = None

UNIFIED_PASS = environ.get('UNIFIED_PASS', '')
if len(UNIFIED_PASS) == 0:
    UNIFIED_PASS = None

HUBDRIVE_CRYPT = environ.get('HUBDRIVE_CRYPT', '')
if len(HUBDRIVE_CRYPT) == 0:
    HUBDRIVE_CRYPT = None

KATDRIVE_CRYPT = environ.get('KATDRIVE_CRYPT', '')
if len(KATDRIVE_CRYPT) == 0:
    KATDRIVE_CRYPT = None

DRIVEFIRE_CRYPT = environ.get('DRIVEFIRE_CRYPT', '')
if len(DRIVEFIRE_CRYPT) == 0:
    DRIVEFIRE_CRYPT = None

MIRROR_LOG_URL = environ.get('MIRROR_LOG_URL', '')
if len(MIRROR_LOG_URL) == 0:
    MIRROR_LOG_URL = None

LEECH_LOG_URL = environ.get('LEECH_LOG_URL', '')
if len(LEECH_LOG_URL) == 0:
    LEECH_LOG_URL = None

TIME_GAP = environ.get('TIME_GAP', '')
if len(TIME_GAP) == 0:
    TIME_GAP = -1

AUTHOR_NAME = environ.get('AUTHOR_NAME', '')
if len(AUTHOR_NAME) == 0:
    AUTHOR_NAME = 'Karan'

AUTHOR_URL = environ.get('AUTHOR_URL', '')
if len(AUTHOR_URL) == 0:
    AUTHOR_URL = 'https://t.me/WeebZone_updates'

TITLE_NAME = environ.get('TITLE_NAME', '')
if len(TITLE_NAME) == 0:
    TITLE_NAME = 'WeebZone'

GD_INFO = environ.get('GD_INFO', '')
if len(GD_INFO) == 0:
    GD_INFO = 'Uploaded by WeebZone Mirror Bot'

CREDIT_NAME = environ.get('CREDIT_NAME', '')
if len(CREDIT_NAME) == 0:
    CREDIT_NAME = 'WeebZone'

NAME_FONT = environ.get('NAME_FONT', '')
if len(NAME_FONT) == 0:
    NAME_FONT = 'code'

CAPTION_FONT = environ.get('CAPTION_FONT', '')
if len(CAPTION_FONT) == 0:
    CAPTION_FONT = 'code'

FINISHED_PROGRESS_STR = environ.get('FINISHED_PROGRESS_STR', '')
UN_FINISHED_PROGRESS_STR = environ.get('UN_FINISHED_PROGRESS_STR', '')
if len(FINISHED_PROGRESS_STR) == 0 or len(FINISHED_PROGRESS_STR) == 0:
    FINISHED_PROGRESS_STR = '●' # '■'
    UN_FINISHED_PROGRESS_STR = '○' # '□'

CHANNEL_USERNAME = environ.get('CHANNEL_USERNAME', '')
if len(CHANNEL_USERNAME) == 0:
    CHANNEL_USERNAME = "WeebZone_updates"

FSUB_CHANNEL_ID = environ.get('FSUB_CHANNEL_ID', '')
if len(FSUB_CHANNEL_ID) == 0:
    FSUB_CHANNEL_ID = '-1001512307861'

IMAGE_URL = environ.get('IMAGE_URL', '')
if len(IMAGE_URL) == 0:
    IMAGE_URL = 'https://graph.org/file/6b22ef7b8a733c5131d3f.jpg'

TIMEZONE = environ.get('TIMEZONE', '')
if len(TIMEZONE) == 0:
    TIMEZONE = 'Asia/Kolkata'

PIXABAY_API_KEY = environ.get('PIXABAY_API_KEY', '')
if len(PIXABAY_API_KEY) == 0:
    PIXABAY_API_KEY = None

PIXABAY_CATEGORY = environ.get('PIXABAY_CATEGORY', '')
if len(PIXABAY_CATEGORY) == 0:
    PIXABAY_CATEGORY = None

PIXABAY_SEARCH = environ.get('PIXABAY_SEARCH', '')
if len(PIXABAY_SEARCH) == 0:
    PIXABAY_SEARCH = None

WALLFLARE_SEARCH = environ.get('WALLFLARE_SEARCH', '')
if len(WALLFLARE_SEARCH) == 0:
    WALLFLARE_SEARCH = None

WALLTIP_SEARCH = environ.get('WALLTIP_SEARCH', '')
if len(WALLTIP_SEARCH) == 0:
    WALLTIP_SEARCH = None

WALLCRAFT_CATEGORY = environ.get('WALLCRAFT_CATEGORY', '')
if len(WALLCRAFT_CATEGORY) == 0:
    WALLCRAFT_CATEGORY = None

PICS = (environ.get('PICS', '')).split()

TOKEN_PICKLE_URL = environ.get('TOKEN_PICKLE_URL', '')
if len(TOKEN_PICKLE_URL) != 0:
    try:
        res = rget(TOKEN_PICKLE_URL)
        if res.status_code == 200:
            with open('token.pickle', 'wb+') as f:
                f.write(res.content)
        else:
            log_error(f"Failed to download token.pickle, link got HTTP response: {res.status_code}")
    except Exception as e:
        log_error(f"TOKEN_PICKLE_URL: {e}")

ACCOUNTS_ZIP_URL = environ.get('ACCOUNTS_ZIP_URL', '')
if len(ACCOUNTS_ZIP_URL) != 0:
    try:
        res = rget(ACCOUNTS_ZIP_URL)
        if res.status_code == 200:
            with open('accounts.zip', 'wb+') as f:
                f.write(res.content)
            srun(["unzip", "-q", "-o", "accounts.zip"])
            srun(["chmod", "-R", "777", "accounts"])
            osremove("accounts.zip")
        else:
            log_error(f"Failed to download accounts.zip, link got HTTP response: {res.status_code}")
    except Exception as e:
        log_error(f"ACCOUNTS_ZIP_URL: {e}")

MULTI_SEARCH_URL = environ.get('MULTI_SEARCH_URL', '')
if len(MULTI_SEARCH_URL) != 0:
    try:
        res = rget(MULTI_SEARCH_URL)
        if res.status_code == 200:
            with open('drive_folder', 'wb+') as f:
                f.write(res.content)
        else:
            log_error(f"Failed to download drive_folder, link got HTTP response: {res.status_code}")
    except Exception as e:
        log_error(f"MULTI_SEARCH_URL: {e}")

YT_COOKIES_URL = environ.get('YT_COOKIES_URL', '')
if len(YT_COOKIES_URL) != 0:
    try:
        res = rget(YT_COOKIES_URL)
        if res.status_code == 200:
            with open('cookies.txt', 'wb+') as f:
                f.write(res.content)
        else:
            log_error(f"Failed to download cookies.txt, link got HTTP response: {res.status_code}")
    except Exception as e:
        log_error(f"YT_COOKIES_URL: {e}")


DRIVES_NAMES.append("Main")
DRIVES_IDS.append(PARENT_ID)
if ospath.exists('drive_folder'):
    with open('drive_folder', 'r+') as f:
        lines = f.readlines()
        for line in lines:
            temp = line.strip().split()
            DRIVES_IDS.append(temp[1])
            DRIVES_NAMES.append(temp[0].replace("_", " "))
            if len(temp) > 2:
                INDEX_URLS.append(temp[2])
            else:
                INDEX_URLS.append(None)

updater = tgUpdater(token=BOT_TOKEN, request_kwargs={'read_timeout': 20, 'connect_timeout': 15})
bot = updater.bot
dispatcher = updater.dispatcher
job_queue = updater.job_queue
botname = bot.username
