from PIL import Image
from logging import getLogger, FileHandler, StreamHandler, INFO, basicConfig, error as log_error, info as log_info, warning as log_warning
from socket import setdefaulttimeout
from urllib.request import urlretrieve
from faulthandler import enable as faulthandler_enable
from telegram.ext import Updater as tgUpdater
from qbittorrentapi import Client as qbClient
from aria2p import API as ariaAPI, Client as ariaClient
from os import remove as osremove, path as ospath, getenv, mkdir
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

TIME_GAP_STORE = {}

load_dotenv('config.env', override=True)

NETRC_URL = getenv('NETRC_URL', '')
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

SERVER_PORT = getenv('SERVER_PORT', '')
if len(SERVER_PORT) == 0:
    SERVER_PORT = 80

BASE_URL = getenv('BASE_URL_OF_BOT', '').rstrip("/")
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
    if bool(getenv('_____REMOVE_THIS_LINE_____')):
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


BOT_TOKEN = getenv('BOT_TOKEN', '')
if len(BOT_TOKEN) == 0:
    log_error("BOT_TOKEN variable is missing! Exiting now")
    exit(1)

OWNER_ID = getenv('OWNER_ID', '')
if len(OWNER_ID) == 0:
    log_error("OWNER_ID variable is missing! Exiting now")
    exit(1)
else:
    OWNER_ID = int(OWNER_ID)


TELEGRAM_API = getenv('TELEGRAM_API', '')
if len(TELEGRAM_API) == 0:
    log_error("TELEGRAM_API variable is missing! Exiting now")
    exit(1)
else:
    TELEGRAM_API = int(TELEGRAM_API)

TELEGRAM_HASH = getenv('TELEGRAM_HASH', '')
if len(TELEGRAM_HASH) == 0:
    log_error("TELEGRAM_HASH variable is missing! Exiting now")
    exit(1)

PARENT_ID = getenv('GDRIVE_FOLDER_ID', '')
if len(PARENT_ID) == 0:
    PARENT_ID = None

DOWNLOAD_DIR = getenv('DOWNLOAD_DIR', '')
if len(DOWNLOAD_DIR) == 0:
    DOWNLOAD_DIR = '/usr/src/app/downloads/'
elif not DOWNLOAD_DIR.endswith("/"):
    DOWNLOAD_DIR = DOWNLOAD_DIR + '/'

DOWNLOAD_STATUS_UPDATE_INTERVAL = getenv('DOWNLOAD_STATUS_UPDATE_INTERVAL', '')
if len(DOWNLOAD_STATUS_UPDATE_INTERVAL) == 0:
    DOWNLOAD_STATUS_UPDATE_INTERVAL = 10
else:
    DOWNLOAD_STATUS_UPDATE_INTERVAL = int(DOWNLOAD_STATUS_UPDATE_INTERVAL)

AUTO_DELETE_MESSAGE_DURATION = getenv('AUTO_DELETE_MESSAGE_DURATION', '')
if len(AUTO_DELETE_MESSAGE_DURATION) == 0:
    AUTO_DELETE_MESSAGE_DURATION = 30
else:
    AUTO_DELETE_MESSAGE_DURATION = int(AUTO_DELETE_MESSAGE_DURATION)

AUTO_DELETE_UPLOAD_MESSAGE_DURATION = getenv('AUTO_DELETE_UPLOAD_MESSAGE_DURATION', '')
if len(AUTO_DELETE_UPLOAD_MESSAGE_DURATION) == 0:
    AUTO_DELETE_UPLOAD_MESSAGE_DURATION = -1
else:
    AUTO_DELETE_UPLOAD_MESSAGE_DURATION = int(AUTO_DELETE_UPLOAD_MESSAGE_DURATION)


TGH_THUMB = getenv('TGH_THUMB')
if len(TGH_THUMB) == 0:
    TGH_THUMB = 'https://te.legra.ph/file/3325f4053e8d68eab07b5.jpg'

path = "Thumbnails/"
if not ospath.isdir(path):
    mkdir(path)
