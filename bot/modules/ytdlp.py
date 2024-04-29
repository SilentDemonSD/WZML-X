import asyncio
import contextlib
import os
import sys
import time
import traceback
from typing import Any, Callable, Dict, List, Optional, Union

import aiofiles
import aiohttp
import pyrogram
from pyrogram.errors import FloodWait, MessageNotModified, MessageNotFound
from pyrogram.handlers import MessageHandler, CallbackQueryHandler
from pyrogram.filters import command, regex, user
from yt_dlp import YoutubeDL
from yt_dlp.utils import DownloadError

from bot import DOWNLOAD_DIR, bot, categories_dict, config_dict, user_data, LOGGER
from bot.helper.ext_utils.task_manager import task_utils
from bot.helper.telegram_helper.message_utils import (
    sendMessage,
    editMessage,
    deleteMessage,
    auto_delete_message,
    delete_links,
    open_category_btns,
    open_dump_btns,
)
from bot.helper.telegram_helper.button_build import ButtonMaker
from bot.helper.ext_utils.bot_utils import (
    get_readable_file_size,
    fetch_user_tds,
    fetch_user_dumps,
    is_url,
    is_gdrive_link,
    new_task,
    sync_to_async,
    is_rclone_path,
    new_thread,
    get_readable_time,
    arg_parser,
)
from bot.helper.mirror_utils.download_utils.yt_dlp_download import YoutubeDLHelper
from bot.helper.mirror_utils.rclone_utils.list import RcloneList
from bot.helper.telegram_helper.bot_commands import BotCommands
from bot.helper.mirror_utils.upload_utils.gdrive_tools import GoogleDriveHelper
from bot.helper.telegram_helper.filters import CustomFilters
from bot.helper.listeners.tasks_listener import MirrorLeechListener
from bot.helper.ext_utils.help_messages import YT_HELP_MESSAGE
from bot.helper.ext_utils.bulk_links import extract_bulk_links


@new_task
async def select_format(query: pyrogram.types.CallbackQuery, obj: "YtSelection"):
    data = query.data.split()
    message = query.message
    await query.answer()

    if data[1] == "dict":
        b_name = data[2]
        await obj.qual_subbuttons(b_name)
    elif data[1] == "mp3":
        await obj.mp3_subbuttons()
    elif data[1] == "audio":
        await obj.audio_format()
    elif data[1] == "aq":
        if data[2] == "back":
            await obj.audio_format()
        else:
            await obj.audio_quality(data[2])
    elif data[1] == "back":
        await obj.back_to_main()
    elif data[1] == "cancel":
        await editMessage(message, "Task has been cancelled.")
        obj.qual = None
        obj.is_cancelled = True
        obj.event.set()
    else:
        if data[1] == "sub":
            obj.qual = obj.formats[data[2]][data[3]][1]
        elif "|" in data[1]:
            obj.qual = obj.formats[data[1]]
        else:
            obj.qual = data[1]
        obj.event.set()


class YtSelection:
    def __init__(
        self,
        client: pyrogram.Client,
        message: pyrogram.types.Message,
    ):
        self.__message = message
        self.__user_id = message.from_user.id
        self.__client = client
        self.__is_m4a = False
        self.__reply_to = None
        self.__time = time.time()
        self.__timeout = 120
        self.__is_playlist = False
        self.is_cancelled = False
        self.__main_buttons = None
        self.event = asyncio.Event()
        self.formats = {}
        self.qual = None

    @new_thread
    async def __event_handler(self):
        pfunc = partial(select_format, obj=self)
        handler = self.__client.add_handler(
            CallbackQueryHandler(pfunc, filters=regex("^ytq") & user(self.__user_id)),
            group=-1,
        )
        try:
            await self.event.wait()
        except asyncio.TimeoutError:
            await editMessage(
                self.__reply_to, "Timed Out. Task has been cancelled!"
            )
            self.qual = None
            self.is_cancelled = True
            self.event.set()
        finally:
            self.__client.remove_handler(*handler)

    async def get_quality(self, result: dict):
        future = self.__event_handler()
        buttons = ButtonMaker()
        if "entries" in result:
            self.__is_playlist = True
            for i in ["144", "240", "360", "480", "720", "108
