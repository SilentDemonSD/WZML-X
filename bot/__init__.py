from PIL import Image
from logging import getLogger, FileHandler, StreamHandler, INFO, basicConfig, error as log_error, info as log_info, warning as log_warning
from socket import setdefaulttimeout
from urllib.request import urlretrieve
from faulthandler import enable as faulthandler_enable
from telegram.ext import Updater as tgUpdater
from qbittorrentapi import Client as qbClient
from aria2p import API as ariaAPI, Client as ariaClient
from os import remove as osremove, path as ospath, environ, mkdir
from requests import get as rget
from subprocess import Popen, run as srun, check_output
from time import sleep, time
from threading import Thread, Lock
from dotenv import load_dotenv
from pyrogram import Client, enums
from asyncio import get_event_loop
from pymongo import MongoClient

main_loop = get_event_loop()

faulthandler_enable()

setdefaulttimeout(600)

botStartTime = time()

basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    handlers=[FileHandler('log.txt'), StreamHandler()],
                    level=INFO)

LOGGER = getLogger(__name__)

load_dotenv('config.env', override=True)

Interval = []
QbInterval = []
DRIVES_NAMES = []
DRIVES_IDS = []
INDEX_URLS = []
user_data = {}
aria2_options = {}
qbit_options = {}
TIME_GAP_STORE = {}
GLOBAL_EXTENSION_FILTER = ['.aria2']

try:
    if bool(environ.get('_____REMOVE_THIS_LINE_____')):
        log_error('The README.md file there to be read! Exiting now!')
        exit()
except:
    pass

download_dict_lock = Lock()
status_reply_dict_lock = Lock()
# Key: update.effective_chat.id
# Value: telegram.Message
status_reply_dict = {}
# Key: update.message.message_id
# Value: An object of Status
download_dict = {}
# key: rss_title
# value: {link, last_feed, last_title, filter}
rss_dict = {}


BOT_TOKEN = environ.get('BOT_TOKEN', '')
if len(BOT_TOKEN) == 0:
    log_error("BOT_TOKEN variable is missing! Exiting now")
    exit(1)

bot_id = int(BOT_TOKEN.split(':', 1)[0])

DATABASE_URL = environ.get('DATABASE_URL', '')
if len(DATABASE_URL) == 0:
    DATABASE_URL = ''

if DATABASE_URL:
    conn = MongoClient(DATABASE_URL)
    db = conn.mltb
    if config_dict := db.settings.config.find_one({'_id': bot_id}):  #retrun config dict (all env vars)
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
    bot_id = int(BOT_TOKEN.split(':', 1)[0])
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

DOWNLOAD_DIR = environ.get('DOWNLOAD_DIR', '')
if len(DOWNLOAD_DIR) == 0:
    DOWNLOAD_DIR = '/usr/src/app/downloads/'
elif not DOWNLOAD_DIR.endswith("/"):
    DOWNLOAD_DIR = f'{DOWNLOAD_DIR}/'


TGH_THUMB = environ.get('TGH_THUMB', '')
if len(TGH_THUMB) == 0:
    TGH_THUMB = 'https://te.legra.ph/file/3325f4053e8d68eab07b5.jpg'

path = "Thumbnails/"
if not ospath.isdir(path):
    mkdir(path)
photo_dir = path + TGH_THUMB.split('/')[-1]
urlretrieve(TGH_THUMB, photo_dir)
Image.open(photo_dir).convert("RGB").save('Thumbnails/weeb.jpg', "JPEG")
osremove(photo_dir)

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

PAID_USERS = environ.get('PAID_USERS', '')
if len(PAID_USERS) != 0:
    aid = PAID_USERS.split()
    for id_ in aid:
        user_data[int(id_.strip())] = {'is_paid': True}

LOG_LEECH = environ.get('LOG_LEECH', '')
if len(LOG_LEECH) != 0:
    aid = LOG_LEECH.split(' ')
    user_data['is_log_leech'] = [int(id_.strip()) for id_ in aid]

LEECH_LOG = environ.get('LEECH_LOG', '')
if len(LEECH_LOG) != 0:
    aid = LEECH_LOG.split(' ')
    user_data['is_leech_log'] = [int(id_.strip()) for id_ in aid]

