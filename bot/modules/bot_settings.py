from telegram.ext import CommandHandler, CallbackQueryHandler, MessageHandler, Filters
from functools import partial
from time import time, sleep
from os import remove, rename, path as ospath, getenv
from subprocess import run as srun, Popen
from dotenv import load_dotenv
from bot import config_dict, dispatcher, user_data, DB_URI, tgBotMaxFileSize, DRIVES_IDS, DRIVES_NAMES, INDEX_URLS, aria2, GLOBAL_EXTENSION_FILTER, LOGGER, status_reply_dict_lock, Interval, aria2_options, aria2c_global, download_dict, qbit_options, get_client
from bot.helper.telegram_helper.message_utils import sendFile, sendMarkup, editMessage, update_all_messages
from bot.helper.telegram_helper.filters import CustomFilters
from bot.helper.telegram_helper.bot_commands import BotCommands
from bot.helper.telegram_helper.button_build import ButtonMaker
from bot.helper.ext_utils.bot_utils import new_thread, setInterval
from bot.helper.ext_utils.db_handler import DbManger
from bot.modules.search import initiate_search_tools

START = 0
STATE = 'view'
handler_dict = {}
default_values = {'AUTO_DELETE_MESSAGE_DURATION': 30,
                  'AUTO_DELETE_UPLOAD_MESSAGE_DURATION': -1,               
                  'UPSTREAM_BRANCH': 'master',
                  'UPSTREAM_REPO': 'https://github.com/weebzone/WZML',
                  'STATUS_UPDATE_INTERVAL': 10,
                  'TIME_GAP': -1,
                  'TG_SPLIT_SIZE': tgBotMaxFileSize,
                  'TGH_THUMB': 'https://te.legra.ph/file/3325f4053e8d68eab07b5.jpg',
                  'START_BTN1_NAME': 'Master',
                  'START_BTN1_URL': 'https://t.me/krn_adhikari',
                  'START_BTN2_NAME': 'Support Group',
                  'START_BTN2_URL': 'https://t.me/WeebZone_updates',
                  'AUTHOR_NAME': 'WZML',
                  'AUTHOR_URL': 'https://t.me/WeebZone_updates',
                  'TITLE_NAME': 'WeebZone',
                  'GD_INFO': 'Uploaded by WeebZone Mirror Bot',
                  'CREDIT_NAME': 'WeebZone',
                  'NAME_FONT': 'code',
                  'CAPTION_FONT': 'code',
                  'FINISHED_PROGRESS_STR': '●',
                  'UN_FINISHED_PROGRESS_STR': '○',
                  'CHANNEL_USERNAME': 'WeebZone_updates',
                  'FSUB_CHANNEL_ID': '-1001512307861',
                  'IMAGE_URL': 'https://graph.org/file/6b22ef7b8a733c5131d3f.jpg',
                  'TIMEZONE': 'Asia/Kolkata',
                  'SEARCH_LIMIT': 0,
                  'RSS_DELAY': 900}



