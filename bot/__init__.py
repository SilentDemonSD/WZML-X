import re
from os import environ
from logging import getLogger, FileHandler, StreamHandler, INFO, basicConfig, error as log_error, info as log_info, warning as log_warning
from socket import setdefaulttimeout
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


def getConfig(name: str):
    return environ[name]


load_dotenv('config.env', override=True)

try:
    NETRC_URL = getConfig('NETRC_URL')
    if len(NETRC_URL) == 0:
        raise KeyError
    try:
        res = rget(NETRC_URL)
        if res.status_code == 200:
            with open('.netrc', 'wb+') as f:
                f.write(res.content)
        else:
            log_error(f"Failed to download .netrc {res.status_code}")
    except Exception as e:
        log_error(f"NETRC_URL: {e}")
except:
    pass
try:
    SERVER_PORT = getConfig('SERVER_PORT')
    if len(SERVER_PORT) == 0:
        raise KeyError
except:
    SERVER_PORT = 80

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
DRIVES_NAMES = []
DRIVES_IDS = []
INDEX_URLS = []

try:
    if bool(getConfig('_____REMOVE_THIS_LINE_____')):
        log_error('The README.md file there to be read! Exiting now!')
        exit()
except:
    pass

aria2 = ariaAPI(
    ariaClient(
        host="http://localhost",
        port=6800,
        secret="",
    )
)

def get_client():
    return qbClient(host="localhost", port=8090, VERIFY_WEBUI_CERTIFICATE=False, REQUESTS_ARGS={'timeout': (30, 60)})

DOWNLOAD_DIR = None
BOT_TOKEN = None

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

AUTHORIZED_CHATS = set()
SUDO_USERS = set()
AS_DOC_USERS = set()
AS_MEDIA_USERS = set()
EXTENSION_FILTER = set(['.aria2'])
LEECH_LOG = set()	
MIRROR_LOGS = set()
LINK_LOGS = set()


try:
    BOT_TOKEN = getConfig('BOT_TOKEN')
    parent_id = getConfig('GDRIVE_FOLDER_ID')
    DOWNLOAD_DIR = getConfig('DOWNLOAD_DIR')
    if not DOWNLOAD_DIR.endswith("/"):
        DOWNLOAD_DIR = DOWNLOAD_DIR + '/'
    DOWNLOAD_STATUS_UPDATE_INTERVAL = int(getConfig('DOWNLOAD_STATUS_UPDATE_INTERVAL'))
    OWNER_ID = int(getConfig('OWNER_ID'))
    AUTO_DELETE_MESSAGE_DURATION = int(getConfig('AUTO_DELETE_MESSAGE_DURATION'))
    TELEGRAM_API = getConfig('TELEGRAM_API')
    TELEGRAM_HASH = getConfig('TELEGRAM_HASH')
except:
    log.error("One or more env variables missing! Exiting now")
    exit(1)


try:
    aid = getConfig('AUTHORIZED_CHATS')
    aid = aid.split()
    for _id in aid:
        AUTHORIZED_CHATS.add(int(_id.strip()))
except:
    pass
try:
    aid = getConfig('SUDO_USERS')
    aid = aid.split()
    for _id in aid:
        SUDO_USERS.add(int(_id.strip()))
except:
    pass
try:
    fx = getConfig('EXTENSION_FILTER')
    if len(fx) > 0:
        fx = fx.split()
        for x in fx:
            EXTENSION_FILTER.add(x.strip().lower())
except:
    pass
try:	
    aid = getConfig('LEECH_LOG')	
    aid = aid.split(' ')	
    for _id in aid:	
        LEECH_LOG.add(int(_id))	
except:	
    pass	
try:	
    aid = getConfig('MIRROR_LOGS')	
    aid = aid.split(' ')	
    for _id in aid:	
        MIRROR_LOGS.add(int(_id))
except:	
    pass
try:
    aid = getConfig('LINK_LOGS')
    aid = aid.split(' ')
    for _id in aid:
        LINK_LOGS.add(int(_id))
except:
    pass


try:
    AUTO_DELETE_UPLOAD_MESSAGE_DURATION = int(getConfig('AUTO_DELETE_UPLOAD_MESSAGE_DURATION'))
except KeyError as e:
    AUTO_DELETE_UPLOAD_MESSAGE_DURATION = -1
    LOGGER.warning("AUTO_DELETE_UPLOAD_MESSAGE_DURATION var missing!")
    pass

