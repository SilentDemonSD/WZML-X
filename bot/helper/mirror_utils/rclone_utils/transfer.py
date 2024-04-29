import asyncio
import os
from re import findall as re_findall
from json import loads
from typing import List, Tuple, Dict, Any, Union, Optional
from aiofiles import open as aiopen, dirsize
from configparser import ConfigParser
from random import randrange
from logging import getLogger
from bot.helper.ext_utils.bot_utils import cmd_exec

LOGGER = getLogger(__name__)


class RcloneTransferHelper:
    def __init__(self, listener: Any, name: str):
        self.__listener = listener
        self.__proc = None
        self.__transferred_size = '0 B'
        self.__eta = '-'
        self.__percentage = '0%'
        self.__speed = '0 B/s'
        self.__size = '0 B'
        self.__is_cancelled = False
        self.__is_download = False
        self.__is_upload = False
        self.__sa_count = 1
        self.__sa_index = 0
        self.__sa_number = 0
        self.name = name

    @property
    def transferred_size(self) -> str:
        return self.__transferred_size

    @property
    def percentage(self) -> str:
        return self.__percentage

    @property
    def speed(self) -> str:
        return self.__speed

    @property
    def eta(self) -> str:
        return self.__eta

    @property
    def size(self) -> str:
        return self.__size

    async def __progress(self) -> None:
        while not (self.__proc is None or self.__is_cancelled):
            try:
                data = (await self.__proc.stdout.readline()).decode()
            except Exception:
                continue
            if not data:
                break
            if data := re_findall(r'Transferred:\s+([\d.]+\s*\w+)\s+/\s+([\d.]+\s*\w+),\s+([\d.]+%)\s*,\s+([\d.]+\s*\w+/s),\s+ETA\s+([\dwdhms]+)', data):
                self.__transferred_size, self.__size, self.__percentage, self.__speed, self.__eta = data[0]

    def __switch_service_account(self) -> str:
        if self.__sa_index == self.__sa_number - 1:
            self.__sa_index = 