def load_config():

    GDRIVE_ID = getenv('GDRIVE_ID', '')
    if len(GDRIVE_ID) == 0:
        GDRIVE_ID = ''

    AUTHORIZED_CHATS = getenv('AUTHORIZED_CHATS', '')
    if len(AUTHORIZED_CHATS) != 0:
        aid = AUTHORIZED_CHATS.split()
        for id_ in aid:
            user_data[int(id_.strip())] = {'is_auth': True}

    SUDO_USERS = getenv('SUDO_USERS', '')
    if len(SUDO_USERS) != 0:
        aid = SUDO_USERS.split()
        for id_ in aid:
            user_data[int(id_.strip())] = {'is_sudo': True}

    PAID_USERS = getenv('PAID_USERS', '')
    if len(PAID_USERS) != 0:    
        aid = PAID_USERS.split()
        for id_ in aid:
            user_data[int(id_.strip())] = {'is_paid': True}

    LOG_LEECH = getenv('LOG_LEECH', '')
    if len(LOG_LEECH) != 0: 
        aid = LOG_LEECH.split(' ')
        user_data['is_log_leech'] = [int(id_.strip()) for id_ in aid]

    LEECH_LOG = getenv('LEECH_LOG', '')
    if len(LEECH_LOG) != 0: 
        aid = LEECH_LOG.split(' ')
        user_data['is_leech_log'] = [int(id_.strip()) for id_ in aid]

    MIRROR_LOGS = getenv('MIRROR_LOGS', '')
    if len(MIRROR_LOGS) != 0:   
        aid = MIRROR_LOGS.split(' ')
        user_data['mirror_logs'] = [int(id_.strip()) for id_ in aid]

    LINK_LOGS = getenv('LINK_LOGS', '')
    if len(LINK_LOGS) != 0: 
        aid = LINK_LOGS.split(' ')
        user_data['link_logs'] = [int(id_.strip()) for id_ in aid]

    EXTENSION_FILTER = getenv('EXTENSION_FILTER', '')
    if len(EXTENSION_FILTER) > 0:
        fx = EXTENSION_FILTER.split()
        GLOBAL_EXTENSION_FILTER.clear()
        GLOBAL_EXTENSION_FILTER.append('.aria2')
        for x in fx:
            GLOBAL_EXTENSION_FILTER.append(x.strip().lower())


    tgBotMaxFileSize = 2097151000

    TG_SPLIT_SIZE = getenv('TG_SPLIT_SIZE', '')
    if len(TG_SPLIT_SIZE) == 0 or int(TG_SPLIT_SIZE) > tgBotMaxFileSize:
        TG_SPLIT_SIZE = tgBotMaxFileSize
    else:
        TG_SPLIT_SIZE = int(TG_SPLIT_SIZE)

    MEGA_API_KEY = getenv('MEGA_API_KEY', '')
    if len(MEGA_API_KEY) == 0:
        MEGA_API_KEY = ''

    MEGA_EMAIL_ID = getenv('MEGA_EMAIL_ID', '')
    MEGA_PASSWORD = getenv('MEGA_PASSWORD', '')
    if len(MEGA_EMAIL_ID) == 0 or len(MEGA_PASSWORD) == 0:
        MEGA_EMAIL_ID = ''
        MEGA_PASSWORD = ''

    STATUS_LIMIT = getenv('STATUS_LIMIT', '')
    STATUS_LIMIT = '' if len(STATUS_LIMIT) == 0 else int(STATUS_LIMIT)

    UPTOBOX_TOKEN = getenv('UPTOBOX_TOKEN', '')
    if len(UPTOBOX_TOKEN) == 0: 
        UPTOBOX_TOKEN = ''

    INDEX_URL = getenv('INDEX_URL', '').rstrip("/")
    if len(INDEX_URL) == 0: 
        INDEX_URL = ''

    SEARCH_API_LINK = getenv('SEARCH_API_LINK', '').rstrip("/")
    if len(SEARCH_API_LINK) == 0:   
        SEARCH_API_LINK = ''

    STATUS_UPDATE_INTERVAL = getenv('STATUS_UPDATE_INTERVAL', '')
    if len(STATUS_UPDATE_INTERVAL) == 0:
        STATUS_UPDATE_INTERVAL = 10
    else:
        STATUS_UPDATE_INTERVAL = int(STATUS_UPDATE_INTERVAL)
    if len(download_dict) != 0:
        with status_reply_dict_lock:
            try:
                if Interval:
                    Interval[0].cancel()
                    Interval.clear()
            except:
                pass
            finally:
                Interval.append(setInterval(STATUS_UPDATE_INTERVAL, update_all_messages))

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

    SEARCH_LIMIT = getenv('SEARCH_LIMIT', '')
    SEARCH_LIMIT = 0 if len(SEARCH_LIMIT) == 0 else int(SEARCH_LIMIT)

    CMD_PERFIX = getenv('CMD_PERFIX', '')

    TELEGRAM_HASH = getenv('TELEGRAM_HASH', '')

    TELEGRAM_API = getenv('TELEGRAM_API', '')

    USER_SESSION_STRING = getenv('USER_SESSION_STRING', '')

    TORRENT_TIMEOUT = getenv('TORRENT_TIMEOUT', '')
    downloads = aria2.get_downloads()
    if len(TORRENT_TIMEOUT) == 0:
        if downloads:
            aria2.set_options({'bt-stop-timeout': '0'}, downloads)
        aria2_options['bt-stop-timeout'] = '0'
    else:
        if downloads:
            aria2.set_options({'bt-stop-timeout': TORRENT_TIMEOUT}, downloads)
        aria2_options['bt-stop-timeout'] = TORRENT_TIMEOUT
        TORRENT_TIMEOUT = int(TORRENT_TIMEOUT)


    TORRENT_DIRECT_LIMIT = getenv('TORRENT_DIRECT_LIMIT', '')
    TORRENT_DIRECT_LIMIT = '' if len(TORRENT_DIRECT_LIMIT) == 0 else float(TORRENT_DIRECT_LIMIT)

    CLONE_LIMIT = getenv('CLONE_LIMIT', '')
    CLONE_LIMIT = '' if len(CLONE_LIMIT) == 0 else float(CLONE_LIMIT)

    LEECH_LIMIT = getenv('LEECH_LIMIT', '')
    LEECH_LIMIT = '' if len(LEECH_LIMIT) == 0 else float(LEECH_LIMIT)

    MEGA_LIMIT = getenv('MEGA_LIMIT', '')
    MEGA_LIMIT = '' if len(MEGA_LIMIT) == 0 else float(MEGA_LIMIT)

    STORAGE_THRESHOLD = getenv('STORAGE_THRESHOLD', '')
    STORAGE_THRESHOLD = '' if len(STORAGE_THRESHOLD) == 0 else float(STORAGE_THRESHOLD)

    ZIP_UNZIP_LIMIT = getenv('ZIP_UNZIP_LIMIT', '')
    ZIP_UNZIP_LIMIT = '' if len(ZIP_UNZIP_LIMIT) == 0 else float(ZIP_UNZIP_LIMIT)

    TOTAL_TASKS_LIMIT = getenv('TOTAL_TASKS_LIMIT', '')
    TOTAL_TASKS_LIMIT = '' if len(TOTAL_TASKS_LIMIT) == 0 else int(TOTAL_TASKS_LIMIT)

    USER_TASKS_LIMIT = getenv('USER_TASKS_LIMIT', '')
    USER_TASKS_LIMIT = '' if len(USER_TASKS_LIMIT) == 0 else int(USER_TASKS_LIMIT)


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

    AS_DOCUMENT = getenv('AS_DOCUMENT', '')
    AS_DOCUMENT = AS_DOCUMENT.lower() == 'true'

    EQUAL_SPLITS = getenv('EQUAL_SPLITS', '')
    EQUAL_SPLITS = EQUAL_SPLITS.lower() == 'true'

    IGNORE_PENDING_REQUESTS = getenv('IGNORE_PENDING_REQUESTS', '')
    IGNORE_PENDING_REQUESTS = IGNORE_PENDING_REQUESTS.lower() == 'true'

    RSS_CHAT_ID = getenv('RSS_CHAT_ID', '')
    RSS_CHAT_ID = '' if len(RSS_CHAT_ID) == 0 else int(RSS_CHAT_ID)

    RSS_DELAY = getenv('RSS_DELAY', '')
    RSS_DELAY = 900 if len(RSS_DELAY) == 0 else int(RSS_DELAY)

    RSS_COMMAND = getenv('RSS_COMMAND', '')
    if len(RSS_COMMAND) == 0:
        RSS_COMMAND = ''

    SERVER_PORT = getenv('SERVER_PORT', '')
    SERVER_PORT = 80 if len(SERVER_PORT) == 0 else int(SERVER_PORT)

    DRIVES_IDS.clear()
    DRIVES_NAMES.clear()
    INDEX_URLS.clear()

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

    SEARCH_PLUGINS = getenv('SEARCH_PLUGINS', '')
    if len(SEARCH_PLUGINS) == 0:
        SEARCH_PLUGINS = ''

    UPSTREAM_REPO = getenv('UPSTREAM_REPO', '')
    if len(UPSTREAM_REPO) == 0: 
        UPSTREAM_REPO = 'https://github.com/weebzone/WZML'

    UPSTREAM_BRANCH = getenv('UPSTREAM_BRANCH', '')
    if len(UPSTREAM_BRANCH) == 0:   
        UPSTREAM_BRANCH = 'master'


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
        BUTTON_FOUR_NAME = ''
        BUTTON_FOUR_URL = ''

    BUTTON_FIVE_NAME = getenv('BUTTON_FIVE_NAME', '')
    BUTTON_FIVE_URL = getenv('BUTTON_FIVE_URL', '')
    if len(BUTTON_FIVE_NAME) == 0 or len(BUTTON_FIVE_URL) == 0: 
        BUTTON_FIVE_NAME = ''
        BUTTON_FIVE_URL = ''

    BUTTON_SIX_NAME = getenv('BUTTON_SIX_NAME', '')
    BUTTON_SIX_URL = getenv('BUTTON_SIX_URL', '')
    if len(BUTTON_SIX_NAME) == 0 or len(BUTTON_SIX_URL) == 0:   
        BUTTON_SIX_NAME = ''
        BUTTON_SIX_URL = ''

    SHORTENER = getenv('SHORTENER', '')
    SHORTENER_API = getenv('SHORTENER_API', '')
    if len(SHORTENER) == 0 or len(SHORTENER_API) == 0:  
        SHORTENER = ''
        SHORTENER_API = ''

    CRYPT = getenv('CRYPT', '')
    if len(CRYPT) == 0: 
        CRYPT = ''

    UNIFIED_EMAIL = getenv('UNIFIED_EMAIL', '')
    if len(UNIFIED_EMAIL) == 0: 
        UNIFIED_EMAIL = ''

    UNIFIED_PASS = getenv('UNIFIED_PASS', '')
    if len(UNIFIED_PASS) == 0:  
        UNIFIED_PASS = ''

    HUBDRIVE_CRYPT = getenv('HUBDRIVE_CRYPT', '')
    if len(HUBDRIVE_CRYPT) == 0:    
        HUBDRIVE_CRYPT = ''

    KATDRIVE_CRYPT = getenv('KATDRIVE_CRYPT', '')
    if len(KATDRIVE_CRYPT) == 0:    
        KATDRIVE_CRYPT = ''

    DRIVEFIRE_CRYPT = getenv('DRIVEFIRE_CRYPT', '')
    if len(DRIVEFIRE_CRYPT) == 0:   
        DRIVEFIRE_CRYPT = ''

    MIRROR_LOG_URL = getenv('MIRROR_LOG_URL', '')
    if len(MIRROR_LOG_URL) == 0:    
        MIRROR_LOG_URL = ''

    LEECH_LOG_URL = getenv('LEECH_LOG_URL', '')
    if len(LEECH_LOG_URL) == 0: 
        LEECH_LOG_URL = ''

    TIME_GAP = getenv('TIME_GAP', '')
    if len(TIME_GAP) == 0:  
        TIME_GAP = -1
    else:   
        TIME_GAP = int(TIME_GAP)

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
        CHANNEL_USERNAME = 'WeebZone_updates'

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
        PIXABAY_API_KEY = ''

    PIXABAY_CATEGORY = getenv('PIXABAY_CATEGORY', '')
    if len(PIXABAY_CATEGORY) == 0:
        PIXABAY_CATEGORY = ''

    PIXABAY_SEARCH = getenv('PIXABAY_SEARCH', '')
    if len(PIXABAY_SEARCH) == 0:
        PIXABAY_SEARCH = ''

    WALLFLARE_SEARCH = getenv('WALLFLARE_SEARCH', '')
    if len(WALLFLARE_SEARCH) == 0:
        WALLFLARE_SEARCH = ''

    WALLTIP_SEARCH = getenv('WALLTIP_SEARCH', '')
    if len(WALLTIP_SEARCH) == 0:
        WALLTIP_SEARCH = ''

    WALLCRAFT_CATEGORY = getenv('WALLCRAFT_CATEGORY', '')
    if len(WALLCRAFT_CATEGORY) == 0:
        WALLCRAFT_CATEGORY = ''

    PICS = (getenv('PICS', '')).split()

    YT_DLP_QUALITY = getenv('YT_DLP_QUALITY', '')
    if len(YT_DLP_QUALITY) == 0:
        YT_DLP_QUALITY = ''

    BASE_URL = getenv('BASE_URL', '').rstrip("/")
    if len(BASE_URL) == 0:
        BASE_URL = ''
        srun(["pkill", "-9", "-f", "gunicorn"])
    else:
        srun(["pkill", "-9", "-f", "gunicorn"])
        Popen(f"gunicorn web.wserver:app --bind 0.0.0.0:{SERVER_PORT}", shell=True)

    initiate_search_tools()

    config_dict.update({'AS_DOCUMENT': AS_DOCUMENT,
                   'AUTHORIZED_CHATS': AUTHORIZED_CHATS,
                   'AUTO_DELETE_MESSAGE_DURATION': AUTO_DELETE_MESSAGE_DURATION,
                   'AUTO_DELETE_UPLOAD_MESSAGE_DURATION': AUTO_DELETE_UPLOAD_MESSAGE_DURATION,
                   'BASE_URL': BASE_URL,
                   'CMD_PERFIX': CMD_PERFIX,
                   'EQUAL_SPLITS': EQUAL_SPLITS,
                   'EXTENSION_FILTER': EXTENSION_FILTER,
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
                   'VIEW_LINK': VIEW_LINK,
                   'LEECH_ENABLED': LEECH_ENABLED,
                   'MIRROR_ENABLED': MIRROR_ENABLED,
                   'WATCH_ENABLED': WATCH_ENABLED,
                   'CLONE_ENABLED': CLONE_ENABLED,
                   'ANILIST_ENABLED': ANILIST_ENABLED,
                   'WAYBACK_ENABLED': WAYBACK_ENABLED,
                   'MEDIAINFO_ENABLED': MEDIAINFO_ENABLED,
                   'SET_BOT_COMMANDS': SET_BOT_COMMANDS,
                   'BOT_PM': BOT_PM,
                   'FORCE_BOT_PM': FORCE_BOT_PM,
                   'LEECH_LOG': LEECH_LOG,
                   'LEECH_LOG_URL': LEECH_LOG_URL,
                   'LEECH_LOG_INDEXING': LEECH_LOG_INDEXING,
                   'PAID_SERVICE': PAID_SERVICE,
                   'MIRROR_LOGS': MIRROR_LOGS,
                   'MIRROR_LOG_URL': MIRROR_LOG_URL,
                   'LINK_LOGS': LINK_LOGS,
                   'TIMEZONE': TIMEZONE,
                   'TITLE_NAME': TITLE_NAME,
                   'AUTHOR_NAME': AUTHOR_NAME,
                   'AUTHOR_URL': AUTHOR_URL,
                   'GD_INFO': GD_INFO,
                   'FSUB': FSUB,
                   'CHANNEL_USERNAME': CHANNEL_USERNAME,
                   'FSUB_CHANNEL_ID': FSUB_CHANNEL_ID,
                   'SHORTENER': SHORTENER,
                   'SHORTENER_API': SHORTENER_API,
                   'CRYPT': CRYPT,
                   'UNIFIED_EMAIL': UNIFIED_EMAIL,
                   'UNIFIED_PASS': UNIFIED_PASS,
                   'HUBDRIVE_CRYPT': HUBDRIVE_CRYPT,
                   'KATDRIVE_CRYPT': KATDRIVE_CRYPT,
                   'DRIVEFIRE_CRYPT': DRIVEFIRE_CRYPT,
                   'TOTAL_TASKS_LIMIT': TOTAL_TASKS_LIMIT,
                   'USER_TASKS_LIMIT': USER_TASKS_LIMIT,
                   'STORAGE_THRESHOLD': STORAGE_THRESHOLD,
                   'TORRENT_DIRECT_LIMIT': TORRENT_DIRECT_LIMIT,
                   'ZIP_UNZIP_LIMIT': ZIP_UNZIP_LIMIT,
                   'CLONE_LIMIT': CLONE_LIMIT,
                   'LEECH_LIMIT': LEECH_LIMIT,
                   'MEGA_LIMIT': MEGA_LIMIT,
                   'TIME_GAP': TIME_GAP,
                   'FINISHED_PROGRESS_STR': FINISHED_PROGRESS_STR,
                   'UN_FINISHED_PROGRESS_STR': UN_FINISHED_PROGRESS_STR,
                   'EMOJI_THEME': EMOJI_THEME,
                   'SHOW_LIMITS_IN_STATS': SHOW_LIMITS_IN_STATS,
                   'TELEGRAPH_STYLE': TELEGRAPH_STYLE,
                   'CREDIT_NAME': CREDIT_NAME,
                   'WALLFLARE_SEARCH': WALLFLARE_SEARCH,
                   'WALLTIP_SEARCH': WALLTIP_SEARCH,
                   'WALLCRAFT_CATEGORY': WALLCRAFT_CATEGORY,
                   'PIXABAY_API_KEY': PIXABAY_API_KEY,
                   'PIXABAY_CATEGORY': PIXABAY_CATEGORY,
                   'PIXABAY_SEARCH': PIXABAY_SEARCH,
                   'NAME_FONT': NAME_FONT,
                   'CAPTION_FONT': CAPTION_FONT,
                   'DISABLE_DRIVE_LINK': DISABLE_DRIVE_LINK,
                   'SOURCE_LINK': SOURCE_LINK,
                   'START_BTN1_NAME': START_BTN1_NAME,
                   'START_BTN1_URL': START_BTN1_URL,
                   'START_BTN2_NAME': START_BTN2_NAME,
                   'START_BTN2_URL': START_BTN2_URL,
                   'BUTTON_FOUR_NAME': BUTTON_FOUR_NAME,
                   'BUTTON_FOUR_URL': BUTTON_FOUR_URL,
                   'BUTTON_FIVE_NAME': BUTTON_FIVE_NAME,
                   'BUTTON_FIVE_URL': BUTTON_FIVE_URL,
                   'BUTTON_SIX_NAME': BUTTON_SIX_NAME,
                   'BUTTON_SIX_URL': TELEGRAPH_STYLE,
                   'WEB_PINCODE': WEB_PINCODE,
                   'YT_DLP_QUALITY': YT_DLP_QUALITY})


    if DB_URI:
        DbManger().update_config(config_dict)



