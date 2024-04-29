#!/usr/bin/env python3
from time import time

from bot.helper.ext_utils.bot_utils import EngineStatus, get_readable_file_size, MirrorStatus, get_readable_time, async_to_sync
from bot.helper.ext_utils.fs_utils import get_path_size

class ExtractStatus:
    def __init__(self, name: str, size: int, gid: int, listener):
        self.name = name
        self.size = size
        self.gid = gid
        self.listener = listener
        self.upload_details = listener.upload_details
        self.uid = listener.uid
        self.start_time = time()
        self.message = listener.message

    @property
    def readable_size(self):
        return get_readable_file_size(self.size)

    @property
    def readable_time_elapsed(self):
        return get_readable_time(time() - self.start_time)

    @property
    def path_size(self):
        return get_path_size(self.name)

