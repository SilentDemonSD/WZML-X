from importlib import import_module
from os import getenv


class Config:
    AS_DOCUMENT = False
    AUTHORIZED_CHATS = ""
    BASE_URL = ""
    BASE_URL_PORT = 80
    BOT_TOKEN = ""
    HELPER_TOKENS = ""
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
    DISABLE_BULK = False
    DISABLE_MULTI = False
    DISABLE_SEED = False
    DISABLE_FF_MODE = False
    EQUAL_SPLITS = False
    EXCLUDED_EXTENSIONS = ""
    FFMPEG_CMDS = {}
    FILELION_API = ""
    MEDIA_STORE = True
    FORCE_SUB_IDS = ""
    GDRIVE_ID = ""
    GD_DESP = "Uploaded with WZ Bot"
    AUTHOR_NAME = "WZML-X"
    AUTHOR_URL = "https://t.me/WZML_X"
    INSTADL_API = ""
    IMDB_TEMPLATE = ""
    INCOMPLETE_TASK_NOTIFIER = False
    INDEX_URL = ""
    IS_TEAM_DRIVE = False
    JD_EMAIL = ""
    JD_PASS = ""
    MEGA_EMAIL = ""
    MEGA_PASSWORD = ""
    DIRECT_LIMIT = 0
    MEGA_LIMIT = 0
    TORRENT_LIMIT = 0
    GD_DL_LIMIT = 0
    RC_DL_LIMIT = 0
    CLONE_LIMIT = 0
    JD_LIMIT = 0
    NZB_LIMIT = 0
    YTDLP_LIMIT = 0
    PLAYLIST_LIMIT = 0
    LEECH_LIMIT = 0
    EXTRACT_LIMIT = 0
    ARCHIVE_LIMIT = 0
    STORAGE_LIMIT = 0
    LEECH_DUMP_CHAT = ""
    LINKS_LOG_ID = ""
    MIRROR_LOG_ID = ""
    CLEAN_LOG_MSG = False
    LEECH_PREFIX = ""
    LEECH_CAPTION = ""
    LEECH_SUFFIX = ""
    LEECH_FONT = ""
    LEECH_SPLIT_SIZE = 2097152000
    MEDIA_GROUP = False
    HYBRID_LEECH = True
    HYPER_THREADS = 0
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
    RCLONE_SERVE_PORT = 8080
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
    VERIFY_TIMEOUT = 0
    LOGIN_PASS = ""
    TORRENT_TIMEOUT = 0
    TIMEZONE = "Asia/Kolkata"
    USER_MAX_TASKS = 0
    USER_TIME_INTERVAL = 0
    UPLOAD_PATHS = {}
    UPSTREAM_REPO = ""
    UPSTREAM_BRANCH = "master"
    UPDATE_PKGS = True
    USENET_SERVERS = []
    USER_SESSION_STRING = ""
    USER_TRANSMISSION = True
    USE_SERVICE_ACCOUNTS = False
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
        for key in ["BOT_TOKEN", "OWNER_ID", "TELEGRAM_API", "TELEGRAM_HASH"]:
            value = getattr(cls, key)
            if isinstance(value, str):
                value = value.strip()
            if not value:
                raise ValueError(f"{key} variable is missing!")

    @classmethod
    def load_env(cls):
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
            return value.lower() in ("true", "1", "yes")
        elif isinstance(original_value, int):
            try:
                return int(value)
            except ValueError:
                return original_value
        elif isinstance(original_value, float):
            try:
                return float(value)
            except ValueError:
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
                setattr(cls, key, value)
        for key in ["BOT_TOKEN", "OWNER_ID", "TELEGRAM_API", "TELEGRAM_HASH"]:
            value = getattr(cls, key)
            if isinstance(value, str):
                value = value.strip()
            if not value:
                raise ValueError(f"{key} variable is missing!")


class BinConfig:
    ARIA2_NAME = "blitzfetcher"
    QBIT_NAME = "stormtorrent"
    FFMPEG_NAME = "mediaforge"
    RCLONE_NAME = "ghostdrive"
    SABNZBD_NAME = "newsripper"