MIRROR_LOGS = environ.get('MIRROR_LOGS', '')
if len(MIRROR_LOGS) != 0:
    aid = MIRROR_LOGS.split(' ')
    user_data['mirror_logs'] = [int(id_.strip()) for id_ in aid]

LINK_LOGS = environ.get('LINK_LOGS', '')
if len(LINK_LOGS) != 0:
    aid = LINK_LOGS.split(' ')
    user_data['link_logs'] = [int(id_.strip()) for id_ in aid]

EXTENSION_FILTER = environ.get('EXTENSION_FILTER', '')
if len(EXTENSION_FILTER) > 0:
    fx = EXTENSION_FILTER.split()
    for x in fx:
        GLOBAL_EXTENSION_FILTER.append(x.strip().lower())

DEF_ANI_TEMP  = environ.get('ANIME_TEMPLATE', '')
if len(DEF_ANI_TEMP) == 0:
    DEF_ANI_TEMP = '''<b>{ro_title}</b>({na_title})
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

LIST_ITEMS  = environ.get('LIST_ITEMS', '')
if len(LIST_ITEMS) == 0:
    LIST_ITEMS = 4
else: LIST_ITEMS = int(LIST_ITEMS)

DEF_IMDB_TEMP  = environ.get('IMDB_TEMPLATE', '')
if len(DEF_IMDB_TEMP) == 0:
    DEF_IMDB_TEMP = '''<b>Title: </b> {title} [{year}]
<b>Also Known As:</b> {aka}
<b>Rating ⭐️:</b> <i>{rating}</i>
<b>Release Info: </b> <a href="{url_releaseinfo}">{release_date}</a>
<b>Genre: </b>{genres}
<b>IMDb URL:</b> {url}
<b>Language: </b>{languages}
<b>Country of Origin : </b> {countries}

<b>Story Line: </b><code>{plot}</code>

