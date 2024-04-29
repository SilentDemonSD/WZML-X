#!/usr/bin/env python3
import os
import re
import asyncio
import traceback
from typing import Dict, Any, List, Tuple, Union

import aiohttp
import aiohttp_sessions
from yt_dlp import YoutubeDL, DownloadError
from logging import getLogger

class YoutubeDLHelper(YoutubeDL):
    def __init__(self, listener):
        super().__init__()
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

    def __post_init__(self):
        self.opts: Dict[str, Any] = {
            'progress_hooks': [self.__onDownloadProgress],
            'logger': self.MyLogger(self),
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

    def cancel(self):
        self.__is_cancelled = True

    @property
    def is_downloading(self):
        return self.__downloading

    @property
    def download_speed_str(self):
        return f"{self.__download_speed} bytes/sec"

    @property
    def eta_str(self):
        return f"{self.__eta}" if isinstance(self.__eta, str) else f"{self.__eta:.2f} sec"

    @property
    def downloaded_bytes_str(self):
        return f"{self.__downloaded_bytes} bytes"

    @property
    def size_str(self):
        return f"{self.__size} bytes"

    @property
    def progress_str(self):
        return f"{self.__progress * 100:.2f}%"

    @property
    def gid(self):
        return self.__gid

    @property
    def is_cancelled(self):
        return self.__is_cancelled

    def __onDownloadProgress(self, d):
        if d['status'] == 'downloading':
            self.__downloading = True
            self.__size = d['total_bytes']
            self.__downloaded_bytes = d['downloaded_bytes']
            self.__progress = self.__downloaded_bytes / self.__size
            self.__download_speed = d['speed']
            self.__eta = d['eta']
        elif d['status'] == 'finished':
            self.__downloading = False
            self.__gid = d['id']
            self.__last_downloaded = self.__downloaded_bytes
            self.__size = 0
            self.__downloaded_bytes = 0
            self.__progress = 0
            self.__download_speed = 0
            self.__eta = '-'

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
