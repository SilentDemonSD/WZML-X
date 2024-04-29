#!/usr/bin/env python3
import os
import sys
import time
from typing import Any, Dict, List, Union

import apscheduler.jobstores.sqlalchemy as sqlajob
import apscheduler.triggers.cron as cron
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from dotenv import load_dotenv
from pymongo import MongoClient
from pyrogram import Client as tgClient, enums
from pyrogram.errors import FloodWait
from qbittorrentapi import Client as qbClient
from threading import Thread
from typing_extensions import Literal

load_dotenv()

BOT_TOKEN: str = os.getenv("BOT_TOKEN", "")
if not BOT_TOKEN:
    print("BOT_TOKEN variable is missing! Exiting now", file=sys.stderr)
    sys.exit(1)

bot_id: str = BOT_TOKEN.split(":", 1)[0]

DATABASE_URL: str = os.getenv("DATABASE_URL", "")
if DATABASE_URL:
    conn = MongoClient(DATABASE_URL)
    db = conn.wzmlx
    current_config = dict(os.environ)
    old_config = db.settings.deployConfig.find_one({"_id": bot_id})
    if old_config is None:
        db.settings.deployConfig.replace_one(
            {"_id": bot_id}, current_config, upsert=True
        )
    else:
        del old_config["_id"]
    if old_config and old_config != current_config:
        db.settings.deployConfig.replace_one(
            {"_id": bot_id}, current_config, upsert=True
        )
    elif config_dict := db.settings.config.find_one({"_id": bot_id}):
        del config_dict["_id"]
        for key, value in config_dict.items():
            os.environ[key] = str(value)
    if pf_dict := db.settings.files.find_one({"_id": bot_id}):
        del pf_dict["_id"]
        for key, value in pf_dict.items():
            if value:
                file_ = key.replace("__", ".")
                with open(file_, "wb+") as f:
                    f.write(value)
    if a2c_options := db.settings.aria2c.find_one({"_id": bot_id}):
        del a2c_options["_id"]
        aria2_options = a2c_options
    if qbit_opt := db.settings.qbittorrent.find_one({"_id": bot_id}):
        del qbit_opt["_id"]
        qbit_options = qbit_opt
    conn.close()
    BOT_TOKEN = os.getenv("BOT_TOKEN", "")
    bot_id = BOT_TOKEN.split(":", 1)[0]
    DATABASE_URL = os.getenv("DATABASE_URL", "")
else:
    config_dict = {}

OWNER_ID: int = int(os.getenv("OWNER_ID", ""))
if not OWNER_ID:
    print("OWNER_ID variable is missing! Exiting now", file=sys.stderr)
    sys.exit(1)

TELEGRAM_API: int = int(os.getenv("TELEGRAM_API", ""))
if not TELEGRAM_API:
    print("TELEGRAM_API variable is missing! Exiting now", file=sys.stderr)
    sys.exit(1)

TELEGRAM_HASH: str = os.getenv("TELEGRAM_HASH", "")
if not TELEGRAM_HASH:
    print("TELEGRAM_HASH variable is missing! Exiting now", file=sys.stderr)
    sys.exit(1)

TIMEZONE: str = os.getenv("TIMEZONE", "Asia/Kolkata")

def changetz(*args):
    return datetime.now(timezone(TIMEZONE)).timetuple()

Formatter.converter = changetz
print("TIMEZONE synced with logging status", flush=True)

GDRIVE_ID: str = os.getenv("GDRIVE_ID", "")
RCLONE_PATH: str = os.getenv("RCLONE_PATH", "")
RCLONE_FLAGS: str = os.getenv("RCLONE_FLAGS", "")
DEFAULT_UPLOAD: Literal["rc", "ddl", "gd"] = os.getenv(
    "DEFAULT_UPLOAD", "gd").lower()
DOWNLOAD_DIR: str = os.getenv("DOWNLOAD_DIR", "/usr/src/app/downloads/")
AUTHORIZED_CHATS: str = os.getenv("AUTHORIZED_CHATS", "")
SUDO_USERS: str = os.getenv("SUDO_USERS", "")
BLACKLIST_USERS: str = os.getenv("BLACKLIST_USERS", "")
EXTENSION_FILTER: List[str] = os.getenv(
    "EXTENSION_FILTER", "").split() if os.getenv("EXTENSION_FILTER") else []