<a href="{url_cast}">Read More ...</a>'''

LOGGER.info("Generating SESSION_STRING")
app = Client(name='pyrogram', api_id=(TELEGRAM_API), api_hash=TELEGRAM_HASH, bot_token=BOT_TOKEN, parse_mode=enums.ParseMode.HTML, no_updates=True)

MEGA_API_KEY = environ.get('MEGA_API_KEY', '')
if len(MEGA_API_KEY) == 0:
    log_warning('MEGA API KEY not provided!')
    MEGA_API_KEY = ''

MEGA_EMAIL_ID = environ.get('MEGA_EMAIL_ID', '')
MEGA_PASSWORD = environ.get('MEGA_PASSWORD', '')
if len(MEGA_EMAIL_ID) == 0 or len(MEGA_PASSWORD) == 0:
    log_warning('MEGA Credentials not provided!')
    MEGA_EMAIL_ID = ''
    MEGA_PASSWORD = ''

tgBotMaxFileSize = 2097151000

TG_SPLIT_SIZE = environ.get('TG_SPLIT_SIZE', '')
if len(TG_SPLIT_SIZE) == 0 or int(TG_SPLIT_SIZE) > tgBotMaxFileSize:
    TG_SPLIT_SIZE = tgBotMaxFileSize
else:
    TG_SPLIT_SIZE = int(TG_SPLIT_SIZE)

try:
    USER_SESSION_STRING = environ.get('USER_SESSION_STRING', '')
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
            LOGGER.info("Telegram Premium Detected! Leech Limit upgraded to 4GB")
        elif (not DATABASE_URL) or (not RSS_CHAT_ID):
            premium_session.stop()
            LOGGER.info(f"Not using rss. if you want to use fill RSS_CHAT_ID and DATABASE_URL variables.")
except:
    USER_SESSION_STRING = ''
    premium_session = ''
LOGGER.info(f"TG_SPLIT_SIZE: {TG_SPLIT_SIZE}")

STATUS_LIMIT = environ.get('STATUS_LIMIT', '')
STATUS_LIMIT = '' if len(STATUS_LIMIT) == 0 else int(STATUS_LIMIT)

UPTOBOX_TOKEN = environ.get('UPTOBOX_TOKEN', '')
if len(UPTOBOX_TOKEN) == 0:
    UPTOBOX_TOKEN = ''

INDEX_URL = environ.get('INDEX_URL', '').rstrip("/")
if len(INDEX_URL) == 0:
    INDEX_URL = ''

SEARCH_API_LINK = environ.get('SEARCH_API_LINK', '').rstrip("/")
if len(SEARCH_API_LINK) == 0:
    SEARCH_API_LINK = ''

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

AUTO_DELETE_UPLOAD_MESSAGE_DURATION = environ.get('AUTO_DELETE_UPLOAD_MESSAGE_DURATION', '')
if len(AUTO_DELETE_UPLOAD_MESSAGE_DURATION) == 0:
    AUTO_DELETE_UPLOAD_MESSAGE_DURATION = -1
else:
    AUTO_DELETE_UPLOAD_MESSAGE_DURATION = int(AUTO_DELETE_UPLOAD_MESSAGE_DURATION)

SEARCH_LIMIT = environ.get('SEARCH_LIMIT', '')
SEARCH_LIMIT = 0 if len(SEARCH_LIMIT) == 0 else int(SEARCH_LIMIT)

CMD_PERFIX = environ.get('CMD_PERFIX', '')

TORRENT_TIMEOUT = environ.get('TORRENT_TIMEOUT', '')
TORRENT_TIMEOUT = '' if len(TORRENT_TIMEOUT) == 0 else int(TORRENT_TIMEOUT)

TORRENT_DIRECT_LIMIT = environ.get('TORRENT_DIRECT_LIMIT', '')
TORRENT_DIRECT_LIMIT = '' if len(TORRENT_DIRECT_LIMIT) == 0 else float(TORRENT_DIRECT_LIMIT)

CLONE_LIMIT = environ.get('CLONE_LIMIT', '')
CLONE_LIMIT = '' if len(CLONE_LIMIT) == 0 else float(CLONE_LIMIT)

LEECH_LIMIT = environ.get('LEECH_LIMIT', '')
LEECH_LIMIT = '' if len(LEECH_LIMIT) == 0 else float(LEECH_LIMIT)

MEGA_LIMIT = environ.get('MEGA_LIMIT', '')
MEGA_LIMIT = '' if len(MEGA_LIMIT) == 0 else float(MEGA_LIMIT)

STORAGE_THRESHOLD = environ.get('STORAGE_THRESHOLD', '')
STORAGE_THRESHOLD = '' if len(STORAGE_THRESHOLD) == 0 else float(STORAGE_THRESHOLD)

ZIP_UNZIP_LIMIT = environ.get('ZIP_UNZIP_LIMIT', '')
ZIP_UNZIP_LIMIT = '' if len(ZIP_UNZIP_LIMIT) == 0 else float(ZIP_UNZIP_LIMIT)

TOTAL_TASKS_LIMIT = environ.get('TOTAL_TASKS_LIMIT', '')
TOTAL_TASKS_LIMIT = '' if len(TOTAL_TASKS_LIMIT) == 0 else int(TOTAL_TASKS_LIMIT)

USER_TASKS_LIMIT = environ.get('USER_TASKS_LIMIT', '')
USER_TASKS_LIMIT = '' if len(USER_TASKS_LIMIT) == 0 else int(USER_TASKS_LIMIT)


RSS_USER_SESSION_STRING = environ.get('RSS_USER_SESSION_STRING', '')
rss_session = Client(name='rss_session', api_id=(TELEGRAM_API), api_hash=TELEGRAM_HASH, session_string=RSS_USER_SESSION_STRING, parse_mode=enums.ParseMode.HTML, no_updates=True) if len(RSS_USER_SESSION_STRING) != 0 else None

RSS_COMMAND = environ.get('RSS_COMMAND', '')
if len(RSS_COMMAND) == 0:
    RSS_COMMAND = ''

RSS_CHAT_ID = environ.get('RSS_CHAT_ID', '')
RSS_CHAT_ID = '' if len(RSS_CHAT_ID) == 0 else int(RSS_CHAT_ID)

RSS_DELAY = environ.get('RSS_DELAY', '')
RSS_DELAY = 900 if len(RSS_DELAY) == 0 else int(RSS_DELAY)

SEARCH_PLUGINS = environ.get('SEARCH_PLUGINS', '')
if len(SEARCH_PLUGINS) == 0:
    SEARCH_PLUGINS = ''

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

USR_TD_DEFAULT = environ.get('USR_TD_DEFAULT', '')
USR_TD_DEFAULT = USR_TD_DEFAULT.lower() == 'false'

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

IMDB_ENABLED = environ.get('IMDB_ENABLED', '')
IMDB_ENABLED = IMDB_ENABLED.lower() == 'true'

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
    BUTTON_FOUR_NAME = ''
    BUTTON_FOUR_URL = ''

BUTTON_FIVE_NAME = environ.get('BUTTON_FIVE_NAME', '')
BUTTON_FIVE_URL = environ.get('BUTTON_FIVE_URL', '')
if len(BUTTON_FIVE_NAME) == 0 or len(BUTTON_FIVE_URL) == 0:
    BUTTON_FIVE_NAME = ''
    BUTTON_FIVE_URL = ''

BUTTON_SIX_NAME = environ.get('BUTTON_SIX_NAME', '')
BUTTON_SIX_URL = environ.get('BUTTON_SIX_URL', '')
if len(BUTTON_SIX_NAME) == 0 or len(BUTTON_SIX_URL) == 0:
    BUTTON_SIX_NAME = ''
    BUTTON_SIX_URL = ''

SHORTENER = environ.get('SHORTENER', '')
SHORTENER_API = environ.get('SHORTENER_API', '')
if len(SHORTENER) == 0 or len(SHORTENER_API) == 0:
    SHORTENER = ''
    SHORTENER_API = ''
SHORTENER = (SHORTENER.replace("'", '').replace('"', '').replace('[', '').replace(']', '').replace(",", "")).split()
SHORTENER_API = (SHORTENER_API.replace("'", '').replace('"', '').replace('[', '').replace(']', '').replace(",", "")).split()


UNIFIED_EMAIL = environ.get('UNIFIED_EMAIL', '')
if len(UNIFIED_EMAIL) == 0:
    UNIFIED_EMAIL = ''

UNIFIED_PASS = environ.get('UNIFIED_PASS', '')
if len(UNIFIED_PASS) == 0:
    UNIFIED_PASS = ''

GDTOT_CRYPT = environ.get('GDTOT_CRYPT', '')
if len(GDTOT_CRYPT) == 0:
    GDTOT_CRYPT = ''

HUBDRIVE_CRYPT = environ.get('HUBDRIVE_CRYPT', '')
if len(HUBDRIVE_CRYPT) == 0:
    HUBDRIVE_CRYPT = ''

KATDRIVE_CRYPT = environ.get('KATDRIVE_CRYPT', '')
if len(KATDRIVE_CRYPT) == 0:
    KATDRIVE_CRYPT = ''

DRIVEFIRE_CRYPT = environ.get('DRIVEFIRE_CRYPT', '')
if len(DRIVEFIRE_CRYPT) == 0:
    DRIVEFIRE_CRYPT = ''

SHAREDRIVE_PHPCKS = environ.get('SHAREDRIVE_PHPCKS', '')
if len(SHAREDRIVE_PHPCKS) == 0:
    SHAREDRIVE_PHPCKS = ''

XSRF_TOKEN = environ.get('XSRF_TOKEN', '')
if len(XSRF_TOKEN) == 0:
    XSRF_TOKEN = ''

laravel_session = environ.get('laravel_session', '')
if len(laravel_session) == 0:
    laravel_session = ''

MIRROR_LOG_URL = environ.get('MIRROR_LOG_URL', '')
if len(MIRROR_LOG_URL) == 0:
    MIRROR_LOG_URL = ''

LEECH_LOG_URL = environ.get('LEECH_LOG_URL', '')
if len(LEECH_LOG_URL) == 0:
    LEECH_LOG_URL = ''

TIME_GAP = environ.get('TIME_GAP', '')
if len(TIME_GAP) == 0:
    TIME_GAP = -1
else:
    TIME_GAP = int(TIME_GAP)

AUTHOR_NAME = environ.get('AUTHOR_NAME', '')
if len(AUTHOR_NAME) == 0:
    AUTHOR_NAME = 'WZML'

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
MULTI_WORKING_PROGRESS_STR = environ.get('MULTI_WORKING_PROGRESS_STR', '')
if len(FINISHED_PROGRESS_STR) == 0 or len(FINISHED_PROGRESS_STR) == 0 or len(MULTI_WORKING_PROGRESS_STR) == 0:
    FINISHED_PROGRESS_STR = '█' # '■'
    UN_FINISHED_PROGRESS_STR = '▒' # '□'
    MULTI_WORKING_PROGRESS_STR = '▁ ▂ ▃ ▄ ▅ ▆ ▇'
MULTI_WORKING_PROGRESS_STR = (MULTI_WORKING_PROGRESS_STR.replace("'", '').replace('"', '').replace('[', '').replace(']', '').replace(",", "")).split(' ')

if len(MULTI_WORKING_PROGRESS_STR) != 7:
    LOGGER.warning("Multi Progress doesn't contain 7 Symbols. Check Agian, Using Default for Now !")
    MULTI_WORKING_PROGRESS_STR = '▁ ▂ ▃ ▄ ▅ ▆ ▇'.split(' ')

CHANNEL_USERNAME = environ.get('CHANNEL_USERNAME', '')
if len(CHANNEL_USERNAME) == 0:
    CHANNEL_USERNAME = 'WeebZone_updates'

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
    PIXABAY_API_KEY = ''

PIXABAY_CATEGORY = environ.get('PIXABAY_CATEGORY', '')
if len(PIXABAY_CATEGORY) == 0:
    PIXABAY_CATEGORY = ''

PIXABAY_SEARCH = environ.get('PIXABAY_SEARCH', '')
if len(PIXABAY_SEARCH) == 0:
    PIXABAY_SEARCH = ''

WALLFLARE_SEARCH = environ.get('WALLFLARE_SEARCH', '')
if len(WALLFLARE_SEARCH) == 0:
    WALLFLARE_SEARCH = ''

WALLTIP_SEARCH = environ.get('WALLTIP_SEARCH', '')
if len(WALLTIP_SEARCH) == 0:
    WALLTIP_SEARCH = ''

WALLCRAFT_CATEGORY = environ.get('WALLCRAFT_CATEGORY', '')
if len(WALLCRAFT_CATEGORY) == 0:
    WALLCRAFT_CATEGORY = ''

PICS = environ.get('PICS', '')
PICS = (PICS.replace("'", '').replace('"', '').replace('[', '').replace(']', '').replace(",", "")).split()

SERVER_PORT = environ.get('SERVER_PORT', '')
if len(SERVER_PORT) == 0:
    SERVER_PORT = 80
else:
    SERVER_PORT = int(SERVER_PORT)

YT_DLP_QUALITY = environ.get('YT_DLP_QUALITY', '')
if len(YT_DLP_QUALITY) == 0:
    YT_DLP_QUALITY = ''

BASE_URL = environ.get('BASE_URL', '').rstrip("/")
if len(BASE_URL) == 0:
    log_warning('BASE_URL not provided!')
    BASE_URL = ''

UPSTREAM_REPO = environ.get('UPSTREAM_REPO', '')
if len(UPSTREAM_REPO) == 0:
   UPSTREAM_REPO = 'https://github.com/weebzone/WZML'

UPSTREAM_BRANCH = environ.get('UPSTREAM_BRANCH', '')
if len(UPSTREAM_BRANCH) == 0:
    UPSTREAM_BRANCH = 'master'

UPDATE_PACKAGES = environ.get('UPDATE_PACKAGES', '')
if len(UPDATE_PACKAGES) == 0:
    UPDATE_PACKAGES = 'False'


config_dict = {'ANILIST_ENABLED': ANILIST_ENABLED,
               'AS_DOCUMENT': AS_DOCUMENT,
               'AUTHORIZED_CHATS': AUTHORIZED_CHATS,
               'AUTHOR_NAME': AUTHOR_NAME,
               'AUTHOR_URL': AUTHOR_URL,
               'AUTO_DELETE_MESSAGE_DURATION': AUTO_DELETE_MESSAGE_DURATION,
               'AUTO_DELETE_UPLOAD_MESSAGE_DURATION': AUTO_DELETE_UPLOAD_MESSAGE_DURATION,
               'BASE_URL': BASE_URL,
               'BOT_TOKEN': BOT_TOKEN,
               'BOT_PM': BOT_PM,
               'BUTTON_FOUR_NAME': BUTTON_FOUR_NAME,
               'BUTTON_FOUR_URL': BUTTON_FOUR_URL,
               'BUTTON_FIVE_NAME': BUTTON_FIVE_NAME,
               'BUTTON_FIVE_URL': BUTTON_FIVE_URL,
               'BUTTON_SIX_NAME': BUTTON_SIX_NAME,
               'BUTTON_SIX_URL': BUTTON_SIX_URL,
               'CAPTION_FONT': CAPTION_FONT,
               'CREDIT_NAME': CREDIT_NAME,
               'CHANNEL_USERNAME': CHANNEL_USERNAME,
               'CLONE_ENABLED': CLONE_ENABLED,
               'CLONE_LIMIT': CLONE_LIMIT,
               'CMD_PERFIX': CMD_PERFIX,
               'DRIVEFIRE_CRYPT': DRIVEFIRE_CRYPT,
               'DOWNLOAD_DIR': DOWNLOAD_DIR,
               'DATABASE_URL': DATABASE_URL,
               'IMDB_TEMPLATE': DEF_IMDB_TEMP,
               'ANIME_TEMPLATE': DEF_ANI_TEMP,  
               'DISABLE_DRIVE_LINK': DISABLE_DRIVE_LINK,
               'OWNER_ID': OWNER_ID,
               'EQUAL_SPLITS': EQUAL_SPLITS,
               'EXTENSION_FILTER': EXTENSION_FILTER,
               'EMOJI_THEME': EMOJI_THEME,
               'GDRIVE_ID': GDRIVE_ID,               
               'IGNORE_PENDING_REQUESTS': IGNORE_PENDING_REQUESTS,
               'INCOMPLETE_TASK_NOTIFIER': INCOMPLETE_TASK_NOTIFIER,
               'INDEX_URL': INDEX_URL,
               'IS_TEAM_DRIVE': IS_TEAM_DRIVE,
               'TG_SPLIT_SIZE': TG_SPLIT_SIZE,
               'MEGA_API_KEY': MEGA_API_KEY,
               'MEGA_EMAIL_ID': MEGA_EMAIL_ID,
               'MEGA_PASSWORD': MEGA_PASSWORD,
               'USER_SESSION_STRING': USER_SESSION_STRING,
               'RSS_CHAT_ID': RSS_CHAT_ID,
               'RSS_COMMAND': RSS_COMMAND,
               'RSS_DELAY': RSS_DELAY,
               'LEECH_ENABLED': LEECH_ENABLED,
               'MIRROR_ENABLED': MIRROR_ENABLED,
               'WATCH_ENABLED': WATCH_ENABLED,
               'WAYBACK_ENABLED': WAYBACK_ENABLED,
               'MEDIAINFO_ENABLED': MEDIAINFO_ENABLED,
               'SET_BOT_COMMANDS': SET_BOT_COMMANDS,
               'FORCE_BOT_PM': FORCE_BOT_PM,
               'LEECH_LOG': LEECH_LOG,
               'LEECH_LOG_URL': LEECH_LOG_URL,
               'LEECH_LOG_INDEXING': LEECH_LOG_INDEXING,
               'PAID_SERVICE': PAID_SERVICE,
               'MIRROR_LOGS': MIRROR_LOGS,
               'MIRROR_LOG_URL': MIRROR_LOG_URL,
               'LINK_LOGS': LINK_LOGS,
               'TIMEZONE': TIMEZONE,
               'TGH_THUMB': TGH_THUMB,
               'TITLE_NAME': TITLE_NAME,
               'GD_INFO': GD_INFO,
               'FSUB': FSUB,
               'FSUB_CHANNEL_ID': FSUB_CHANNEL_ID,
               'SHORTENER': SHORTENER,
               'SHORTENER_API': SHORTENER_API,
               'SEARCH_API_LINK': SEARCH_API_LINK,
               'SEARCH_LIMIT': SEARCH_LIMIT,
               'SEARCH_PLUGINS': SEARCH_PLUGINS,
               'SERVER_PORT': SERVER_PORT,
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
               'USE_SERVICE_ACCOUNTS': USE_SERVICE_ACCOUNTS,
               'USR_TD_DEFAULT' : USR_TD_DEFAULT,
               'UNIFIED_EMAIL': UNIFIED_EMAIL,
               'UNIFIED_PASS': UNIFIED_PASS,
               'VIEW_LINK': VIEW_LINK,
               'GDTOT_CRYPT': GDTOT_CRYPT,
               'HUBDRIVE_CRYPT': HUBDRIVE_CRYPT,
               'KATDRIVE_CRYPT': KATDRIVE_CRYPT,
               'SHAREDRIVE_PHPCKS': SHAREDRIVE_PHPCKS,
               'XSRF_TOKEN': XSRF_TOKEN,
               'laravel_session': laravel_session,
               'TOTAL_TASKS_LIMIT': TOTAL_TASKS_LIMIT,
               'USER_TASKS_LIMIT': USER_TASKS_LIMIT,
               'STORAGE_THRESHOLD': STORAGE_THRESHOLD,
               'TORRENT_DIRECT_LIMIT': TORRENT_DIRECT_LIMIT,
               'ZIP_UNZIP_LIMIT': ZIP_UNZIP_LIMIT,
               'LEECH_LIMIT': LEECH_LIMIT,
               'MEGA_LIMIT': MEGA_LIMIT,
               'TIME_GAP': TIME_GAP,
               'FINISHED_PROGRESS_STR': FINISHED_PROGRESS_STR,
               'UN_FINISHED_PROGRESS_STR': UN_FINISHED_PROGRESS_STR,
               'MULTI_WORKING_PROGRESS_STR': MULTI_WORKING_PROGRESS_STR,
               'SHOW_LIMITS_IN_STATS': SHOW_LIMITS_IN_STATS,
               'TELEGRAPH_STYLE': TELEGRAPH_STYLE,
               'WALLFLARE_SEARCH': WALLFLARE_SEARCH,
               'WALLTIP_SEARCH': WALLTIP_SEARCH,
               'WALLCRAFT_CATEGORY': WALLCRAFT_CATEGORY,
               'PIXABAY_API_KEY': PIXABAY_API_KEY,
               'PIXABAY_CATEGORY': PIXABAY_CATEGORY,
               'PIXABAY_SEARCH': PIXABAY_SEARCH,
               'PICS': PICS,
               'NAME_FONT': NAME_FONT,
               'UPDATE_PACKAGES': UPDATE_PACKAGES,
               'SOURCE_LINK': SOURCE_LINK,
               'START_BTN1_NAME': START_BTN1_NAME,
               'START_BTN1_URL': START_BTN1_URL,
               'START_BTN2_NAME': START_BTN2_NAME,
               'START_BTN2_URL': START_BTN2_URL,
               'WEB_PINCODE': WEB_PINCODE,
               'YT_DLP_QUALITY': YT_DLP_QUALITY}


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

if BASE_URL:
    Popen(f"gunicorn web.wserver:app --bind 0.0.0.0:{SERVER_PORT}", shell=True)

srun(["qbittorrent-nox", "-d", "--profile=."])
if not ospath.exists('.netrc'):
    srun(["touch", ".netrc"])
srun(["cp", ".netrc", "/root/.netrc"])
srun(["chmod", "600", ".netrc"])
srun(["chmod", "+x", "aria.sh"])
srun("./aria.sh", shell=True)
if ospath.exists('accounts.zip'):
    if ospath.exists('accounts'):
        srun(["rm", "-rf", "accounts"])
    srun(["unzip", "-q", "-o", "accounts.zip", "-x", "accounts/emails.txt"])
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
        sleep(15)
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
    del aria2_options['dir']
else:
    a2c_glo = {}
    for op in aria2c_global:
        if op in aria2_options:
            a2c_glo[op] = aria2_options[op]
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

updater = tgUpdater(token=BOT_TOKEN, request_kwargs={'read_timeout': 20, 'connect_timeout': 15})
bot = updater.bot
dispatcher = updater.dispatcher
job_queue = updater.job_queue
