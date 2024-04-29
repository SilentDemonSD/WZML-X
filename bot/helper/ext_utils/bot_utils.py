#!/usr/bin/env python3
import os
import re
import shutil
import string
import time
import uuid
from asyncio import create_subprocess_exec, run_coroutine_threadsafe, sleep
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from functools import partial, wraps
from html import escape
from os.path import exists, join
from pkg_resources import get_distribution
from subprocess import run as srun
from time import gmtime, strftime
from typing import List, Union
from urllib.parse import unquote

import aiofiles
import aiohttp
import psutil
import requests
import yt_dlp
from bs4 import BeautifulSoup
from mega import MegaApi
from pyrogram import Client, filters
from pyrogram.enums import ChatType
from pyrogram.errors import PeerIdInvalid
from pyrogram.types import BotCommand, InlineKeyboardButton, InlineKeyboardMarkup, Message

from bot.helper.ext_utils.db_handler import DbManger
from bot.helper.ext_utils.shortners import short_url
from bot.helper.telegram_helper.button_build import ButtonMaker
from bot.helper.telegram_helper.filters import CustomFilters
from bot.helper.telegram_helper.message_utils import sendMessage, sendMarkup
from bot.version import get_version
from bot.ytdl_handler import ytdl_download

THREADPOOL = ThreadPoolExecutor(max_workers=1000)
MAGNET_REGEX = r"magnet:\?xt=urn:(btih|btmh):[a-zA-Z0-9]*\s*"
URL_REGEX = r"^(?!\/)(rtmps?:\/\/|mms:\/\/|rtsp:\/\/|https?:\/\/|ftp:\/\/)?([^\/:]+:[^\/@]+@)?(www\.)?(?=[^\/:\s]+\.[^\/:\s]+)([^\/:\s]+\.[^\/:\s]+)(:\d+)?(\/[^#\s]*[\s\S]*)?(\?[^#\s]*)?(#.*)?$"
SIZE_UNITS = ["B", "KB", "MB", "GB", "TB", "PB", "EB"]
STATUS_START = 0
PAGES = 1
PAGE_NO = 1

class MirrorStatus:
    STATUS_UPLOADING = "Upload"
    STATUS_DOWNLOADING = "Download"
    STATUS_CLONING = "Clone"
    STATUS_QUEUEDL = "QueueDL"
    STATUS_QUEUEUP = "QueueUp"
    STATUS_PAUSED = "Pause"
    STATUS_ARCHIVING = "Archive"
    STATUS_EXTRACTING = "Extract"
    STATUS_SPLITTING = "Split"
    STATUS_CHECKING = "CheckUp"
    STATUS_SEEDING = "Seed"
    STATUS_UPLOADDDL = "Upload DDL"

class setInterval:
    def __init__(self, interval, action):
        self.interval = interval
        self.action = action
        self.task = bot_loop.create_task(self.__set_interval())

    async def __set_interval(self):
        while True:
            await sleep(self.interval)
            await self.action()

    def cancel(self):
        self.task.cancel()

def get_readable_file_size(size_in_bytes):
    if size_in_bytes is None:
        return '0B'
    index = 0
    while size_in_bytes >= 1024 and index < len(SIZE_UNITS) - 1:
        size_in_bytes /= 102