photo_dir = path + TGH_THUMB.split('/')[-1]
urlretrieve(TGH_THUMB, photo_dir)
Image.open(photo_dir).convert("RGB").save('Thumbnails/weeb.jpg', "JPEG")
osremove(photo_dir)

aid = getenv('AUTHORIZED_CHATS', '')
if len(aid) != 0:
    aid = aid.split()
    for id_ in aid:
        user_data[int(id_.strip())] = {'is_auth': True}

aid = getenv('SUDO_USERS', '')
if len(aid) != 0:
    aid = aid.split()
    for id_ in aid:
        user_data[int(id_.strip())] = {'is_sudo': True}

aid = getenv('PAID_USERS', '')
if len(aid) != 0:
    aid = aid.split()
    for id_ in aid:
        user_data[int(id_.strip())] = {'is_paid': True}

aid = getenv('LOG_LEECH', '')
if len(aid) != 0:
    aid = aid.split(' ')
    user_data['is_log_leech'] = [int(id_.strip()) for id_ in aid]

aid = getenv('LEECH_LOG', '')
if len(aid) != 0:
    aid = aid.split(' ')
    user_data['is_leech_log'] = [int(id_.strip()) for id_ in aid]

aid = getenv('MIRROR_LOGS', '')
if len(aid) != 0:
    aid = aid.split(' ')
    user_data['mirror_logs'] = [int(id_.strip()) for id_ in aid]

aid = getenv('LINK_LOGS', '')
if len(aid) != 0:
    aid = aid.split(' ')
    user_data['link_logs'] = [int(id_.strip()) for id_ in aid]

fx = getenv('EXTENSION_FILTER', '')
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

MEGA_API_KEY = getenv('MEGA_API_KEY', '')
if len(MEGA_API_KEY) == 0:
    log_warning('MEGA API KEY not provided!')
    MEGA_API_KEY = None

MEGA_EMAIL_ID = getenv('MEGA_EMAIL_ID', '')
MEGA_PASSWORD = getenv('MEGA_PASSWORD', '')
if len(MEGA_EMAIL_ID) == 0 or len(MEGA_PASSWORD) == 0:
    log_warning('MEGA Credentials not provided!')
    MEGA_EMAIL_ID = None
    MEGA_PASSWORD = None

DB_URI = getenv('DATABASE_URL', '')
if len(DB_URI) == 0:
    DB_URI = None

tgBotMaxFileSize = 2097151000

TG_SPLIT_SIZE = getenv('TG_SPLIT_SIZE', '')
if len(TG_SPLIT_SIZE) == 0 or int(TG_SPLIT_SIZE) > tgBotMaxFileSize:
    TG_SPLIT_SIZE = tgBotMaxFileSize

try:
    USER_SESSION_STRING = getenv('USER_SESSION_STRING', '')
    if len(USER_SESSION_STRING) != 0:
        premium_session = Client('WZML-Premium', api_id=TELEGRAM_API, api_hash=TELEGRAM_HASH, session_string=USER_SESSION_STRING, parse_mode=enums.ParseMode.HTML, no_updates=True)
    if not premium_session:
        LOGGER.error("Cannot initialized User Session. Please regenerate USER_SESSION_STRING")
    else:
        premium_session.start()
        if (premium_session.get_me()).is_premium:
            if not LEECH_LOG:
                LOGGER.error("You must set LEECH_LOG for uploads. Exiting Now...")
                try: premium_session.send_message(OWNER_ID, "You must set LEECH_LOG for uploads, Exiting Now...")
                except Exception as e: LOGGER.exception(e)
                premium_session.stop()
                app.stop()
                exit(1)
            TG_SPLIT_SIZE = 4194304000
            LOGGER.info("Telegram Premium detected! Leech Limit upgraded to 4GB")
        elif (not DB_URI) or (not RSS_CHAT_ID):
            premium_session.stop()
            LOGGER.info(f"Not using rss. if you want to use fill RSS_CHAT_ID and DB_URI variables.")
except:
    USER_SESSION_STRING = None
    premium_session = None
LOGGER.info(f"TG_SPLIT_SIZE: {TG_SPLIT_SIZE}")

