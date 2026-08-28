from ast import literal_eval
from importlib import import_module
from os import getenv
from wz_bin import bin_name


class Config:
    ALLDEBRID_API_KEY = ""
    ALLDEBRID_NO_SEED_TIMEOUT = 180
    AS_DOCUMENT = False
    AUTHORIZED_CHATS = ""
    BASE_URL = ""
    BOT_TOKEN = ""
    HELPER_TOKENS = ""
    HELPER_STRINGS = ""
    STREAM_TOKENS = ""
    HELPER_BOT_PROXIES = ""
    HELPER_USER_PROXIES = ""
    BOT_MAX_TASKS = 0
    BOT_PM = False
    CMD_SUFFIX = ""
    DEFAULT_LANG = "en"
    DATABASE_URL = ""
    DEFAULT_UPLOAD = "rc"
    DELETE_LINKS = False
    DEBRID_LINK_API = ""
    DISABLE_TORRENTS = False
    DISABLE_LEECH = False
    DISABLE_MIRROR = False
    DISABLE_BULK = False
    DISABLE_MULTI = False
    DISABLE_SEED = False
    DISABLE_FF_MODE = False
    DISABLE_MEGA = False
    DISABLE_PLUGINS = False
    DISABLE_JD = True
    DISABLE_NZB = True
    DISABLE_SEEDR = True
    DISABLE_RSS = False
    DISABLE_SEARCH = False
    DISABLE_STREAM = False
    DISABLE_YTDLP = False
    PLUGIN_INDEXES = []
    EQUAL_SPLITS = False
    EXCLUDED_EXTENSIONS = ""
    FFMPEG_CMDS = {}
    FILELION_API = ""
    MEDIA_STORE = True
    FORCE_SUB_IDS = ""
    GOFILE_API = ""
    GOFILE_FOLDER_ID = ""
    GOFILE_AUTO_CREATE_FOLDER = False
    PIXELDRAIN_KEY = ""
    PROTECTED_API = ""
    BUZZHEAVIER_API = ""
    DEVUPLOADS_KEY = ""
    DEVUPLOADS_FOLDER = ""
    VIKINGFILE_HASH = ""
    VIKINGFILE_FOLDER = ""
    GDRIVE_ID = ""
    GD_DESP = "Uploaded with WZ Bot"
    AUTHOR_NAME = "WZML-X"
    AUTHOR_URL = "https://t.me/WZML_X"
    INSTADL_API = ""
    IMDB_TEMPLATE = ""
    IMAGES = []
    IMG_SEARCH = ""
    IMG_PAGE = 1
    USE_IMAGES = False
    IMG_SOURCES = ["wallpaperflare"]
    INC_TASK_NOTIFY = False
    INC_TASK_RESUME = False
    INDEX_URL = ""
    IS_TEAM_DRIVE = False
    JD_EMAIL = ""
    JD_PASS = ""
    MEGA_EMAIL = ""
    MEGA_PASSWORD = ""
    SEEDR_EMAIL = ""
    SEEDR_PASSWORD = ""
    SEEDR_DELETE_FOLDER = False
    DIRECT_LIMIT = 0
    MEGA_LIMIT = 0
    TORRENT_LIMIT = 0
    GD_DL_LIMIT = 0
    RC_DL_LIMIT = 0
    CLONE_LIMIT = 0
    JD_LIMIT = 0
    NZB_LIMIT = 0
    SEEDR_LIMIT = 0
    YTDLP_LIMIT = 0
    PLAYLIST_LIMIT = 0
    LEECH_LIMIT = 0
    EXTRACT_LIMIT = 0
    ARCHIVE_LIMIT = 0
    STORAGE_LIMIT = 0
    LEECH_LOG_CHAT = ""
    LEECH_DUMP_CHATS = {}
    LINKS_LOG_ID = ""
    MIRROR_LOG_ID = ""
    LEECH_PREFIX = ""
    LEECH_CAPTION = ""
    LEECH_SUFFIX = ""
    LEECH_FONT = ""
    LEECH_SPLIT_SIZE = 2097152000
    MEDIA_GROUP = False
    USE_HYPER = True
    HYPER_THREADS = 0
    HYPER_PIPELINE = 4
    HYPER_CHUNK = 512 * 1024
    MEM_BUDGET = 0
    MEM_DEEP_STATS = False
    STREAM_PIPELINE = 8
    STREAM_CHUNK = 1048576
    STREAM_PER_CLIENT = 6
    STREAM_GATE = 96
    CPU_LIMIT = 20
    FFMPEG_CORES = "auto"
    THROTTLE_SERVICES = "auto"
    HYDRA_IP = ""
    HYDRA_API_KEY = ""
    NAME_SWAP = ""
    OWNER_ID = 0
    QUEUE_ALL = 0
    QUEUE_DOWNLOAD = 0
    QUEUE_UPLOAD = 0
    RCLONE_FLAGS = ""
    RCLONE_PATH = ""
    RCLONE_SERVE_URL = ""
    SHOW_CLOUD_LINK = True
    RCLONE_SERVE_USER = ""
    RCLONE_SERVE_PASS = ""
    RCLONE_SERVE_PORT = 8081
    RSS_CHAT = ""
    RSS_DELAY = 600
    RSS_SIZE_LIMIT = 0
    SEARCH_API_LINK = ""
    SEARCH_LIMIT = 0
    SEARCH_PLUGINS = []
    SET_COMMANDS = True
    STATUS_LIMIT = 10
    STATUS_UPDATE_INTERVAL = 15
    STOP_DUPLICATE = False
    STREAMWISH_API = ""
    SUDO_USERS = ""
    TELEGRAM_API = 0
    TELEGRAM_HASH = ""
    TG_PROXY = None
    THUMBNAIL_LAYOUT = ""
    TMDB_ACCESS_TOKEN = ""
    AUTO_THUMBNAIL = False
    VERIFY_TIMEOUT = 0
    LOGIN_PASS = ""
    TORRENT_TIMEOUT = 0
    TIMEZONE = "Asia/Kolkata"
    USER_MAX_TASKS = 0
    USER_TIME_INTERVAL = 0
    UPLOAD_PATHS = {}
    DRIVE_CATEGORY_MODE = False
    DRIVE_CATEGORY_SA = ""
    UPSTREAM_REPO = ""
    UPSTREAM_BRANCH = "master"
    USENET_SERVERS = []
    USER_SESSION_STRING = ""
    TRANSMISSION_MODE = "both"
    USE_SERVICE_ACCOUNTS = False
    ENABLE_TELEMETRY = True
    WEB_ACCESS_PASSWORD = ""
    WEB_PINCODE = True
    YT_DLP_OPTIONS = {}
    YT_DESP = "Uploaded with WZML-X bot"
    YT_TAGS = ["telegram", "bot", "youtube"]
    YT_CATEGORY_ID = 22
    YT_PRIVACY_STATUS = "unlisted"

    @classmethod
    def get(cls, key):
        return getattr(cls, key) if hasattr(cls, key) else None

    @classmethod
    def set(cls, key, value):
        if hasattr(cls, key):
            value = cls._convert_env_type(key, value)
            setattr(cls, key, value)
        else:
            raise KeyError(f"{key} is not a valid configuration key.")

    @classmethod
    def get_all(cls):
        return {
            key: getattr(cls, key)
            for key in cls.__dict__.keys()
            if not key.startswith("__") and not callable(getattr(cls, key))
        }

    @classmethod
    def load(cls):
        cls.load_config()
        cls.load_env()

    @classmethod
    def load_config(cls):
        try:
            settings = import_module("config")
        except ModuleNotFoundError:
            return
        for attr in dir(settings):
            if hasattr(cls, attr):
                value = getattr(settings, attr)
                if not value:
                    continue
                if isinstance(value, str):
                    value = value.strip()
                if attr == "DEFAULT_UPLOAD" and value != "gd":
                    value = "rc"
                elif attr in [
                    "BASE_URL",
                    "RCLONE_SERVE_URL",
                    "INDEX_URL",
                    "SEARCH_API_LINK",
                ]:
                    if value:
                        value = value.strip("/")
                elif attr == "USENET_SERVERS":
                    try:
                        if not value[0].get("host"):
                            continue
                    except Exception:
                        continue
                setattr(cls, attr, value)
        if hasattr(settings, "LEECH_DUMP_CHAT"):
            legacy_value = getattr(settings, "LEECH_DUMP_CHAT")
            if legacy_value and not cls.LEECH_LOG_CHAT:
                if isinstance(legacy_value, str):
                    legacy_value = legacy_value.strip()
                cls.LEECH_LOG_CHAT = legacy_value
        for key in ["BOT_TOKEN", "OWNER_ID", "TELEGRAM_API", "TELEGRAM_HASH"]:
            value = getattr(cls, key)
            if isinstance(value, str):
                value = value.strip()
            if not value:
                raise ValueError(f"{key} variable is missing!")

    @classmethod
    def load_env(cls):
        legacy_dump_chat = getenv("LEECH_DUMP_CHAT")
        if legacy_dump_chat is not None and getenv("LEECH_LOG_CHAT") is None:
            cls.LEECH_LOG_CHAT = cls._convert_env_type(
                "LEECH_LOG_CHAT", legacy_dump_chat
            )
        config_vars = cls.get_all()
        for key in config_vars:
            env_value = getenv(key)
            if env_value is not None:
                converted_value = cls._convert_env_type(key, env_value)
                cls.set(key, converted_value)

    @classmethod
    def _convert_env_type(cls, key, value):
        original_value = getattr(cls, key, None)
        if original_value is None:
            return value
        elif isinstance(original_value, bool):
            if isinstance(value, bool):
                return value
            return str(value).lower() in ("true", "1", "yes")
        elif isinstance(original_value, int):
            if isinstance(value, int):
                return value
            try:
                return int(value)
            except (ValueError, TypeError):
                return original_value
        elif isinstance(original_value, float):
            if isinstance(value, float):
                return value
            try:
                return float(value)
            except (ValueError, TypeError):
                return original_value
        elif isinstance(original_value, list):
            if isinstance(value, list):
                return value
            if isinstance(value, str):
                try:
                    parsed = literal_eval(value)
                    if isinstance(parsed, list):
                        return parsed
                except (ValueError, SyntaxError):
                    pass
                if value.startswith("[") and value.endswith("]"):
                    return original_value
                return [v.strip() for v in value.split(",") if v.strip()]
            return original_value
        elif isinstance(original_value, dict):
            if isinstance(value, dict):
                return value
            if isinstance(value, str):
                try:
                    parsed = literal_eval(value)
                    if isinstance(parsed, dict):
                        return parsed
                except (ValueError, SyntaxError):
                    pass
            return original_value
        return value

    @classmethod
    def load_dict(cls, config_dict):
        for key, value in config_dict.items():
            if hasattr(cls, key):
                if key == "DEFAULT_UPLOAD" and value != "gd":
                    value = "rc"
                elif key in [
                    "BASE_URL",
                    "RCLONE_SERVE_URL",
                    "INDEX_URL",
                    "SEARCH_API_LINK",
                ]:
                    if value:
                        value = value.strip("/")
                elif key == "USENET_SERVERS":
                    try:
                        if not value[0].get("host"):
                            value = []
                    except Exception:
                        value = []
                value = cls._convert_env_type(key, value)
                setattr(cls, key, value)
        if config_dict.get("LEECH_DUMP_CHAT") and not cls.LEECH_LOG_CHAT:
            cls.LEECH_LOG_CHAT = cls._convert_env_type(
                "LEECH_LOG_CHAT", config_dict["LEECH_DUMP_CHAT"]
            )
        for key in ["BOT_TOKEN", "OWNER_ID", "TELEGRAM_API", "TELEGRAM_HASH"]:
            value = getattr(cls, key)
            if isinstance(value, str):
                value = value.strip()
            if not value:
                raise ValueError(f"{key} variable is missing!")


class BinConfig:
    ARIA2_NAME = bin_name(0)
    QBIT_NAME = bin_name(1)
    FFMPEG_NAME = bin_name(2)
    RCLONE_NAME = bin_name(3)
    SABNZBD_NAME = bin_name(4)