def get_buttons(key=None, edit_type=None):
    buttons = ButtonMaker()
    if key is None:
        buttons.sbutton('Edit Variables', "botset var")
        buttons.sbutton('Private Files', "botset private")
        buttons.sbutton('Qbit Settings', "botset qbit")
        buttons.sbutton('Aria2c Settings', "botset aria")
        buttons.sbutton('Close', "botset close")
        msg = 'Bot Settings:'
    elif key == 'var':
        for k in list(config_dict.keys())[START:10+START]:
            buttons.sbutton(k, f"botset editvar {k}")
        if STATE == 'view':
            buttons.sbutton('Edit', "botset edit var")
        else:
            buttons.sbutton('View', "botset view var")
        buttons.sbutton('Back', "botset back")
        buttons.sbutton('Close', "botset close")
        for x in range(0, len(config_dict)-1, 10):
            buttons.sbutton(int(x/10), f"botset start var {x}", position='footer')
        msg = f'Bot Variables. Page: {int(START/10)}. State: {STATE}'
    elif key == 'private':
        buttons.sbutton('Back', "botset back")
        buttons.sbutton('Close', "botset close")
        msg = f'Send private file: config.env, token.pickle, accounts.zip, list_drives.txt, cookies.txt or .netrc.\nTimeout: 60 sec'
    elif key == 'aria':
        for k in list(aria2_options.keys())[START:10+START]:
            buttons.sbutton(k, f"botset editaria {k}")
        if STATE == 'view':
            buttons.sbutton('Edit', "botset edit aria")
        else:
            buttons.sbutton('View', "botset view aria")
        buttons.sbutton('Add new key', "botset editaria newkey")
        buttons.sbutton('Back', "botset back")
        buttons.sbutton('Close', "botset close")
        for x in range(0, len(aria2_options)-1, 10):
            buttons.sbutton(int(x/10), f"botset start aria {x}", position='footer')
        msg = f'Aria2c Options. Page: {int(START/10)}. State: {STATE}'
    elif key == 'qbit':
        for k in list(qbit_options.keys())[START:10+START]:
            buttons.sbutton(k, f"botset editqbit {k}")
        if STATE == 'view':
            buttons.sbutton('Edit', "botset edit qbit")
        else:
            buttons.sbutton('View', "botset view qbit")
        buttons.sbutton('Back', "botset back")
        buttons.sbutton('Close', "botset close")
        for x in range(0, len(qbit_options)-1, 10):
            buttons.sbutton(int(x/10), f"botset start qbit {x}", position='footer')
        msg = f'Qbittorrent Options. Page: {int(START/10)}. State: {STATE}'
    elif edit_type == 'editvar':
        buttons.sbutton('Back', "botset back var")
        if key not in ['TELEGRAM_HASH', 'TELEGRAM_API']:
            buttons.sbutton('Default', f"botset resetvar {key}")
        buttons.sbutton('Close', "botset close")
        msg = f'Send a valid value for {key}. Timeout: 60 sec'
    elif edit_type == 'editaria':
        buttons.sbutton('Back', "botset back aria")
        if key != 'newkey':
            buttons.sbutton('Default', f"botset resetaria {key}")
        buttons.sbutton('Close', "botset close")
        if key == 'newkey':
            msg = 'Send a key with value. Example: https-proxy-user:value'
        else:
            msg = f'Send a valid value for {key}. Timeout: 60 sec'
    elif edit_type == 'editqbit':
        buttons.sbutton('Back', "botset back qbit")
        buttons.sbutton('Close', "botset close")
        msg = f'Send a valid value for {key}. Timeout: 60 sec'
    return msg, buttons.build_menu(2)