STATUS_LIMIT = getenv('STATUS_LIMIT', '')
STATUS_LIMIT = None if len(STATUS_LIMIT) == 0 else int(STATUS_LIMIT)

UPTOBOX_TOKEN = getenv('UPTOBOX_TOKEN', '')
if len(UPTOBOX_TOKEN) == 0:
    UPTOBOX_TOKEN = None

INDEX_URL = getenv('INDEX_URL', '').rstrip("/")
if len(INDEX_URL) == 0:
    INDEX_URL = None
    INDEX_URLS.append(None)
else:
    INDEX_URLS.append(INDEX_URL)

SEARCH_API_LINK = getenv('SEARCH_API_LINK', '').rstrip("/")
if len(SEARCH_API_LINK) == 0:
    SEARCH_API_LINK = None

SEARCH_LIMIT = getenv('SEARCH_LIMIT', '')
SEARCH_LIMIT = 0 if len(SEARCH_LIMIT) == 0 else int(SEARCH_LIMIT)

CMD_INDEX = getenv('CMD_INDEX', '')


TORRENT_TIMEOUT = getenv('TORRENT_TIMEOUT', '')
TORRENT_TIMEOUT = None if len(TORRENT_TIMEOUT) == 0 else int(TORRENT_TIMEOUT)

TORRENT_DIRECT_LIMIT = getenv('TORRENT_DIRECT_LIMIT', '')
TORRENT_DIRECT_LIMIT = None if len(TORRENT_DIRECT_LIMIT) == 0 else float(TORRENT_DIRECT_LIMIT)

CLONE_LIMIT = getenv('CLONE_LIMIT', '')
CLONE_LIMIT = None if len(CLONE_LIMIT) == 0 else float(CLONE_LIMIT)

LEECH_LIMIT = getenv('LEECH_LIMIT', '')
LEECH_LIMIT = None if len(LEECH_LIMIT) == 0 else float(LEECH_LIMIT)

MEGA_LIMIT = getenv('MEGA_LIMIT', '')
MEGA_LIMIT = None if len(MEGA_LIMIT) == 0 else float(MEGA_LIMIT)

STORAGE_THRESHOLD = getenv('STORAGE_THRESHOLD', '')
STORAGE_THRESHOLD = None if len(STORAGE_THRESHOLD) == 0 else float(STORAGE_THRESHOLD)

ZIP_UNZIP_LIMIT = getenv('ZIP_UNZIP_LIMIT', '')
ZIP_UNZIP_LIMIT = None if len(ZIP_UNZIP_LIMIT) == 0 else float(ZIP_UNZIP_LIMIT)

TOTAL_TASKS_LIMIT = getenv('TOTAL_TASKS_LIMIT', '')
TOTAL_TASKS_LIMIT = None if len(TOTAL_TASKS_LIMIT) == 0 else int(TOTAL_TASKS_LIMIT)

USER_TASKS_LIMIT = getenv('USER_TASKS_LIMIT', '')
USER_TASKS_LIMIT = None if len(USER_TASKS_LIMIT) == 0 else int(USER_TASKS_LIMIT)


RSS_USER_SESSION_STRING = getenv('RSS_USER_SESSION_STRING', '')
rss_session = Client(name='rss_session', api_id=(TELEGRAM_API), api_hash=TELEGRAM_HASH, session_string=RSS_USER_SESSION_STRING, parse_mode=enums.ParseMode.HTML, no_updates=True) if len(RSS_USER_SESSION_STRING) != 0 else None

RSS_COMMAND = getenv('RSS_COMMAND', '')
if len(RSS_COMMAND) == 0:
    RSS_COMMAND = None

RSS_CHAT_ID = getenv('RSS_CHAT_ID', '')
RSS_CHAT_ID = None if len(RSS_CHAT_ID) == 0 else int(RSS_CHAT_ID)

RSS_DELAY = getenv('RSS_DELAY', '')
RSS_DELAY = 900 if len(RSS_DELAY) == 0 else int(RSS_DELAY)

