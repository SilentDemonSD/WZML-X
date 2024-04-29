#!/usr/bin/env python3
from bot.helper.ext_utils.bot_utils import MirrorStatus, get_readable_file_size, get_readable_time

class DDLStatus:
    def __init__(self, obj, size, message, gid, upload_details):
        self.__obj = obj

