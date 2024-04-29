#!/usr/bin/env python3
import os
import re
import sys
import traceback
from typing import Any, Dict, List, Optional, Union

import aiofiles
import aiohttp
import aiorwlock
import youtube_dl
from bot import download_dict_lock, download_dict, non_queued_dl, queue_dict_lock, config_dict
from bot.helper.telegram_helper.message_utils import sendStatusMessage
from ..status_utils.yt_dlp_download_status import YtDlpDownloadStatus
from bot.helper.mirror_utils.status_utils.queue_status import QueueStatus
from bot.helper.ext_utils.bot_utils import sync_to_async, async_to_sync, is_queued, stop_duplicate_check, limit_checker


class MyLogger:
    def __init__(self, obj):
        self.obj = obj

    def debug(self, msg: str) -> None:
        # Hack to fix changing extension
        if not self.obj.is_playlist:
            if match := re.search(r'.Merger..Merging formats into..(.*?).$', msg) or \
                    re.search(r'.ExtractAudio..Destination..(.*?)$', msg):
                LOGGER.info(msg)
                newname = match.group(1)
                newname = newname.rsplit("/", 1)[-1]
                self.obj.name = newname

    @staticmethod
    def warning(msg: str) -> None:
        LOGGER.warning(msg)

    @staticmethod
    def error(msg: str) -> None:

