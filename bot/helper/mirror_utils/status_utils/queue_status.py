#!/usr/bin/env python3
from bot import LOGGER
from bot.helper.ext_utils.bot_utils import EngineStatus, get_readable_file_size, MirrorStatus

class QueueStatus:
    """
    Represents the status of a queue.
    """
    def __init__(self, name: str, size: int, gid: int, listener, status: str):
        self.__name = name
        self.__size = size
        self.__gid = gid
        self.__listener = listener
        self.upload_details = listener.upload_details
        self.__status = status
        self.message = listener.message