SEARCH_PLUGINS = getenv('SEARCH_PLUGINS', '')
if len(SEARCH_PLUGINS) == 0:
    SEARCH_PLUGINS = None
else:
    SEARCH_PLUGINS = jsonloads(SEARCH_PLUGINS)

INCOMPLETE_TASK_NOTIFIER = getenv('INCOMPLETE_TASK_NOTIFIER', '')
INCOMPLETE_TASK_NOTIFIER = INCOMPLETE_TASK_NOTIFIER.lower() == 'true'

STOP_DUPLICATE = getenv('STOP_DUPLICATE', '')
STOP_DUPLICATE = STOP_DUPLICATE.lower() == 'true'

VIEW_LINK = getenv('VIEW_LINK', '')
VIEW_LINK = VIEW_LINK.lower() == 'true'

SET_BOT_COMMANDS = getenv('SET_BOT_COMMANDS', '')
SET_BOT_COMMANDS = SET_BOT_COMMANDS.lower() == 'true'

IS_TEAM_DRIVE = getenv('IS_TEAM_DRIVE', '')
IS_TEAM_DRIVE = IS_TEAM_DRIVE.lower() == 'true'

USE_SERVICE_ACCOUNTS = getenv('USE_SERVICE_ACCOUNTS', '')
USE_SERVICE_ACCOUNTS = USE_SERVICE_ACCOUNTS.lower() == 'true'

WEB_PINCODE = getenv('WEB_PINCODE', '')
WEB_PINCODE = WEB_PINCODE.lower() == 'true'

IGNORE_PENDING_REQUESTS = getenv('IGNORE_PENDING_REQUESTS', '')
IGNORE_PENDING_REQUESTS = IGNORE_PENDING_REQUESTS.lower() == 'true'

AS_DOCUMENT = getenv('AS_DOCUMENT', '')
AS_DOCUMENT = AS_DOCUMENT.lower() == 'true'

EQUAL_SPLITS = getenv('EQUAL_SPLITS', '')
EQUAL_SPLITS = EQUAL_SPLITS.lower() == 'true'

MIRROR_ENABLED = getenv('MIRROR_ENABLED', '')
MIRROR_ENABLED = MIRROR_ENABLED.lower() == 'true'

LEECH_ENABLED = getenv('LEECH_ENABLED', '')
LEECH_ENABLED = LEECH_ENABLED.lower() == 'true'

WATCH_ENABLED = getenv('WATCH_ENABLED', '')
WATCH_ENABLED = WATCH_ENABLED.lower() == 'true'

CLONE_ENABLED = getenv('CLONE_ENABLED', '')
CLONE_ENABLED = CLONE_ENABLED.lower() == 'true'

ANILIST_ENABLED = getenv('ANILIST_ENABLED', '')
ANILIST_ENABLED = ANILIST_ENABLED.lower() == 'true'

WAYBACK_ENABLED = getenv('WAYBACK_ENABLED', '')
WAYBACK_ENABLED = WAYBACK_ENABLED.lower() == 'true'

MEDIAINFO_ENABLED = getenv('MEDIAINFO_ENABLED', '')
MEDIAINFO_ENABLED = MEDIAINFO_ENABLED.lower() == 'true'

TELEGRAPH_STYLE = getenv('TELEGRAPH_STYLE', '')
TELEGRAPH_STYLE = TELEGRAPH_STYLE.lower() == 'true'

EMOJI_THEME = getenv('EMOJI_THEME', '')
EMOJI_THEME = EMOJI_THEME.lower() == 'true'

DISABLE_DRIVE_LINK = getenv('DISABLE_DRIVE_LINK', '')
DISABLE_DRIVE_LINK = DISABLE_DRIVE_LINK.lower() == 'true'

LEECH_LOG_INDEXING = getenv('LEECH_LOG_INDEXING', '')
LEECH_LOG_INDEXING = LEECH_LOG_INDEXING.lower() == 'true'

BOT_PM = getenv('BOT_PM', '')
BOT_PM = BOT_PM.lower() == 'true'

FORCE_BOT_PM = getenv('FORCE_BOT_PM', '')
FORCE_BOT_PM = FORCE_BOT_PM.lower() == 'true'