LOGGER.info("Generating SESSION_STRING")
app = Client(name='pyrogram', api_id=int(TELEGRAM_API), api_hash=TELEGRAM_HASH, bot_token=BOT_TOKEN, parse_mode=enums.ParseMode.HTML, no_updates=True)

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

try:
    MEGA_API_KEY = getConfig('MEGA_API_KEY')
    if len(MEGA_API_KEY) == 0:
        raise KeyError
except:
    log_warning('MEGA API KEY not provided!')
    MEGA_API_KEY = None
try:
    MEGA_EMAIL_ID = getConfig('MEGA_EMAIL_ID')
    MEGA_PASSWORD = getConfig('MEGA_PASSWORD')
    if len(MEGA_EMAIL_ID) == 0 or len(MEGA_PASSWORD) == 0:
        raise KeyError
except:
    log_warning('MEGA Credentials not provided!')
    MEGA_EMAIL_ID = None
    MEGA_PASSWORD = None

try:
    DB_URI = getConfig('DATABASE_URL')
    if len(DB_URI) == 0:
        raise KeyError
except:
    DB_URI = None


tgBotMaxFileSize = 2097151000
try:
    TG_SPLIT_SIZE = getConfig('TG_SPLIT_SIZE')
    if len(TG_SPLIT_SIZE) == 0 or int(TG_SPLIT_SIZE) > tgBotMaxFileSize:
        raise KeyError
    TG_SPLIT_SIZE = int(TG_SPLIT_SIZE)
except:
    TG_SPLIT_SIZE = tgBotMaxFileSize
try:
    USER_SESSION_STRING = getConfig('USER_SESSION_STRING')
    if len(USER_SESSION_STRING) == 0:
        raise KeyError
    premium_session = Client(name='premium_session', api_id=int(TELEGRAM_API), api_hash=TELEGRAM_HASH, session_string=USER_SESSION_STRING, parse_mode=enums.ParseMode.HTML, no_updates=True)
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
try:
    STATUS_LIMIT = getConfig('STATUS_LIMIT')
    if len(STATUS_LIMIT) == 0:
        raise KeyError
    STATUS_LIMIT = int(STATUS_LIMIT)
except:
    STATUS_LIMIT = None
try:
    UPTOBOX_TOKEN = getConfig('UPTOBOX_TOKEN')
    if len(UPTOBOX_TOKEN) == 0:
        raise KeyError
except:
    UPTOBOX_TOKEN = None
try:
    INDEX_URL = getConfig('INDEX_URL').rstrip("/")
    if len(INDEX_URL) == 0:
        raise KeyError
    INDEX_URLS.append(INDEX_URL)
except:
    INDEX_URL = None
    INDEX_URLS.append(None)
try:
    SEARCH_API_LINK = getConfig('SEARCH_API_LINK').rstrip("/")
    if len(SEARCH_API_LINK) == 0:
        raise KeyError
except:
    SEARCH_API_LINK = None
try:
    SEARCH_LIMIT = getConfig('SEARCH_LIMIT')
    if len(SEARCH_LIMIT) == 0:
        raise KeyError
    SEARCH_LIMIT = int(SEARCH_LIMIT)
except:
    SEARCH_LIMIT = 0
try:
    RSS_COMMAND = getConfig('RSS_COMMAND')
    if len(RSS_COMMAND) == 0:
        raise KeyError
except:
    RSS_COMMAND = None
try:
    CMD_INDEX = getConfig('CMD_INDEX')
    if len(CMD_INDEX) == 0:
        raise KeyError
except:
    CMD_INDEX = ''
try:
    SHOW_LIMITS_IN_STATS = getConfig('SHOW_LIMITS_IN_STATS')
    SHOW_LIMITS_IN_STATS = SHOW_LIMITS_IN_STATS.lower() == 'true'
except KeyError:
    SHOW_LIMITS_IN_STATS = False
try:
    TORRENT_DIRECT_LIMIT = getConfig('TORRENT_DIRECT_LIMIT')
    if len(TORRENT_DIRECT_LIMIT) == 0:
        raise KeyError
    TORRENT_DIRECT_LIMIT = float(TORRENT_DIRECT_LIMIT)
except:
    TORRENT_DIRECT_LIMIT = None