def update_buttons(message, key=None, edit_type=None):
    msg, button = get_buttons(key, edit_type)
    editMessage(msg, message, button)

def edit_variable(update, context, omsg, key):
    handler_dict[omsg.chat.id] = False
    value = update.message.text
    if value.lower() == 'true':
        value = True
    elif value.lower() == 'false':
        value = False
    elif key == 'STATUS_UPDATE_INTERVAL':
        value = int(value)
        if len(download_dict) != 0:
            with status_reply_dict_lock:
                if Interval:
                    Interval[0].cancel()
                    Interval.clear()
                    Interval.append(setInterval(value, update_all_messages))
    elif key == 'TORRENT_TIMEOUT':
        value = int(value)
        downloads = aria2.get_downloads()
        if downloads:
            aria2.set_options({'bt-stop-timeout': f'{value}'}, downloads)
        aria2_options['bt-stop-timeout'] = f'{value}'
    elif key == 'TG_SPLIT_SIZE':
        value = min(int(value), tgBotMaxFileSize)
    elif key == 'SERVER_PORT':
        value = int(value)
        srun(["pkill", "-9", "-f", "gunicorn"])
        Popen(f"gunicorn web.wserver:app --bind 0.0.0.0:{value}", shell=True)
    elif key == 'EXTENSION_FILTER':
        fx = value.split()
        GLOBAL_EXTENSION_FILTER.clear()
        GLOBAL_EXTENSION_FILTER.append('.aria2')
        for x in fx:
            GLOBAL_EXTENSION_FILTER.append(x.strip().lower())
    elif key in ['SEARCH_PLUGINS', 'SEARCH_API_LINK']:
        initiate_search_tools()
    elif key == 'GDRIVE_ID':
        if DRIVES_NAMES and DRIVES_NAMES[0] == 'Main':
            DRIVES_IDS[0] = value
        else:
            DRIVES_IDS.insert(0, value)
    elif key == 'INDEX_URL':
        if DRIVES_NAMES and DRIVES_NAMES[0] == 'Main':
            INDEX_URLS[0] = value
        else:
            INDEX_URLS.insert(0, value)
    elif value.isdigit():
        value = int(value)
    config_dict[key] = value
    update_buttons(omsg, 'var')
    update.message.delete()
    if DB_URI:
        DbManger().update_config({key: value})