LINKS_LOG_ID: int = int(os.getenv("LINKS_LOG_ID", ""))
MIRROR_LOG_ID: int = int(os.getenv("MIRROR_LOG_ID", ""))
LEECH_LOG_ID: int = int(os.getenv("LEECH_LOG_ID", ""))
EXCEP_CHATS: str = os.getenv("EXCEP_CHATS", "")
IS_PREMIUM_USER: bool = False
USER_SESSION_STRING: str = os.getenv("USER_SESSION_STRING", "")
MEGA_EMAIL: str = os.getenv("MEGA_EMAIL", "")
MEGA_PASSWORD: str = os.getenv("MEGA_PASSWORD", "")
GDTOT_CRYPT: str = os.getenv("GDTOT_CRYPT", "")
JIODRIVE_TOKEN: str = os.getenv("JIODRIVE_TOKEN", "")
REAL_DEBRID_API: str = os.getenv("REAL_DEBRID_API", "")
DEBRID_LINK_API: str = os.getenv("DEBRID_LINK_API", "")
INDEX_URL: str = os.getenv("INDEX_URL", "").rstrip("/")
SEARCH_API_LINK: str = os.getenv("SEARCH_API_LINK", "").rstrip("/")
CAP_FONT: str = os.getenv("CAP_FONT", "").lower()
LEECH_FILENAME_PREFIX: str = os.getenv(
    "LEECH_FILENAME_PREFIX", "").strip()
LEECH_FILENAME_SUFFIX: str = os.getenv(
    "LEECH_FILENAME_SUFFIX", "").strip()
LEECH_FILENAME_CAPTION: str = os.getenv(
    "LEECH_FILENAME_CAPTION", "").strip()
LEECH_FILENAME_REMNAME: str = os.getenv(
    "LEECH_FILENAME_REMNAME", "").strip()
MIRROR_FILENAME_PREFIX: str = os.getenv(
    "MIRROR_FILENAME_PREFIX", "").strip()
MIRROR_FILENAME_SUFFIX: str = os.getenv(
    "MIRROR_FILENAME_SUFFIX", "").strip()
MIRROR_FILENAME_REMNAME: str = os.getenv(
    "MIRROR_FILENAME_REMNAME", "").strip()
SEARCH_PLUGINS: str = os.getenv("SEARCH_PLUGINS", "")
MAX_SPLIT_SIZE: int = 4194304000 if IS_PREMIUM_USER else 2097152000
LEECH_SPLIT_SIZE: int = int(
    os.getenv("LEECH_SPLIT_SIZE", "")) if os.getenv("LEECH_SPLIT_SIZE") else MAX_SPLIT_SIZE
BOT_MAX_TASKS: int = int(
    os.getenv("BOT_MAX_TASKS", "")) if os.getenv("BOT_MAX_TASKS").isdigit() else None
STATUS_UPDATE_INTERVAL: int = int(
    os.getenv("STATUS_UPDATE_INTERVAL", "")) if os.getenv("STATUS_UPDATE_INTERVAL").isdigit() else 10
AUTO_DELETE_MESSAGE_DURATION: int = int(
    os.getenv("AUTO_DELETE_MESSAGE_DURATION", "")) if os.getenv("AUTO_DELETE_MESSAGE_DURATION").isdigit() else 30
YT_DLP_OPTIONS: str = os.getenv("YT_DLP_OPTIONS", "")
SEARCH_LIMIT: int = 0 if os.getenv("SEARCH_LIMIT") else None
STATUS_LIMIT: int = 6 if os.getenv("STATUS_LIMIT") else None
CMD_SUFFIX: str = os.getenv("CMD_SUFFIX", "")
RSS_CHAT: Union[int, str] = os.getenv("RSS_CHAT", "")
RSS_DELAY: int = int(os.getenv("RSS_DELAY", ""))
TORRENT_TIMEOUT: Union[int, str] = os.getenv("TORRENT_TIMEOUT", "")
QUEUE_ALL: Union[int, str] = os.getenv("QUEUE_ALL", "")
QUEUE_DOWNLOAD: Union[int, str] = os.getenv("QUEUE_DOWNLOAD", "")
QUEUE_UPLOAD: Union[int, str] = os.getenv("QUEUE_UPLOAD", "")
INCOMPLETE_TASK_NOTIFIER: bool = os.getenv(
    "INCOMPLETE_TASK_NOTIFIER", "").lower() == "true"