SOURCE_LINK = getenv('SOURCE_LINK', '')
SOURCE_LINK = SOURCE_LINK.lower() == 'true'

FSUB = getenv('FSUB', '')
FSUB = FSUB.lower() == 'true'

PAID_SERVICE = getenv('PAID_SERVICE', '')
PAID_SERVICE = PAID_SERVICE.lower() == 'true'

SHOW_LIMITS_IN_STATS = getenv('SHOW_LIMITS_IN_STATS', '')
SHOW_LIMITS_IN_STATS = SHOW_LIMITS_IN_STATS.lower() == 'true'

START_BTN1_NAME = getenv('START_BTN1_NAME', '')
START_BTN1_URL = getenv('START_BTN1_URL', '')
if len(START_BTN1_NAME) == 0 or len(START_BTN1_URL) == 0:
    START_BTN1_NAME = 'Master'
    START_BTN1_URL = 'https://t.me/krn_adhikari'

START_BTN2_NAME = getenv('START_BTN2_NAME', '')
START_BTN2_URL = getenv('START_BTN2_URL', '')
if len(START_BTN2_NAME) == 0 or len(START_BTN2_URL) == 0:
    START_BTN2_NAME = 'Support Group'
    START_BTN2_URL = 'https://t.me/WeebZone_updates'

BUTTON_FOUR_NAME = getenv('BUTTON_FOUR_NAME', '')
BUTTON_FOUR_URL = getenv('BUTTON_FOUR_URL', '')
if len(BUTTON_FOUR_NAME) == 0 or len(BUTTON_FOUR_URL) == 0:
    BUTTON_FOUR_NAME = None
    BUTTON_FOUR_URL = None

BUTTON_FIVE_NAME = getenv('BUTTON_FIVE_NAME', '')
BUTTON_FIVE_URL = getenv('BUTTON_FIVE_URL', '')
if len(BUTTON_FIVE_NAME) == 0 or len(BUTTON_FIVE_URL) == 0:
    BUTTON_FIVE_NAME = None
    BUTTON_FIVE_URL = None

BUTTON_SIX_NAME = getenv('BUTTON_SIX_NAME', '')
BUTTON_SIX_URL = getenv('BUTTON_SIX_URL', '')
if len(BUTTON_SIX_NAME) == 0 or len(BUTTON_SIX_URL) == 0:
    BUTTON_SIX_NAME = None
    BUTTON_SIX_URL = None

SHORTENER = getenv('SHORTENER', '')
SHORTENER_API = getenv('SHORTENER_API', '')
if len(SHORTENER) == 0 or len(SHORTENER_API) == 0:
    SHORTENER = None
    SHORTENER_API = None

CRYPT = getenv('CRYPT', '')
if len(CRYPT) == 0:
    CRYPT = None

UNIFIED_EMAIL = getenv('UNIFIED_EMAIL', '')
if len(UNIFIED_EMAIL) == 0:
    UNIFIED_EMAIL = None

UNIFIED_PASS = getenv('UNIFIED_PASS', '')
if len(UNIFIED_PASS) == 0:
    UNIFIED_PASS = None

HUBDRIVE_CRYPT = getenv('HUBDRIVE_CRYPT', '')
if len(HUBDRIVE_CRYPT) == 0:
    HUBDRIVE_CRYPT = None

KATDRIVE_CRYPT = getenv('KATDRIVE_CRYPT', '')
if len(KATDRIVE_CRYPT) == 0:
    KATDRIVE_CRYPT = None

DRIVEFIRE_CRYPT = getenv('DRIVEFIRE_CRYPT', '')
if len(DRIVEFIRE_CRYPT) == 0:
    DRIVEFIRE_CRYPT = None

MIRROR_LOG_URL = getenv('MIRROR_LOG_URL', '')
if len(MIRROR_LOG_URL) == 0:
    MIRROR_LOG_URL = None

LEECH_LOG_URL = getenv('LEECH_LOG_URL', '')
if len(LEECH_LOG_URL) == 0:
    LEECH_LOG_URL = None