try:
    CLONE_LIMIT = getConfig('CLONE_LIMIT')
    if len(CLONE_LIMIT) == 0:
        raise KeyError
    CLONE_LIMIT = float(CLONE_LIMIT)
except:
    CLONE_LIMIT = None
try:
    LEECH_LIMIT = getConfig('LEECH_LIMIT')
    if len(LEECH_LIMIT) == 0:
        raise KeyError
    LEECH_LIMIT = float(LEECH_LIMIT)
except:
    LEECH_LIMIT = None
try:
    MEGA_LIMIT = getConfig('MEGA_LIMIT')
    if len(MEGA_LIMIT) == 0:
        raise KeyError
    MEGA_LIMIT = float(MEGA_LIMIT)
except:
    MEGA_LIMIT = None
try:
    TOTAL_TASKS_LIMIT = getConfig('TOTAL_TASKS_LIMIT')
    if len(TOTAL_TASKS_LIMIT) == 0:
        raise KeyError
    TOTAL_TASKS_LIMIT = int(TOTAL_TASKS_LIMIT)
except KeyError:
    TOTAL_TASKS_LIMIT = None
try:
    USER_TASKS_LIMIT = getConfig('USER_TASKS_LIMIT')
    if len(USER_TASKS_LIMIT) == 0:
        raise KeyError
    USER_TASKS_LIMIT = int(USER_TASKS_LIMIT)
except KeyError:
    USER_TASKS_LIMIT = None
try:
    STORAGE_THRESHOLD = getConfig('STORAGE_THRESHOLD')
    if len(STORAGE_THRESHOLD) == 0:
        raise KeyError
    STORAGE_THRESHOLD = float(STORAGE_THRESHOLD)
except:
    STORAGE_THRESHOLD = None
try:
    ZIP_UNZIP_LIMIT = getConfig('ZIP_UNZIP_LIMIT')
    if len(ZIP_UNZIP_LIMIT) == 0:
        raise KeyError
    ZIP_UNZIP_LIMIT = float(ZIP_UNZIP_LIMIT)
except:
    ZIP_UNZIP_LIMIT = None
try:
    RSS_CHAT_ID = getConfig('RSS_CHAT_ID')
    if len(RSS_CHAT_ID) == 0:
        raise KeyError
    RSS_CHAT_ID = int(RSS_CHAT_ID)
except:
    RSS_CHAT_ID = None



try:
    RSS_USER_SESSION_STRING = getConfig('RSS_USER_SESSION_STRING')
    if len(RSS_USER_SESSION_STRING) == 0:
        raise KeyError
    rss_session = Client(name='rss_session', api_id=int(TELEGRAM_API), api_hash=TELEGRAM_HASH, session_string=RSS_USER_SESSION_STRING, parse_mode=enums.ParseMode.HTML, no_updates=True)
except:
    USER_SESSION_STRING = None
    rss_session = None
try:
    RSS_DELAY = getConfig('RSS_DELAY')
    if len(RSS_DELAY) == 0:
        raise KeyError
    RSS_DELAY = int(RSS_DELAY)
except:
    RSS_DELAY = 900
try:
    TORRENT_TIMEOUT = getConfig('TORRENT_TIMEOUT')
    if len(TORRENT_TIMEOUT) == 0:
        raise KeyError
    TORRENT_TIMEOUT = int(TORRENT_TIMEOUT)
except:
    TORRENT_TIMEOUT = None

try:
    BUTTON_FOUR_NAME = getConfig('BUTTON_FOUR_NAME')
    BUTTON_FOUR_URL = getConfig('BUTTON_FOUR_URL')
    if len(BUTTON_FOUR_NAME) == 0 or len(BUTTON_FOUR_URL) == 0:
        raise KeyError
except:
    BUTTON_FOUR_NAME = None
    BUTTON_FOUR_URL = None
try:
    BUTTON_FIVE_NAME = getConfig('BUTTON_FIVE_NAME')
    BUTTON_FIVE_URL = getConfig('BUTTON_FIVE_URL')
    if len(BUTTON_FIVE_NAME) == 0 or len(BUTTON_FIVE_URL) == 0:
        raise KeyError
except:
    BUTTON_FIVE_NAME = None
    BUTTON_FIVE_URL = None