STOP_DUPLICATE: bool = os.getenv("STOP_DUPLICATE", "").lower() == "true"
IS_TEAM_DRIVE: bool = os.getenv("IS_TEAM_DRIVE", "").lower() == "true"
USE_SERVICE_ACCOUNTS: bool = os.getenv(
    "USE_SERVICE_ACCOUNTS", "").lower() == "true"
WEB_PINCODE: bool = os.getenv("WEB_PINCODE", "").lower() == "true"
AS_DOCUMENT: bool = os.getenv("AS_DOCUMENT", "").lower() == "true"
USER_TD_MODE: bool = os.getenv("USER_TD_MODE", "").lower() == "true"
USER_TD_SA: str = os.getenv("USER_TD_SA", "").lower() if os.getenv(
    "USER_TD_SA") else ""
SHOW_MEDIAINFO: bool = os.getenv("SHOW_MEDIAINFO", "").lower() == "true"
SCREENSHOTS_MODE: bool = os.getenv("SCREENSHOTS_MODE", "").lower() == "true"
SOURCE_LINK: bool = os.getenv("SOURCE_LINK", "").lower() == "true"
DELETE_LINKS: bool = os.getenv("DELETE_LINKS", "").lower() == "true"
EQUAL_SPLITS: bool = os.getenv("EQUAL_SPLITS", "").lower() == "true"
MEDIA_GROUP: bool = os.getenv("MEDIA_GROUP", "").lower() == "true"
BASE_URL_PORT: int = int(os.getenv("BASE_URL_PORT", ""))
BASE_URL: str = os.getenv("BASE_URL", "").rstrip("/")
UPSTREAM_REPO: str = os.getenv("UPSTREAM_REPO", "")
UPSTREAM_BRANCH: str = os.getenv("UPSTREAM_BRANCH", "master")
UPGRADE_PACKAGES: bool = os.getenv("UPGRADE_PACKAGES", "").lower() == "true"
RCLONE_SERVE_URL: str = os.getenv("RCLONE_SERVE_URL", "")
RCLONE_SERVE_PORT: int = int(os.getenv("RCLONE_SERVE_PORT", ""))
RCLONE_SERVE_USER: str = os.getenv("RCLONE_SERVE_USER", "")
RCLONE_SERVE_PASS: str = os.getenv("RCLONE_SERVE_PASS", "")
STORAGE_THRESHOLD: float = float(os.getenv("STORAGE_THRESHOLD", ""))
TORRENT_LIMIT: float = float(os.getenv("TORRENT_LIMIT", ""))
DIRECT_LIMIT: float = float(os.getenv("DIRECT_LIMIT", ""))
YTDLP_LIMIT: float = float(os.getenv("YTDLP_LIMIT", ""))
GDRIVE_LIMIT: float = float(os.getenv("GDRIVE_LIMIT", ""))
CLONE_LIMIT: float = float(os.getenv("CLONE_LIMIT", ""))
MEGA_LIMIT: float = float(os.getenv("MEGA_LIMIT", ""))
LEECH_LIMIT: float = float(os.getenv("LEECH_LIMIT", ""))
USER_MAX_TASKS: int = int(os.getenv("USER_MAX_TASKS", "")) if os.getenv(
    "USER_MAX_TASKS").isdigit() else None
USER_TIME_INTERVAL: int = int(os.getenv("USER_TIME_INTERVAL", "")) if os.getenv(
    "USER_TIME_INTERVAL").isdigit() else 0
PLAYLIST_LIMIT: int = int(os.getenv("PLAYLIST_LIMIT", "")) if os.getenv(
    "PLAYLIST_LIMIT").isdigit() else None
FSUB_IDS: str = os.getenv("FSUB_IDS", "")
BOT_PM: bool = os.getenv("BOT_PM", "").lower() == "true"
DAILY_TASK_LIMIT: int = int(os.getenv("DAILY_TASK_LIMIT", "")) if os.getenv(
    "DAILY_TASK_LIMIT").isdigit() else None
DAILY_MIRROR_LIMIT: float = float(os.getenv("DAILY_MIRROR_LIMIT", "")) if os.getenv(
    "DAILY_MIRROR_LIMIT") else None
