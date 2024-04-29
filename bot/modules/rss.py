import os
import logging
import sys
import re
import pathlib
from typing import Dict, List, Any, Union, Tuple, Callable, Awaitable, Optional
from dataclasses import dataclass
import aiosession
import feedparser
import pyrogram
from pyrogram.handlers import MessageHandler, CallbackQueryHandler
from pyrogram.filters import command, regex, create
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from time import time
from functools import partial
from apscheduler.triggers.interval import IntervalTrigger
from logging.config import dictConfig
from argparse import ArgumentParser

import asyncio
import aioschedule as scheduler
from aiohttp import ClientSession

from bot.helper.telegram_helper.message_utils import sendMessage, editMessage, sendRss, sendFile
from bot.helper.telegram_helper.filters import CustomFilters
from bot.helper.telegram_helper.bot_commands import BotCommands
from bot.helper.ext_utils.db_handler import DbManger
from bot.helper.telegram_helper.button_build import ButtonMaker
from bot.helper.ext_utils.bot_utils import new_thread
from bot.helper.ext_utils.exceptions import RssShutdownException
from bot.helper.ext_utils.help_messages import RSS_HELP_MESSAGE

CONFIG_DIR = pathlib.Path(__file__).parent.resolve()
CONFIG_FILE = CONFIG_DIR / "config.ini"
LOGGING_CONFIG = CONFIG_DIR / "logging.ini"

@dataclass
class Config:
    RSS_DELAY: int = 60
    RSS_CHAT: int = 0

