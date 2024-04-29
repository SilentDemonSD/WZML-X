#!/usr/bin/env python3
import asyncio
import configparser
import json
import os
import sys
import time
from functools import partial
from pathlib import Path
from typing import Any, Callable, List, Optional

import aiofiles
import pyrogram
from pyrogram.filters import regex, user
from pyrogram.handlers import CallbackQueryHandler
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message

# Import helper modules
import bot.helper.ext_utils.db_handler as DbManger
import bot.helper.telegram_helper.button_build as ButtonMaker
import bot.helper.telegram_helper.message_utils as message_utils

# Set the limit for the number of list items
LIST_LIMIT = 6


class RcloneList:
    def __init__(
        self,
        client: pyrogram.Client,
        message: Message,
    ) -> None:
        """
        Initialize the RcloneList class.

        :param client: Pyrogram client object
        :param message: Pyrogram message object
        """
        self.__user_id = message.from_user.id  # User ID
        self.__rc_user = False  # Flag for RC user
        self.__rc_owner = False  # Flag for RC owner
        self.__client = client  # Pyrogram client object
        self.__message = message  # Pyrogram message object
        self.__sections = []  # List of sections
        self.__reply_to = None  # Reply to message
        self.__time = time()  # Time when the object was created
        self.__timeout = 240  # Timeout in seconds
        self.remote = ""  # Remote name
        self.is_cancelled = False  # Flag for cancellation
        self.query_proc = False  # Flag for query processing
        self.item_type = "--dirs-only"  # Item type for listing
        self.event = asyncio.Event()  # Event for waiting
        self.user_rcc_path = f"rclone/{self.__user_id}.conf"  # User RC config path
        self.config_path = ""  # Config path
        self.path = ""  # Path for listing
        self.list_status = ""  # Status of the list
        self.path_list = []  # List of paths
        self.iter_start = 0  # Iterator start index
        self.page_step = 1  # Page step

    def __check_rclone(self) -> bool:
        """
        Check if rclone is installed.

        :return: True if rclone is installed, False otherwise
        """
        try:
            cmd = ["rclone", "version"]
            res, err, code = asyncio.get_event_loop().run_in_executor(None, cmd_exec, cmd)
            if code != 0:
                message_utils.send_message(
                    self.__message, "Rclone is not installed. Please install rclone first."
                )
                return False
        except FileNotFoundError:
            message_utils.send_message(
                self.__message, "Rclone is not installed. Please install rclone first."
            )
            return False
        return True

    def __check_rclone_config(self) -> bool:
        """
        Check if rclone config file exists.

        :return: True if rclone config file exists, False otherwise
        """
        if not Path(self.user_rcc_path).exists():
            message_utils.send_message(
                self.__message, "Rclone config file not found. Please create a config file first."
            )
            return False
        return True

    def __check_remote(self) -> bool:
        """
        Check if remote exists.

        :return: True if remote exists, False otherwise
        """
        cmd = ["rclone", "lsjson", "--config", self.config_path, f"{self.remote}"]
        res, err, code = asyncio.get_event_loop().run_in_executor(None, cmd_exec, cmd)
        if code != 0:
            message_utils.send_message(
                self.__message, f"Remote '{self.remote}' not found. Please create a remote first."
            )
            return False
        return True

    async def __event_handler(self) -> None:
        """
        Handle the event when the user interacts with the inline buttons.

        :return: None
        """
        pfunc = partial(path_updates, obj=self)
        handler = self.__client.add_handler(
            CallbackQueryHandler(pfunc, filters=regex("^rcq") & user(self.__user_id)),
            group=-1,
        )
        try:
            await self.event.wait()
        except asyncio.TimeoutError:
            self.path = ""
            self.remote = "Timed Out. Task has been cancelled!"
            self.is_cancelled = True
            self.event.set()
        finally:
            self.__client.remove_handler(*handler)

    async def __send_list_message(self, msg: str, button: List[List[str]]) -> None:
        """
        Send a message with inline buttons.

        :param msg: The message to be sent
        :param button: The inline buttons to be displayed
        :return: None
        """
        if not self.is_cancelled:
            if self.__reply_to is None:
                self.__reply_to = await message_utils.send_message(
                    self.__message, msg, button
                )
            else:
                await message_utils.edit_message(self.__reply_to, msg, button)

    async def get_path_buttons(self) -> None:
        """
        Generate and display the inline buttons for the user to choose a path.

        :return: None
        """
        items_no = len(self.path_list)
        pages = (items_no + LIST_LIMIT - 1) // LIST_LIMIT
        if items_no <= self.iter_start:
            self.iter_start = 0
        elif self.iter_start < 0 or self.iter_start > items_no:
            self.iter_start = LIST_LIMIT * (pages - 1)
        page = (self.iter_start / LIST_LIMIT) + 1 if self.iter_start != 0 else 1
        buttons = ButtonMaker.ButtonMaker()
        for index, idict in enumerate(
            self.path_list[self.iter_start : LIST_LIMIT + self.iter_start]
        ):
            orig_index = index + self.iter_start
            if idict["IsDir"]:
                ptype = "fo"
                name = idict["Path"]
            else:
                ptype = "fi"
                name = f"[{get_readable_file_size(idict['Size'])}] {idict['Path']}"
            buttons.ibutton(name, f"rcq pa {ptype} {orig_index}")
        if items_no > LIST_LIMIT:
            for i in [1, 2, 4, 6, 10, 30, 50, 100]:
                buttons.ibutton(str(i), f"rcq ps {i}", position="header")
            buttons.ibutton("Previous", "rcq pre", position="footer")
            buttons.ibutton("Next", "rcq nex", position="footer")
        if self.list_status == "rcd":
            if self.item_type == "--dirs-only":
                buttons.ibutton("Files", "rcq itype --files-only", position="footer")
            else:
                buttons.ibutton("Folders", "rcq itype --dirs-only", position="footer")
        if self.list_status in ["rcu", "rcd"] or len(self.path_list) > 0:
            buttons.ibutton("Choose Current Path", "rcq cur", position="footer")
        if self.list_status == "rcu":
            buttons.ibutton("Set as Default Path", "rcq def", position="footer")
        if self.path or len(self.__sections) > 1 or self.__rc_user and self.__rc_owner:
            buttons.ibutton("Back", "rcq back pa", position="footer")
        if self.path:
            buttons.ibutton("Back To Root", "rcq root", position="footer")
        buttons.ibutton("Cancel", "rcq cancel", position="footer")
        button = buttons.build_menu(f_cols=2)
        msg = (
            f"Choose Path:\nTransfer Type: <i>{'Download' if self.list_status == 'rcd' else 'Upload'}</i>"
        )
        if self.list_status == "rcu":
            default_path = config_dict["RCLONE_PATH"]
            msg += f"\nDefault Rclone Path: {default_path}" if default_path else ''
        msg += f"\nItems: {items_no}"
        if items_no > LIST_LIMIT:
            msg += f" | Page: {page}/{pages} | Page Step: {self.page_step}"
        msg += f"\nItem Type: {self.item_type}\nConfig Path: {self.config_path}"
        msg += f"\nCurrent Path: <code>{self.remote}{self.path}</code>"
        msg += f"\nTimeout: {get_readable_time(self.__timeout-(time()-self.__time))}"
        await self.__send_list_message(msg, button)

    async def get_path(self, itype: Optional[str] = None) -> None:
        """
        Get the list of files and directories in the current path.

        :param itype: The item type to be displayed. Defaults to None.
        :return: None
        """
        if itype:
            self.item_type = itype
        elif self.list_status == "rcu":
            self.item_type = "--dirs-only"
        if not self.__check_rclone():
            return
        if not self.__check_rclone_config():
            return
        if not self.__check_remote():
            return
        cmd = [
            "rclone",
            "lsjson",
            self.item_type,
            "--fast-list",
            "--no-mimetype",
            "--no-modtime",
            "--config",
            self.config_path,
            f"{self.remote}{self.path}",
        ]
        if self.is_cancelled:
            return
        res, err, code = await asyncio.get_event_loop().run_in_executor(None, cmd_exec, cmd)
        if code not in [0, -9]:
            LOGGER.error(
                f'While rclone listing. Path: {self.remote}{self.path}. Stderr: {err}'
            )
            self.remote = err[:4000]
            self.path = ""
            self.event.set()
            return
        try:
            result = json.loads(res)
        except json.JSONDecodeError as e:
            LOGGER.error(f'Error decoding JSON: {e}')
            self.remote = "Error decoding JSON"
            self.path = ""
            self.event.set()
            return
        if len(result) == 0 and itype != self.item_type and self.list_status == "rcd":
            itype = "--dirs-only" if self.item_type == "--files-only" else "--files-only"
            self.item_type = itype
            return await self.get_path(itype)
        self.path_list = sorted(result, key=lambda x: x["Path"])
        self.iter_start = 0
        await self.get_path_buttons()

    async def list_remotes(self) -> None:
        if not self.__check_rclone():
            return
        if not self.__check_rclone_config():
            return
        cmd = ["rclone", "listremotes", "--config", self.config_path]
        if self.is_cancelled:
            return
        res, err, code = await asyncio.get_event_loop().run_in_executor(None, cmd_exec, cmd)
        if code not in [0, -9]:
            LOGGER.error(f'While rclone listing remotes. Stderr: {err}')
            self.remote = err[:4000]
            self.event.set()
            return
        try:
            result = json.loads(res)
        except json.JSONDecodeError as e:
            LOGGER.error(f'Error decoding JSON: {e}')
            self.remote = "Error decoding JSON"
            self.event.set()
            return
        self.remote = result[0]["remote"]
        self.path = ""
        self.path_list = result
        await self.get_path_buttons()