def edit_aria(update, context, omsg, key):
    handler_dict[omsg.chat.id] = False
    value = update.message.text
    if key == 'newkey':
        key, value = [x.strip() for x in value.split(':', 1)]
    elif value.lower() == 'true':
        value = "true"
    elif value.lower() == 'false':
        value = "false"
    if key in aria2c_global:
        aria2.set_global_options({key: value})
    else:
        downloads = aria2.get_downloads()
        if downloads:
            aria2.set_options({key: value}, downloads)
    aria2_options[key] = value
    update_buttons(omsg, 'aria')
    update.message.delete()
    if DB_URI:
        DbManger().update_aria2(key, value)


def edit_qbit(update, context, omsg, key):
    handler_dict[omsg.chat.id] = False
    value = update.message.text
    if value.lower() == 'true':
        value = True
    elif value.lower() == 'false':
        value = False
    elif key == 'max_ratio':
        value = float(value)
    elif value.isdigit():
        value = int(value)
    client = get_client()
    client.app_set_preferences({key: value})
    qbit_options[key] = value
    update_buttons(omsg, 'qbit')
    update.message.delete()
    if DB_URI:
        DbManger().update_qbittorrent(key, value)

def upload_file(update, context, omsg):
    handler_dict[omsg.chat.id] = False
    doc = update.message.document
    file_name = doc.file_name
    doc.get_file().download(custom_path=file_name)
    if file_name == 'accounts.zip':
        srun(["unzip", "-q", "-o", "accounts.zip"])
        srun(["chmod", "-R", "777", "accounts"])
    elif file_name == 'list_drives.txt':
        DRIVES_IDS.clear()
        DRIVES_NAMES.clear()
        INDEX_URLS.clear()
        if GDRIVE_ID := config_dict['GDRIVE_ID']:
            DRIVES_NAMES.append("Main")
            DRIVES_IDS.append(GDRIVE_ID)
            INDEX_URLS.append(config_dict['INDEX_URL'])
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
    elif file_name in ['.netrc', 'netrc']:
        if file_name == 'netrc':
            rename('netrc', '.netrc')
            file_name = '.netrc'
        srun(["cp", ".netrc", "/root/.netrc"])
        srun(["chmod", "600", ".netrc"])
    elif file_name == 'config.env':
        load_dotenv('config.env', override=True)
        load_config()
    if '@github.com' in config_dict['UPSTREAM_REPO']:
        buttons = ButtonMaker()
        msg = 'Push to UPSTREAM_REPO ?'
        buttons.sbutton('Yes!', f"botset push {file_name}")
        buttons.sbutton('No', "botset close")
        sendMarkup(msg, context.bot, update.message, buttons.build_menu(2))
    else:
        update.message.delete()
    update_buttons(omsg)
    if DB_URI:
        DbManger().update_private_file(file_name)
    if ospath.exists('accounts.zip'):
        remove('accounts.zip')

