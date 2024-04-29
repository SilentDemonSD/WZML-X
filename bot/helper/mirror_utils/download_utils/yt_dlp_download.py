#!/usr/bin/env python3
import os
import re
import asyncio
import traceback
from typing import Dict, Any, List, Tuple, Union

import aiohttp
import aiohttp_sessions
from yt_dlp import YoutubeDL, DownloadError

from bot import download_dict_lock, download_dict, non_queued_dl, queue_dict_lock
from bot.helper.telegram_helper.message_utils import sendStatusMessage
from ..status_utils.yt_dlp_download_status import YtDlpDownloadStatus
from bot.helper.mirror_utils.status_utils.queue_status import QueueStatus
from bot.helper.ext_utils.bot_utils import sync_to_async, async_to_sync, is_queued, stop_duplicate_check, limit_checker

LOGGER = getLogger(__name__)


class MyLogger:
    def __init__(self, obj):
        self.obj = obj

    def debug(self, msg: str):
        # Hack to fix changing extension
        if not self.obj.is_playlist:
            if match := re.search(r'.Merger..Merging formats into..(.*?).$', msg) or \
                    re.search(r'.ExtractAudio..Destination..(.*?)$', msg):
                LOGGER.info(msg)
                newname = match.group(1)
                newname = newname.rsplit("/", 1)[-1]
                self.obj.name = newname

    @staticmethod
    def warning(msg: str):
        LOGGER.warning(msg)

    @staticmethod
    def error(msg: str):
        if msg != "ERROR: Cancelling...":
            LOGGER.error(msg)


class YoutubeDLHelper:
    def __init__(self, listener):
        self.__last_downloaded: int = 0
        self.__size: int = 0
        self.__progress: float = 0
        self.__downloaded_bytes: int = 0
        self.__download_speed: int = 0
        self.__eta: Union[str, float] = '-'
        self.__listener = listener
        self.__gid = ''
        self.__is_cancelled = False
        self.__downloading = False
        self.__ext = ''
        self.name = ''
        self.is_playlist = False
        self.playlist_count = 0
        self.opts: Dict[str, Any] = {
            'progress_hooks': [self.__onDownloadProgress],
            'logger': MyLogger(self),
            'usenetrc': True,
            'cookiefile': 'cookies.txt',
            'allow_multiple_video_streams': True,
            'allow_multiple_audio_streams': True,
            'noprogress': True,
            'allow_playlist_files': True,
            'overwrites': True,
            'writethumbnail': True,
            'trim_file_name': 220,
            'retry_sleep_functions': {
                'http': lambda n: 3,
                'fragment': lambda n: 3,
                'file_access': lambda n: 3,
                'extractor': lambda n: 3
            }
        }

