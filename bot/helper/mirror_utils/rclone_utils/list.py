#!/usr/bin/env python3
import asyncio
import configparser
from functools import partial
from pathlib import Path
from typing import Any, Callable, List, Optional

import aiofiles
import pyrogram
from pyrogram.filters import regex, user
from pyrogram.handlers import CallbackQueryHandler

from bot import LOGGER, config_dict
from bot.helper.ext_utils.db_handler import DbManger
from bot.helper.telegram_helper.button_build import ButtonMaker
from bot.helper.telegram_helper.message_utils import (
    delete_message,
    send_message,
    edit_message,
)
from bot.helper.ext_utils.bot_utils import (
    cmd_exec,
    new_thread,
    get_readable_file_size,
    new_task,
    get_readable_time,
)

LIST_LIMIT = 6


class RcloneList:
    def __init__(
        self,
        client: pyrogram.Client,
        message: pyrogram.Message,
    ):
        self.__user_id = message.from_user.id
        self.__rc_user = False
        self.__rc_owner = False
        self.__client = client
        self.__message = message
        self.__sections = []
        self.__reply_to = None
        self.__time = time()
        self.__timeout = 240
        self.remote = ""
        self.is_cancelled = False
        self.query_proc = False
        self.item_type = "--dirs-only"
        self.event = asyncio.Event()
        self.user_rcc_path = f"rclone/{self.__user_id}.conf"
        self.config_path = ""
        self.path = ""
        self.list_status = ""
        self.path_list = []
        self.iter_start = 0
        self.page_step = 1

    @new_thread
    async def __event_handler(self):
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
        if not self.is_cancelled:
            if self.__reply_to is None:
                self.__reply_to = await send_message(self.__message, msg, button)
            else:
                await edit_message(self.__reply_to, msg, button)

    async def get_path_buttons(self):
        items_no = len(self.path_list)
        pages = (items_no + LIST_LIMIT - 1) // LIST_LIMIT
        if items_no <= self.iter_start:
            self.iter_start = 0
        elif self.iter_start < 0 or self.iter_start > items_no:
            self.iter_start = LIST_LIMIT * (pages - 1)
        page = (self.iter_start // LIST_LIMIT) + 1 if self.iter_start != 0 else 1
        buttons = ButtonMaker()
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
        if self.list_status == "rcu" or len(self.path_list) > 0:
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
            "Choose Path:"
            + ('\nTransfer Type: <i>Download</i>' if self.list_status == "rcd" else '\nTransfer Type: <i>Upload</i>')
        )
        if self.list_status == "rcu":
            default_path = config_dict["RCLONE_PATH"]
            msg += f"\nDefault Rclone Path: {default_path}" if default_path else ''
        msg += f'\n\nItems: {items_no}'
        if items_no > LIST_LIMIT:
            msg += f' | Page: {int(page)}/{pages} | Page Step: {self.page_step}'
        msg += f'\n\nItem Type: {self.item_type}\nConfig Path: {self.config_path}'
        msg += f'\nCurrent Path: <code>{self.remote}{self.path}</code>'
        msg += f'\nTimeout: {get_readable_time(self.__timeout-(time()-self.__time))}'
        await self.__send_list_message(msg, button)

    async def get_path(self, itype: Optional[str] = None):
        if itype:
            self.item_type = itype
        elif self.list_status == "rcu":
            self.item_type = "--dirs-only"
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
        res, err, code = await cmd_exec(cmd)
        if code not in [0, -9]:
            LOGGER.error(
                f'While rclone listing. Path: {self.remote}{self.path}. Stderr: {err}')
            self.remote = err[:4000]
            self.path = ""
            self.event.set()
            return
        result = loads(res)
        if len(result) == 0 and itype != self.item_type and self.list_status == "rcd":
            itype = "--dirs-only" if self.item_type == "--files-only" else "--files-only"
            self.item_type = itype
            return await self.get_path(itype)
        self.path_list = sorted(result, key=lambda x: x["Path"])
        self.iter_start = 0
        await self.get_path_buttons()

    async def list_remotes(self):
        config = configparser.ConfigParser()
        async with aiofiles.open(self.config_path, "r") as f:
            try:
                contents = await f.read()
                config.read_string(contents)
            except Exception as e:
                await delete_message(self.__reply_to)
                await send_message(
                    self.__message,
                    f"Error reading config file: {str(e)}",
                )
                return
        if config.has_section("combine"):
            config.remove_section("combine")
        self.__sections = config.sections()
        if len(self.__sections) == 1:
            self.remote = f"{self.__sections[0]}:"
            await self.get_path()
        else:
            msg = (
                'Choose Rclone remote:'
                + ('\nTransfer Type: <i>Download</i>' if self.list_status == "rcd" else '\nTransfer Type: <i>Upload</i>')
            )
            msg += f'\nConfig Path: {self.config_path}'
            msg += f'\nTimeout: {get_readable_time(self.__timeout-(time()-self.__time))}'
            buttons = ButtonMaker()
            for remote in self.__sections:
                buttons.ibutton(remote, f"rcq re {remote}:")
            if self.__rc_user and self.__rc_owner:
                buttons.ibutton("Back", "rcq back re", position="footer")
            buttons.ibutton("Cancel", "rcq cancel", position="footer")
            button = buttons.build_menu(2)
            await self.__send_list_message(msg, button)

    async def list_config(self):
        if self.__rc_user and self.__rc_owner:
            msg = (
                'Choose Rclone config:'
                + ('\nTransfer Type: Download' if self.list_status == "rcd" else '\nTransfer Type: Upload')
            )
            msg += f'\nTimeout: {get_readable_time(self.__timeout-(time()-self.__time))}'
            buttons = ButtonMaker()
            buttons.ibutton("Owner Config", "rcq owner")
            buttons.ibutton("My Config", "rcq user")
            buttons.ibutton("Cancel", "rcq cancel")
            button = buttons.build_menu(2)
            await self.__send_list_message(msg, button)
        else:
            self.config_path = "rclone.conf" if self.__rc_owner else self.user_rcc_path
            await self.list_remotes()

    async def back_from_path(self):
        if self.path:
            path = self.path.rsplit("/", 1)
            self.path = path[0] if len(path) > 1 else ""
            await self.get_path()
        elif len(self.__sections) > 1:
            await self.list_remotes()
        else:
            await self.list_config()

    async def get_rclone_path(
        self, status: str, config_path: Optional[str] = None
    ) -> Optional[str]:
        self.list_status = status
        future = self.__event_handler()
        if config_path is None:
            self.__rc_user = Path(self.user_rcc_path).exists()
            self.__rc_owner = Path("rclone.conf").exists()
            if not self.__rc_owner and not self.__rc_user:
                self.event.set()
                return "Rclone Config not Exists!"
            await self.list_config()
        else:
            self.config_path = config_path
            await self.list_remotes()
        await asyncio.wait([future])
        await delete_message(self.__reply_to)
        if self.config_path != "rclone.conf" and not self.is_cancelled:
            return f"mrcc:{self.remote}{self.path}"
        return f"{self.remote}{self.path}"