@new_thread
def edit_bot_settings(update, context):
    query = update.callback_query
    message = query.message
    user_id = query.from_user.id
    data = query.data
    data = data.split()
    if not CustomFilters.owner_query(user_id):
        query.answer(text="You don't have premision to use these buttons!", show_alert=True)
    elif data[1] == 'close':
        query.answer()
        handler_dict[message.chat.id] = False
        query.message.delete()
        query.message.reply_to_message.delete()
    elif data[1] == 'back':
        query.answer()
        handler_dict[message.chat.id] = False
        key = data[2] if len(data) == 3 else None
        update_buttons(message, key)
    elif data[1] == 'var':
        query.answer()
        update_buttons(message, data[1])
    elif data[1] == 'resetvar':
        query.answer()
        value = ''
        if data[2] in default_values:
            value = default_values[data[2]]
        elif data[2] == 'EXTENSION_FILTER':
            GLOBAL_EXTENSION_FILTER.clear()
            GLOBAL_EXTENSION_FILTER.append('.aria2')
        elif data[2] == 'TORRENT_TIMEOUT':
            downloads = aria2.get_downloads()
            if downloads:
                aria2.set_options({'bt-stop-timeout': '0'}, downloads)
            aria2_options['bt-stop-timeout'] = '0'
        elif data[2] == 'BASE_URL':
            srun(["pkill", "-9", "-f", "gunicorn"])
        elif data[2] == 'SERVER_PORT':
            value = 80
            srun(["pkill", "-9", "-f", "gunicorn"])
            Popen("gunicorn web.wserver:app --bind 0.0.0.0:80", shell=True)
        elif data[2] == 'GDRIVE_ID':
            if DRIVES_NAMES and DRIVES_NAMES[0] == 'Main':
                DRIVES_NAMES.pop(0)
                DRIVES_IDS.pop(0)
                INDEX_URLS.pop(0)
        elif data[2] == 'INDEX_URL':
            if DRIVES_NAMES and DRIVES_NAMES[0] == 'Main':
                INDEX_URLS[0] = ''
        config_dict[data[2]] = value
        update_buttons(message, 'var')
        if DB_URI:
            DbManger().update_config({data[2]: value})
        update_buttons(message, 'var')
    elif data[1] == 'resetaria':
        aria2_defaults = aria2.client.get_global_option()
        if aria2_defaults[data[2]] == aria2_options[data[2]]:
            query.answer(text='Value already same as you added in aria.sh!')
            return
        query.answer()
        value = aria2_defaults[data[2]]
        aria2_options[data[2]] = value
        if DB_URI:
            DbManger().update_aria2(data[2], value)
    elif data[1] == 'private':
        query.answer()
        if handler_dict.get(message.chat.id):
            handler_dict[message.chat.id] = False
            sleep(0.5)
        start_time = time()
        handler_dict[message.chat.id] = True
        update_buttons(message, 'private')
        partial_fnc = partial(upload_file, omsg=message)
        file_handler = MessageHandler(filters=Filters.document & Filters.chat(message.chat.id) & Filters.user(user_id),
                                      callback=partial_fnc, run_async=True)
        dispatcher.add_handler(file_handler)
        while handler_dict[message.chat.id]:
            if time() - start_time > 60:
                handler_dict[message.chat.id] = False
                update_buttons(message)
        dispatcher.remove_handler(file_handler)
    elif data[1] == 'editvar' and STATE == 'edit':
        if data[2] in ['SUDO_USERS', 'RSS_USER_SESSION_STRING', 'IGNORE_PENDING_REQUESTS', 'CMD_PERFIX',
                       'USER_SESSION_STRING', 'TELEGRAM_HASH', 'TELEGRAM_API', 'AUTHORIZED_CHATS', 'RSS_DELAY']:
            query.answer(text='Restart required for this edit to take effect!', show_alert=True)
        else:
            query.answer()
        if handler_dict.get(message.chat.id):
            handler_dict[message.chat.id] = False
            sleep(0.5)
        start_time = time()
        handler_dict[message.chat.id] = True
        update_buttons(message, data[2], data[1])
        partial_fnc = partial(edit_variable, omsg=message, key=data[2])
        value_handler = MessageHandler(filters=Filters.text & Filters.chat(message.chat.id) & Filters.user(user_id),
                                       callback=partial_fnc, run_async=True)
        dispatcher.add_handler(value_handler)
        while handler_dict[message.chat.id]:
            if time() - start_time > 60:
                handler_dict[message.chat.id] = False
                update_buttons(message, 'var')
        dispatcher.remove_handler(value_handler)
    elif data[1] == 'editvar' and STATE == 'view':
        value = config_dict[data[2]]
        if len(str(value)) > 200:
            query.answer()
            filename = f"{data[2]}.txt"
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(f'{value}')
            sendFile(context.bot, message, filename)
            return
        elif value == '':
            value = None
        query.answer(text=f'{value}', show_alert=True)
    elif data[1] == 'editaria' and (STATE == 'edit' or data[2] == 'newkey'):
        query.answer()
        if handler_dict.get(message.chat.id):
            handler_dict[message.chat.id] = False
            sleep(0.5)
        start_time = time()
        handler_dict[message.chat.id] = True
        update_buttons(message, data[2], data[1])
        partial_fnc = partial(edit_aria, omsg=message, key=data[2])
        value_handler = MessageHandler(filters=Filters.text & Filters.chat(message.chat.id) &
                        (CustomFilters.owner_filter | CustomFilters.sudo_user), callback=partial_fnc, run_async=True)
        dispatcher.add_handler(value_handler)
        while handler_dict[message.chat.id]:
            if time() - start_time > 60:
                handler_dict[message.chat.id] = False
                update_buttons(message, 'aria')
        dispatcher.remove_handler(value_handler)
    elif data[1] == 'editaria' and STATE == 'view':
        value = aria2_options[data[2]]
        if len(value) > 200:
            query.answer()
            filename = f"{data[2]}.txt"
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(f'{value}')
            sendFile(context.bot, message, filename)
            return
        elif value == '':
            value = None
        query.answer(text=f'{value}', show_alert=True)
    elif data[1] == 'editqbit' and STATE == 'edit':
        query.answer()
        if handler_dict.get(message.chat.id):
            handler_dict[message.chat.id] = False
            sleep(0.5)
        start_time = time()
        handler_dict[message.chat.id] = True
        update_buttons(message, data[2], data[1])
        partial_fnc = partial(edit_qbit, omsg=message, key=data[2])
        value_handler = MessageHandler(filters=Filters.text & Filters.chat(message.chat.id) &
                        (CustomFilters.owner_filter | CustomFilters.sudo_user), callback=partial_fnc, run_async=True)
        dispatcher.add_handler(value_handler)
        while handler_dict[message.chat.id]:
            if time() - start_time > 60:
                handler_dict[message.chat.id] = False
                update_buttons(message, 'var')
        dispatcher.remove_handler(value_handler)
    elif data[1] == 'editqbit' and STATE == 'view':
        value = qbit_options[data[2]]
        if len(str(value)) > 200:
            query.answer()
            filename = f"{data[2]}.txt"
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(f'{value}')
            sendFile(context.bot, message, filename)
            return
        elif value == '':
            value = None
        query.answer(text=f'{value}', show_alert=True)
    elif data[1] == 'edit':
        query.answer()
        globals()['STATE'] = 'edit'
        update_buttons(message, data[2])
    elif data[1] == 'view':
        query.answer()
        globals()['STATE'] = 'view'
        update_buttons(message, data[2])
    elif data[1] == 'start':
        query.answer()
        if START != int(data[3]):
            globals()['START'] = int(data[3])
            update_buttons(message, data[2])
    elif data[1] == 'push':
        query.answer()
        srun([f"git add -f {data[2]} \
                && git commit -sm botsettings -q \
                && git push origin {config_dict['UPSTREAM_BRANCH']} -q"], shell=True)
        query.message.delete()
        query.message.reply_to_message.delete()

def bot_settings(update, context):
    msg, button = get_buttons()
    sendMarkup(msg, context.bot, update.message, button)


bot_settings_handler = CommandHandler(BotCommands.BotSetCommand, bot_settings,
                                      filters=CustomFilters.owner_filter | CustomFilters.sudo_user, run_async=True)
bb_set_handler = CallbackQueryHandler(edit_bot_settings, pattern="botset", run_async=True)

dispatcher.add_handler(bot_settings_handler)
dispatcher.add_handler(bb_set_handler)