TIME_GAP = getenv('TIME_GAP', '')
if len(TIME_GAP) == 0:
    TIME_GAP = -1

AUTHOR_NAME = getenv('AUTHOR_NAME', '')
if len(AUTHOR_NAME) == 0:
    AUTHOR_NAME = 'WZML'

AUTHOR_URL = getenv('AUTHOR_URL', '')
if len(AUTHOR_URL) == 0:
    AUTHOR_URL = 'https://t.me/WeebZone_updates'

TITLE_NAME = getenv('TITLE_NAME', '')
if len(TITLE_NAME) == 0:
    TITLE_NAME = 'WeebZone'

GD_INFO = getenv('GD_INFO', '')
if len(GD_INFO) == 0:
    GD_INFO = 'Uploaded by WeebZone Mirror Bot'

CREDIT_NAME = getenv('CREDIT_NAME', '')
if len(CREDIT_NAME) == 0:
    CREDIT_NAME = 'WeebZone'

NAME_FONT = getenv('NAME_FONT', '')
if len(NAME_FONT) == 0:
    NAME_FONT = 'code'

CAPTION_FONT = getenv('CAPTION_FONT', '')
if len(CAPTION_FONT) == 0:
    CAPTION_FONT = 'code'

FINISHED_PROGRESS_STR = getenv('FINISHED_PROGRESS_STR', '')
UN_FINISHED_PROGRESS_STR = getenv('UN_FINISHED_PROGRESS_STR', '')
if len(FINISHED_PROGRESS_STR) == 0 or len(FINISHED_PROGRESS_STR) == 0:
    FINISHED_PROGRESS_STR = '●' # '■'
    UN_FINISHED_PROGRESS_STR = '○' # '□'

CHANNEL_USERNAME = getenv('CHANNEL_USERNAME', '')
if len(CHANNEL_USERNAME) == 0:
    CHANNEL_USERNAME = "WeebZone_updates"

FSUB_CHANNEL_ID = getenv('FSUB_CHANNEL_ID', '')
if len(FSUB_CHANNEL_ID) == 0:
    FSUB_CHANNEL_ID = '-1001512307861'

IMAGE_URL = getenv('IMAGE_URL', '')
if len(IMAGE_URL) == 0:
    IMAGE_URL = 'https://graph.org/file/6b22ef7b8a733c5131d3f.jpg'

TIMEZONE = getenv('TIMEZONE', '')
if len(TIMEZONE) == 0:
    TIMEZONE = 'Asia/Kolkata'

PIXABAY_API_KEY = getenv('PIXABAY_API_KEY', '')
if len(PIXABAY_API_KEY) == 0:
    PIXABAY_API_KEY = None

PIXABAY_CATEGORY = getenv('PIXABAY_CATEGORY', '')
if len(PIXABAY_CATEGORY) == 0:
    PIXABAY_CATEGORY = None

PIXABAY_SEARCH = getenv('PIXABAY_SEARCH', '')
if len(PIXABAY_SEARCH) == 0:
    PIXABAY_SEARCH = None

WALLFLARE_SEARCH = getenv('WALLFLARE_SEARCH', '')
if len(WALLFLARE_SEARCH) == 0:
    WALLFLARE_SEARCH = None

WALLTIP_SEARCH = getenv('WALLTIP_SEARCH', '')
if len(WALLTIP_SEARCH) == 0:
    WALLTIP_SEARCH = None

WALLCRAFT_CATEGORY = getenv('WALLCRAFT_CATEGORY', '')
if len(WALLCRAFT_CATEGORY) == 0:
    WALLCRAFT_CATEGORY = None

PICS = (getenv('PICS', '')).split()

TOKEN_PICKLE_URL = getenv('TOKEN_PICKLE_URL', '')
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

ACCOUNTS_ZIP_URL = getenv('ACCOUNTS_ZIP_URL', '')
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

MULTI_SEARCH_URL = getenv('MULTI_SEARCH_URL', '')
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

YT_COOKIES_URL = getenv('YT_COOKIES_URL', '')
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