DAILY_LEECH_LIMIT: float = float(os.getenv("DAILY_LEECH_LIMIT", "")) if os.getenv(
    "DAILY_LEECH_LIMIT") else None
DISABLE_DRIVE_LINK: bool = os.getenv(
    "DISABLE_DRIVE_LINK", "").lower() == "true"
BOT_THEME: str = os.getenv("BOT_THEME", "minimal")
IMAGES: List[str] = os.getenv("IMAGES", "").replace("'", "").replace('"', "").replace(
    "[", "").replace("]", "").replace(",", "").split()
IMG_SEARCH: List[str] = os.getenv(
    "IMG_SEARCH", "").replace("'", "").replace('"', "").replace("[", "").replace("]", "").replace(",", "").split()
IMG_PAGE: int = int(os.getenv("IMG_PAGE", "")) if os.getenv("IMG_PAGE").isdigit() else None
AUTHOR_NAME: str = os.getenv("AUTHOR_NAME", "WZML-X")
AUTHOR_URL: str = os.getenv("AUTHOR_URL", "https://t.me/WZML_X")
TITLE_NAME: str = os.getenv("TITLE_NAME", "WZ-M/L-X")
COVER_IMAGE: str = os.getenv("COVER_IMAGE", "https://graph.org/file/60f9f8bcb97d27f76f5c0.jpg")
GD_INFO: str = os.getenv("GD_INFO", "Uploaded by WZML-X")
SAVE_MSG: bool = os.getenv("SAVE_MSG", "").lower() == "true"
SAFE_MODE: bool = os.getenv("SAFE_MODE", "").lower() == "true"
SET_COMMANDS: bool = os.getenv("SET_COMMANDS", "").lower() == "true"
CLEAN_LOG_MSG: bool = os.getenv("CLEAN_LOG_MSG", "").lower() == "true"
SHOW_EXTRA_CMDS: bool = os.getenv("SHOW_EXTRA_CMDS", "").lower() == "true"
TOKEN_TIMEOUT: int = int(os.getenv("TOKEN_TIMEOUT", "")) if os.getenv(
    "TOKEN_TIMEOUT").isdigit() else None
LOGIN_PASS: str = os.getenv("LOGIN_PASS", None)
FILELION_API: str = os.getenv("FILELION_API", "")
IMDB_TEMPLATE: str = os.getenv("IMDB_TEMPLATE", "")
ANIME_TEMPLATE: str = os.getenv("ANIME_TEMPLATE", "")
MDL_TEMPLATE: str = os.getenv("MDL_TEMPLATE", "")

async def schedule_task():
    scheduler = AsyncIOScheduler(timezone=str(get_localzone()), jobstores={"mongo": sqlajob.MongoDBJobStore()})
    scheduler.add_job(func=some_function, trigger=cron.CronTrigger(hour="*"), jobstore="mongo")
    scheduler.start()

async def main():
    try:
        user = tgClient("user", TELEGRAM_API, TELEGRAM_HASH,
                        session_string=USER_SESSION_STRING, parse_mode=enums.ParseMode.HTML, no_updates=True, max_concurrent_transmissions=1000).start()
        IS_PREMIUM_USER = user.me.is_premium
    except Exception as e:
        print(f"Failed making client from USER_SESSION_STRING : {e}", file=sys.stderr)
        user = None

    if not user:
        print("Creating client from BOT_TOKEN", file=sys.stderr)
        bot = tgClient("bot", TELEGRAM_API, TELEGRAM_HASH,
                       bot_token=BOT_TOKEN, workers=1000, parse_mode=enums.ParseMode.HTML, max_concurrent_transmissions=1000).start()
        bot_loop = bot.loop
        bot_name = bot.me.username

        try:
            await bot.send_message(chat_id=OWNER_ID, text="Bot started!")
        except FloodWait as e:
            print(
                f"FloodWait exception occurred while sending message to owner ({e.x}s)", file=sys.stderr)
        except Exception as e:
            print(
                f"Exception occurred while sending message to owner: {e}", file=sys.stderr)

        scheduler = AsyncIOScheduler(timezone=str(get_localzone()), event_loop=bot_loop)
        scheduler.add_job(func=schedule_task, trigger=cron.CronTrigger(minute="*/1"), id="schedule_task")
        scheduler.start()

if __name__ == "__main__":
    main()
