#!/usr/bin/env python3
import os
import re
import asyncio
import logging
from typing import Dict, Any, List, Tuple, Union

import aiohttp
from yt_dlp import YoutubeDL, DownloadError

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
            'progress_hooks': [self.__on_download_progress],
            'logger': self.MyLogger(),
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
    def is_downloading(self) -> bool:
        return self.__downloading

    @property
    def download_speed_str(self) -> str:
        return f"{self.__download_speed} bytes/sec"

    @property
    def eta_str(self) -> str:
        return f"{self.__eta}" if isinstance(self.__eta, str) else f"{self.__eta:.2f} sec"

    @property
    def downloaded_bytes_str(self) -> str:
        return f"{self.__downloaded_bytes} bytes"

    @property
    def size_str(self) -> str:
        return f"{self.__size} bytes"

    @property
    def progress_str(self) -> str:
        return f"{self.__progress * 100:.2f}%"

    @property
    def gid(self) -> str:
        return self.__gid

    @property
    def is_cancelled(self) -> bool:
        return self.__is_cancelled

    @property
    def download_started(self) -> bool:
        return self.__size > 0

    @property
    def download_completed(self) -> bool:
        return self.__downloaded_bytes == self.__size

    @property
    def download_aborted(self) -> bool:
        return self.__is_cancelled and not self.download_completed

    @property
    def download_failed(self) -> bool:
        return not self.download_completed and not self.download_aborted

    @property
    def download_status(self) -> str:
        if self.download_completed:
            return 'completed'
        elif self.download_aborted:
            return 'aborted'
        elif self.download_failed:
            return 'failed'
        else:
            return 'in progress'

    def __on_download_progress(self, d):
        if d['status'] == 'downloading':
            self.__downloading = True
            self.__size = d['total_bytes']
            if self.__size > 0:
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
            self.__update_name(d)
        elif d['status'] == 'failed':
            self.__downloading = False
            self.__gid = d['id']
            self.__size = 0
            self.__downloaded_bytes = 0
            self.__progress = 0
            self.__download_speed = 0
            self.__eta = '-'
            self.__update_name(d)

    @staticmethod
    def MyLogger() -> logging.Logger:
        logger = logging.getLogger()
        logger.setLevel(logging.DEBUG)
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        ch = logging.StreamHandler()
        ch.setFormatter(formatter)
        logger.addHandler(ch)
        return logger

    def __update_name(self, d):
        if not self.is_playlist:
            if match := re.search(r'.Merger..Merging formats into..(.*?).$', d['filename']):
                newname = match.group(1)
                newname = newname.rsplit("/", 1)[-1]
                self.name = newname

    def __del__(self):
        self.close()

    def __repr__(self):
        return (f'YoutubeDLHelper(name={self.name}, '
                f'is_playlist={self.is_playlist}, '
                f'download_status={self.download_status})')