try:
    BUTTON_SIX_NAME = getConfig('BUTTON_SIX_NAME')
    BUTTON_SIX_URL = getConfig('BUTTON_SIX_URL')
    if len(BUTTON_SIX_NAME) == 0 or len(BUTTON_SIX_URL) == 0:
        raise KeyError
except:
    BUTTON_SIX_NAME = None
    BUTTON_SIX_URL = None
try:
    INCOMPLETE_TASK_NOTIFIER = getConfig('INCOMPLETE_TASK_NOTIFIER')
    INCOMPLETE_TASK_NOTIFIER = INCOMPLETE_TASK_NOTIFIER.lower() == 'true'
except:
    INCOMPLETE_TASK_NOTIFIER = False
try:
    STOP_DUPLICATE = getConfig('STOP_DUPLICATE')
    STOP_DUPLICATE = STOP_DUPLICATE.lower() == 'true'
except:
    STOP_DUPLICATE = False
try:
    VIEW_LINK = getConfig('VIEW_LINK')
    VIEW_LINK = VIEW_LINK.lower() == 'true'
except:
    VIEW_LINK = False
try:
    SET_BOT_COMMANDS = getConfig('SET_BOT_COMMANDS')
    SET_BOT_COMMANDS = SET_BOT_COMMANDS.lower() == 'true'
except:
    SET_BOT_COMMANDS = False        
try:
    IS_TEAM_DRIVE = getConfig('IS_TEAM_DRIVE')
    IS_TEAM_DRIVE = IS_TEAM_DRIVE.lower() == 'true'
except:
    IS_TEAM_DRIVE = False
try:
    USE_SERVICE_ACCOUNTS = getConfig('USE_SERVICE_ACCOUNTS')
    USE_SERVICE_ACCOUNTS = USE_SERVICE_ACCOUNTS.lower() == 'true'
except:
    USE_SERVICE_ACCOUNTS = False
try:
    WEB_PINCODE = getConfig('WEB_PINCODE')
    WEB_PINCODE = WEB_PINCODE.lower() == 'true'
except:
    WEB_PINCODE = False
try:
    SHORTENER = getConfig('SHORTENER')
    SHORTENER_API = getConfig('SHORTENER_API')
    if len(SHORTENER) == 0 or len(SHORTENER_API) == 0:
        raise KeyError
except:
    SHORTENER = None
    SHORTENER_API = None
try:
    IGNORE_PENDING_REQUESTS = getConfig("IGNORE_PENDING_REQUESTS")
    IGNORE_PENDING_REQUESTS = IGNORE_PENDING_REQUESTS.lower() == 'true'
except:
    IGNORE_PENDING_REQUESTS = False
try:
    BASE_URL = getConfig('BASE_URL_OF_BOT').rstrip("/")
    if len(BASE_URL) == 0:
        raise KeyError
except:
    log_warning('BASE_URL_OF_BOT not provided!')
    BASE_URL = None

try:
    AS_DOCUMENT = getConfig('AS_DOCUMENT')
    AS_DOCUMENT = AS_DOCUMENT.lower() == 'true'
except:
    AS_DOCUMENT = False
try:
    EQUAL_SPLITS = getConfig('EQUAL_SPLITS')
    EQUAL_SPLITS = EQUAL_SPLITS.lower() == 'true'
except:
    EQUAL_SPLITS = False
try:
    CUSTOM_FILENAME = getConfig('CUSTOM_FILENAME')
    if len(CUSTOM_FILENAME) == 0:
        raise KeyError
except:
    CUSTOM_FILENAME = None
try:
    MIRROR_ENABLED = getConfig("MIRROR_ENABLED")
    MIRROR_ENABLED = MIRROR_ENABLED.lower() == "true"
except:
    MIRROR_ENABLED = False
try:
    LEECH_ENABLED = getConfig("LEECH_ENABLED")
    LEECH_ENABLED = LEECH_ENABLED.lower() == "true"
except:
    LEECH_ENABLED = False

try:
    WATCH_ENABLED = getConfig("WATCH_ENABLED")
    WATCH_ENABLED = WATCH_ENABLED.lower() == "true"
except:
    WATCH_ENABLED = False
try:
    CLONE_ENABLED = getConfig("CLONE_ENABLED")
    CLONE_ENABLED = CLONE_ENABLED.lower() == "true"
except:
    CLONE_ENABLED = False
