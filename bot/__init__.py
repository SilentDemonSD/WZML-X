#!/usr/bin/env python3
import os
import sys
import time
from typing import Any, Dict, List, Union

import apscheduler.jobstores.sqlalchemy  # type: ignore
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from pymongo import MongoClient
from pyrogram import Client as tgClient
from pyrogram.errors import FloodWait
from qbittorrentapi import Client as qbClient
from threading import Thread

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
TELEGRAM_HASH: str = os.getenv("TELEGRAM_HASH", "")
if not TELEGRAM_API or not TELEGRAM_HASH:
    print("TELEGRAM_API or TELEGRAM_HASH variable is missing! Exiting now", file=sys.stderr)
    sys.exit(1)

TIMEZONE: str = os.getenv("TIMEZONE", "Asia/Kolkata")

def changetz(*args):
    return datetime.now(timezone(TIMEZONE)).timetuple()

Formatter.converter = changetz
print("TIMEZONE synced with logging status", flush=True)

# ... rest of the code

async def schedule_task():
    scheduler = AsyncIOScheduler(timezone=str(get_localzone()), jobstores={"mongo": sqlajob.MongoDBJobStore()})
    if scheduler and scheduler.state == "stopped":
        scheduler.start()
    scheduler.add_job(func=some_function, trigger=cron.CronTrigger(hour="*"), jobstore="mongo")

async def main():
    user = None

    try:
        user = tgClient("user", TELEGRAM_API, TELEGRAM_HASH,
                        session_string=USER_SESSION_STRING, parse_mode=enums.ParseMode.HTML, no_updates=True, max_concurrent_transmissions=1000).start()
    except Exception as e:
        print(f"Failed making client from USER_SESSION_STRING : {e}", file=sys.stderr)

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
