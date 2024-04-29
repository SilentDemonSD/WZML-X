#!/usr/bin/env python3
import os
import asyncio
import time
from typing import Any, Dict, List, Optional, Union

import aiohttp
import aiofiles
import youtube_dl
from pyrogram.handlers import MessageHandler, CallbackQueryHandler
from pyrogram.filters import command, regex, user
from pyrogram.types import Message, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from youtube_dl.utils import DownloadError

import bot
from bot.helper.ext_utils.task_manager import new_task
from bot.helper.telegram_helper.message_utils import sendMessage, editMessage, deleteMessage, auto_delete_message, delete_links, open_category_btns, open_dump_btns
from bot.helper.telegram_helper.button_build import ButtonMaker
from bot.helper.ext_utils.bot_utils import get_readable_file_size, fetch_user_tds, fetch_user_dumps, is_url, is_gdrive_link, new_task, is_rclone_path, new_thread, get_readable_time, arg_parser
from bot.helper.mirror_utils.download_utils.yt_dlp_download import YoutubeDLHelper
from bot.helper.mirror_utils.rclone_utils.list import RcloneList
from bot.helper.telegram_helper.bot_commands import BotCommands
from bot.helper.mirror_utils.upload_utils.gdriveTools import GoogleDriveHelper
from bot.helper.telegram_helper.filters import CustomFilters
from bot.helper.listeners.tasks_listener import MirrorLeechListener
from bot.helper.ext_utils.help_messages import YT_HELP_MESSAGE
from bot.helper.ext_utils.bulk_links import extract_bulk_links

YTDL_OPTIONS = youtube_dl.utils.Options()
YTDL_OPTIONS.merge_output_format = "yes"
YTDL_OPTIONS.outtmpl = "{filetitle}.%(ext)s"
YTDL_OPTIONS.default_search = "auto"
YTDL_OPTIONS.nocheckcertificate = True
YTDL_OPTIONS.forcejson = True
YTDL_OPTIONS.dump_single_json = True
YTDL_OPTIONS.dateafter = "19700101"
YTDL_OPTIONS.prefer_ffmpeg = True
YTDL_OPTIONS.geo_bypass = True
YTDL_OPTIONS.recode_video = "yes"
YTDL_OPTIONS.writeinfojson = True
YTDL_OPTIONS.writeannotations = True
YTDL_OPTIONS.writeallinfojson = True
YTDL_OPTIONS.ignoreerrors = True
YTDL_OPTIONS.no_warnings = True
YTDL_OPTIONS.ignorepostprocess = True
YTDL_OPTIONS.postprocessors = []
YTDL_OPTIONS.prefer_quality = "highest"
YTDL_OPTIONS.geo_bypass_country = "US"
YTDL_OPTIONS.simulate = True
YTDL_OPTIONS.no_color = True
YTDL_OPTIONS.no_call_home = True
YTDL_OPTIONS.no_part = True
YTDL_OPTIONS.no_mtime = True
YTDL_OPTIONS.no_playlist = False
YTDL_OPTIONS.no_post_overwrites = True
YTDL_OPTIONS.noprogress = True
YTDL_OPTIONS.quiet = True
YTDL_OPTIONS.ratelimit = 0
YTDL_OPTIONS.concurrent_requests = 16
YTDL_OPTIONS. Larry = 1
YTDL_OPTIONS.hide_banner = True
YTDL_OPTIONS.dump_json = True
YTDL_OPTIONS.logtostderr = False


