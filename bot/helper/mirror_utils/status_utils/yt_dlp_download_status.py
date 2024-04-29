#!/usr/bin/env python3
from bot.helper.ext_utils.bot_utils import EngineStatus, MirrorStatus
from bot.helper.ext_utils.fs_utils import get_path_size
from bot.helper.ext_utils.time_utils import get_readable_time
from typing import Union

class YtDlpDownloadStatus:
    def __init__(self, obj, listener, gid):
        self.obj = obj
        self.listener = listener
        self.upload_details = listener.upload_details
        self.gid = gid
        self.message = listener.message