try:
    ANILIST_ENABLED = getConfig("ANILIST_ENABLED")
    ANILIST_ENABLED = ANILIST_ENABLED.lower() == "true"
except:
    ANILIST_ENABLED = False
try:
    WAYBACK_ENABLED = getConfig("WAYBACK_ENABLED")
    WAYBACK_ENABLED = WAYBACK_ENABLED.lower() == "true"
except:
    WAYBACK_ENABLED = False
try:
    MEDIAINFO_ENABLED = getConfig("MEDIAINFO_ENABLED")
    MEDIAINFO_ENABLED = MEDIAINFO_ENABLED.lower() == "true"
except:
    MEDIAINFO_ENABLED = False
try:
    TIMEZONE = getConfig("TIMEZONE")
    if len(TIMEZONE) == 0:
        TIMEZONE = None
except:
    TIMEZONE = "Asia/Kolkata"
try:
    CRYPT = getConfig('CRYPT')
    if len(CRYPT) == 0:
        raise KeyError
except:
    CRYPT = None
try:
    UNIFIED_EMAIL = getConfig('UNIFIED_EMAIL')
    if len(UNIFIED_EMAIL) == 0:
        raise KeyError
except:
    UNIFIED_EMAIL = None
try:
    UNIFIED_PASS = getConfig('UNIFIED_PASS')
    if len(UNIFIED_PASS) == 0:
        raise KeyError
except:
    UNIFIED_PASS = None
try:
    HUBDRIVE_CRYPT = getConfig('HUBDRIVE_CRYPT')
    if len(HUBDRIVE_CRYPT) == 0:
        raise KeyError
except:
    HUBDRIVE_CRYPT = None
try:
    KATDRIVE_CRYPT = getConfig('KATDRIVE_CRYPT')
    if len(KATDRIVE_CRYPT) == 0:
        raise KeyError
except:
    KATDRIVE_CRYPT = None
try:
    DRIVEFIRE_CRYPT = getConfig('DRIVEFIRE_CRYPT')
    if len(DRIVEFIRE_CRYPT) == 0:
        raise KeyError
except:
    DRIVEFIRE_CRYPT = None
try:
    SOURCE_LINK = getConfig('SOURCE_LINK')
    SOURCE_LINK = SOURCE_LINK.lower() == 'true'
except KeyError:
    SOURCE_LINK = False
try:	
    BOT_PM = getConfig('BOT_PM')	
    BOT_PM = BOT_PM.lower() == 'true'	
except KeyError:	
    BOT_PM = False
try:
    FORCE_BOT_PM = getConfig('FORCE_BOT_PM')
    FORCE_BOT_PM = FORCE_BOT_PM.lower() == 'true'
except KeyError:
    FORCE_BOT_PM = False
try:
    MIRROR_LOG_URL = getConfig('MIRROR_LOG_URL')
    if len(MIRROR_LOG_URL) == 0:
        MIRROR_LOG_URL = ''
except KeyError:
    MIRROR_LOG_URL = ''
try:
    LEECH_LOG_URL = getConfig('LEECH_LOG_URL')
    if len(LEECH_LOG_URL) == 0:
        LEECH_LOG_URL = ''
except KeyError:
    LEECH_LOG_URL = ''
try:	
    LEECH_LOG_INDEXING = getConfig('LEECH_LOG_INDEXING')	
    LEECH_LOG_INDEXING = LEECH_LOG_INDEXING.lower() == 'true'	
except KeyError:	
    LEECH_LOG_INDEXING = False
try:
    AUTHOR_NAME = getConfig('AUTHOR_NAME')
    if len(AUTHOR_NAME) == 0:
        AUTHOR_NAME = 'Karan'
except KeyError:
    AUTHOR_NAME = 'Karan'

try:
    AUTHOR_URL = getConfig('AUTHOR_URL')
    if len(AUTHOR_URL) == 0:
        AUTHOR_URL = 'https://t.me/WeebZone_updates'
except KeyError:
    AUTHOR_URL = 'https://t.me/WeebZone_updates'
try:
    GD_INFO = getConfig('GD_INFO')
    if len(GD_INFO) == 0:
        GD_INFO = 'Uploaded by WeebZone Mirror Bot'
except KeyError:
    GD_INFO = 'Uploaded by WeebZone Mirror Bot'
try:
    DISABLE_DRIVE_LINK = getConfig('DISABLE_DRIVE_LINK')
    DISABLE_DRIVE_LINK = DISABLE_DRIVE_LINK.lower() == 'true'
except KeyError:
    DISABLE_DRIVE_LINK = False
try:
    TITLE_NAME = getConfig('TITLE_NAME')
    if len(TITLE_NAME) == 0:
        TITLE_NAME = 'WeebZone'
except KeyError:
    TITLE_NAME = 'WeebZone'
try:
    START_BTN1_NAME = getConfig('START_BTN1_NAME')
    START_BTN1_URL = getConfig('START_BTN1_URL')
    if len(START_BTN1_NAME) == 0 or len(START_BTN1_URL) == 0:
        raise KeyError
except:
    START_BTN1_NAME = 'Master'
    START_BTN1_URL = 'https://t.me/krn_adhikari'

try:
    START_BTN2_NAME = getConfig('START_BTN2_NAME')
    START_BTN2_URL = getConfig('START_BTN2_URL')
    if len(START_BTN2_NAME) == 0 or len(START_BTN2_URL) == 0:
        raise KeyError
except:
    START_BTN2_NAME = 'Support Group'
    START_BTN2_URL = 'https://t.me/WeebZone_updates'
try:
    CREDIT_NAME = getConfig('CREDIT_NAME')
    if len(CREDIT_NAME) == 0:
        CREDIT_NAME = 'WeebZone'
except KeyError:
    CREDIT_NAME = 'WeebZone'
try:
    NAME_FONT = getConfig('NAME_FONT')
    if len(NAME_FONT) == 0:
        NAME_FONT = 'code'
except KeyError:
    NAME_FONT = 'code'
try:
    CAPTION_FONT = getConfig('CAPTION_FONT')
    if len(CAPTION_FONT) == 0:
        CAPTION_FONT = 'code'
except KeyError:
    CAPTION_FONT = 'code'
try:
    FINISHED_PROGRESS_STR = getConfig('FINISHED_PROGRESS_STR') 
    UN_FINISHED_PROGRESS_STR = getConfig('UN_FINISHED_PROGRESS_STR')
except:
    FINISHED_PROGRESS_STR = '●' # '■'
    UN_FINISHED_PROGRESS_STR = '○' # '□'
try:
    FSUB = getConfig('FSUB')
    FSUB = FSUB.lower() == 'true'
except BaseException:
    FSUB = False
    LOGGER.info("Force Subscribe is disabled")
try:
    CHANNEL_USERNAME = getConfig("CHANNEL_USERNAME")
    if len(CHANNEL_USERNAME) == 0:
        raise KeyError
except KeyError:
    log_info("CHANNEL_USERNAME not provided! Using default @WeebZone_updates")
    CHANNEL_USERNAME = "WeebZone_updates"
try:
    FSUB_CHANNEL_ID = getConfig("FSUB_CHANNEL_ID")
    if len(FSUB_CHANNEL_ID) == 0:
        raise KeyError
    FSUB_CHANNEL_ID = int(FSUB_CHANNEL_ID)
except KeyError:
    log_info("CHANNEL_ID not provided! Using default id of @WeebZone_updates")
    FSUB_CHANNEL_ID = -1001512307861
try:
    TOKEN_PICKLE_URL = getConfig('TOKEN_PICKLE_URL')
    if len(TOKEN_PICKLE_URL) == 0:
        raise KeyError
    try:
        res = rget(TOKEN_PICKLE_URL)
        if res.status_code == 200:
            with open('token.pickle', 'wb+') as f:
                f.write(res.content)
        else:
            log_error(f"Failed to download token.pickle, link got HTTP response: {res.status_code}")
    except Exception as e:
        log_error(f"TOKEN_PICKLE_URL: {e}")
except:
    pass
try:
    ACCOUNTS_ZIP_URL = getConfig('ACCOUNTS_ZIP_URL')
    if len(ACCOUNTS_ZIP_URL) == 0:
        raise KeyError
    try:
        res = rget(ACCOUNTS_ZIP_URL)
        if res.status_code == 200:
            with open('accounts.zip', 'wb+') as f:
                f.write(res.content)
        else:
            log_error(f"Failed to download accounts.zip, link got HTTP response: {res.status_code}")
    except Exception as e:
        log_error(f"ACCOUNTS_ZIP_URL: {e}")
        raise KeyError
    srun(["unzip", "-q", "-o", "accounts.zip"])
    srun(["chmod", "-R", "777", "accounts"])
    osremove("accounts.zip")
