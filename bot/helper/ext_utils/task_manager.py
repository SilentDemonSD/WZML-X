#!/usr/bin/env python3
from typing import List, Dict, Union, Tuple, Optional, AsyncContextManager, Callable, Coroutine, Awaitable
import time
from asyncio import Event, Lock
import aiohttp
import asyncio
import gdown
import os
import re
import shutil
import tarfile
import zipfile
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaIoBaseDownload
from telegram import Update, Bot, Message, Chat, User, InlineKeyboardButton, InlineKeyboardMarkup, ParseMode
from telegram.error import TelegramError, NetworkError, Unauthorized, ChatMigrated, BadRequest
from telegram.ext import CommandHandler, Filters, CallbackContext, run_async, ContextTypes
from telegram.utils.helpers import escape_markdown

from bot import bot_cache, config_dict, queued_dl, queued_up, non_queued_up, non_queued_dl, queue_dict_lock, LOGGER, user_data, download_dict
from bot.helper.mirror_utils.upload_utils.gdriveTools import GoogleDriveHelper
from bot.helper.ext_utils.fs_utils import get_base_name, check_storage_threshold
from bot.helper.ext_utils.bot_utils import get_user_tasks, getdailytasks, sync_to_async, get_telegraph_list, get_readable_file_size, checking_access, get_readable_time
from bot.helper.telegram_helper.message_utils import forcesub, check_botpm
from bot.helper.telegram_helper.filters import CustomFilters
from bot.helper.themes import BotTheme

...

async def stop_duplicate_check(name: str, listener: Any) -> Tuple[Optional[str], Optional[List[InlineKeyboardButton]]]:
    ...

async def timeval_check(user_id: int) -> Optional[int]:
    ...

async def is_queued(uid: int) -> Tuple[bool, Optional[Event]]:
    ...

def start_dl_from_queued(uid: int):
    ...

def start_up_from_queued(uid: int):
    ...

@run_async
async def start_from_queued():
    ...

async def limit_checker(size: int, listener: Any, isTorrent: bool = False, isMega: bool = False, isDriveLink: bool = False, isYtdlp: bool = False, isPlayList: Optional[int] = None) -> Optional[str]:
    ...

async def task_utils(message: Message) -> Tuple[List[str], Optional[List[InlineKeyboardButton]]]:
    ...