except:
    pass
try:
    MULTI_SEARCH_URL = getConfig('MULTI_SEARCH_URL')
    if len(MULTI_SEARCH_URL) == 0:
        raise KeyError
    try:
        res = rget(MULTI_SEARCH_URL)
        if res.status_code == 200:
            with open('drive_folder', 'wb+') as f:
                f.write(res.content)
        else:
            log_error(f"Failed to download drive_folder, link got HTTP response: {res.status_code}")
    except Exception as e:
        log_error(f"MULTI_SEARCH_URL: {e}")
except:
    pass
try:
    YT_COOKIES_URL = getConfig('YT_COOKIES_URL')
    if len(YT_COOKIES_URL) == 0:
        raise KeyError
    try:
        res = rget(YT_COOKIES_URL)
        if res.status_code == 200:
            with open('cookies.txt', 'wb+') as f:
                f.write(res.content)
        else:
            log_error(f"Failed to download cookies.txt, link got HTTP response: {res.status_code}")
    except Exception as e:
        log_error(f"YT_COOKIES_URL: {e}")
except:
    pass

DRIVES_NAMES.append("Main")
DRIVES_IDS.append(parent_id)
if ospath.exists('drive_folder'):
    with open('drive_folder', 'r+') as f:
        lines = f.readlines()
        for line in lines:
            try:
                temp = line.strip().split()
                DRIVES_IDS.append(temp[1])
                DRIVES_NAMES.append(temp[0].replace("_", " "))
            except:
                pass
            try:
                INDEX_URLS.append(temp[2])
            except:
                INDEX_URLS.append(None)
try:
    SEARCH_PLUGINS = getConfig('SEARCH_PLUGINS')
    if len(SEARCH_PLUGINS) == 0:
        raise KeyError
    SEARCH_PLUGINS = jsonloads(SEARCH_PLUGINS)
except:
    SEARCH_PLUGINS = None
try:
    IMAGE_URL = getConfig('IMAGE_URL')
except KeyError:
    IMAGE_URL = 'https://graph.org/file/6b22ef7b8a733c5131d3f.jpg'
try:
    EMOJI_THEME = getConfig('EMOJI_THEME')
    EMOJI_THEME = EMOJI_THEME.lower() == 'true'
except:
    EMOJI_THEME = False
try:
    TELEGRAPH_STYLE = getConfig('TELEGRAPH_STYLE')
    TELEGRAPH_STYLE = TELEGRAPH_STYLE.lower() == 'true'
except:
    TELEGRAPH_STYLE = False
try:
    PIXABAY_API_KEY = getConfig('PIXABAY_API_KEY')
    if len(PIXABAY_API_KEY) == 0:
        raise KeyError
except:
    PIXABAY_API_KEY = None
try:
    PIXABAY_CATEGORY = getConfig('PIXABAY_CATEGORY')
    if len(PIXABAY_CATEGORY) == 0:
        raise KeyError
except:
    PIXABAY_CATEGORY = None
try:
    PIXABAY_SEARCH = getConfig('PIXABAY_SEARCH')
    if len(PIXABAY_SEARCH) == 0:
        raise KeyError
except:
    PIXABAY_SEARCH = None
try:
    WALLFLARE_SEARCH = getConfig('WALLFLARE_SEARCH')
    if len(WALLFLARE_SEARCH) == 0:
        raise KeyError
except:
    WALLFLARE_SEARCH = None
try:
    WALLTIP_SEARCH = getConfig('WALLTIP_SEARCH')
    if len(WALLTIP_SEARCH) == 0:
        raise KeyError
except:
    WALLTIP_SEARCH = None
try:
    WALLCRAFT_CATEGORY = getConfig('WALLCRAFT_CATEGORY')
    if len(WALLCRAFT_CATEGORY) == 0:
        raise KeyError
except:
    WALLCRAFT_CATEGORY = None
PICS = (environ.get('PICS', '')).split()

updater = tgUpdater(token=BOT_TOKEN, request_kwargs={'read_timeout': 20, 'connect_timeout': 15})
bot = updater.bot
dispatcher = updater.dispatcher
job_queue = updater.job_queue
botname = bot.username
