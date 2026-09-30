from aiofiles.os import path as aiopath
from asyncio import wait_for, Event, gather
from functools import partial
from logging import getLogger
from natsort import natsorted
from pyrogram.enums import ButtonStyle
from pyrogram.filters import regex, user
from pyrogram.handlers import CallbackQueryHandler
from tenacity import RetryError
from time import time

from ...ext_utils.bot_utils import new_task, sync_to_async
from ...ext_utils.status_utils import get_readable_file_size, get_readable_time
from ...mirror_leech_utils.gdrive_utils.delete import GoogleDriveDelete
from ...mirror_leech_utils.gdrive_utils.helper import GoogleDriveHelper
from ...telegram_helper.button_build import ButtonMaker
from ...telegram_helper.message_utils import (
    delete_message,
    edit_message,
    send_message,
)

LOGGER = getLogger(__name__)

LIST_LIMIT = 6


@new_task
async def drive_clean_cb(_, query, obj):
    await query.answer()
    message = query.message
    data = query.data.split()
    if obj.query_proc:
        return
    obj.query_proc = True
    action = data[1]
    if action == "cancel":
        obj.listener.is_cancelled = True
        obj.event.set()
        await delete_message(message)
    elif action == "pre":
        obj.iter_start -= LIST_LIMIT * obj.page_step
        await obj.get_items_buttons()
    elif action == "nex":
        obj.iter_start += LIST_LIMIT * obj.page_step
        await obj.get_items_buttons()
    elif action == "ps":
        if obj.page_step == int(data[2]):
            obj.query_proc = False
            return
        obj.page_step = int(data[2])
        await obj.get_items_buttons()
    elif action == "open":
        index = int(data[2])
        item = obj.items_list[index]
        obj.id = item["id"]
        obj.parents.append({"id": item["id"], "name": item["name"]})
        await obj.get_items()
    elif action == "back":
        await obj.get_pevious_id()
    elif action == "root":
        obj.id = obj.parents[0]["id"]
        obj.parents = [obj.parents[0]]
        await obj.get_items()
    elif action == "dr":
        index = int(data[2])
        drive = obj.drives[index]
        obj.id = drive["id"]
        obj.parents = [{"id": drive["id"], "name": drive["name"]}]
        await obj.get_items()
    elif action == "owner":
        obj.token_path = "token.pickle"
        obj.use_sa = False
        obj.id = ""
        obj.parents = []
        await obj.list_drives()
    elif action == "user":
        obj.token_path = obj.user_token_path
        obj.use_sa = False
        obj.id = ""
        obj.parents = []
        await obj.list_drives()
    elif action == "sa":
        obj.token_path = "accounts"
        obj.use_sa = True
        obj.id = ""
        obj.parents = []
        await obj.list_drives()
    elif action == "info":
        index = int(data[2])
        item = obj.items_list[index]
        name = item["name"]
        size = get_readable_file_size(float(item.get("size", 0)))
        mime = item.get("mimeType", "Unknown")
        await query.answer(f"Name: {name}\nSize: {size}\nType: {mime}", show_alert=True)
    elif action == "del":
        index = int(data[2])
        item = obj.items_list[index]
        obj._pending_del = (index, item)
        name = item["name"]
        size = get_readable_file_size(float(item.get("size", 0)))
        buttons = ButtonMaker()
        buttons.data_button("Yes, Delete", "gdc confirm", style=ButtonStyle.DANGER)
        buttons.data_button("No, Back", "gdc cancel_del", style=ButtonStyle.SUCCESS)
        await edit_message(
            message,
            f"Delete <code>{name}</code> ({size})?",
            buttons.build_menu(2),
        )
    elif action == "confirm":
        if obj._pending_del is None:
            obj.query_proc = False
            return
        _index, item = obj._pending_del
        file_id = item["id"]
        link = f"https://drive.google.com/file/d/{file_id}"
        msg = await sync_to_async(
            GoogleDriveDelete().deletefile, link, query.from_user.id
        )
        await query.answer(msg, show_alert=True)
        obj._pending_del = None
        await obj.get_items()
    elif action == "cancel_del":
        obj._pending_del = None
        await obj.get_items_buttons()
    obj.query_proc = False


class GoogleDriveClean(GoogleDriveHelper):
    def __init__(self, listener):
        self.listener = listener
        self._token_user = False
        self._token_owner = False
        self._sa_owner = False
        self._reply_to = None
        self._time = time()
        self._timeout = 240
        self.drives = []
        self.query_proc = False
        self.event = Event()
        self.user_token_path = f"tokens/{self.listener.user_id}.pickle"
        self.id = ""
        self.parents = []
        self.items_list = []
        self.iter_start = 0
        self.page_step = 1
        self._pending_del = None
        self._error_msg = None
        super().__init__()

    async def _event_handler(self):
        pfunc = partial(drive_clean_cb, obj=self)
        handler = self.listener.client.add_handler(
            CallbackQueryHandler(
                pfunc, filters=regex("^gdc") & user(self.listener.user_id)
            ),
            group=-1,
        )
        try:
            await wait_for(self.event.wait(), timeout=self._timeout)
        except Exception:
            self.id = "Timed Out. Task has been cancelled!"
            self.listener.is_cancelled = True
            self.event.set()
        finally:
            self.listener.client.remove_handler(*handler)

    async def _send_list_message(self, msg, button):
        if not self.listener.is_cancelled:
            if self._reply_to is None:
                self._reply_to = await send_message(self.listener.message, msg, button)
            else:
                await edit_message(self._reply_to, msg, button)

    async def get_items_buttons(self):
        items_no = len(self.items_list)
        pages = (items_no + LIST_LIMIT - 1) // LIST_LIMIT
        if items_no <= self.iter_start:
            self.iter_start = 0
        elif self.iter_start < 0 or self.iter_start > items_no:
            self.iter_start = LIST_LIMIT * (pages - 1)
        page = (self.iter_start / LIST_LIMIT) + 1 if self.iter_start != 0 else 1
        buttons = ButtonMaker()
        for index, item in enumerate(
            self.items_list[self.iter_start : LIST_LIMIT + self.iter_start]
        ):
            orig_index = index + self.iter_start
            if item["mimeType"] == self.G_DRIVE_DIR_MIME_TYPE:
                name = item["name"]
                buttons.data_button(f"📁 {name}", f"gdc open {orig_index}")
            else:
                name = f"[{get_readable_file_size(float(item['size']))}] {item['name']}"
                buttons.data_button(f"📄 {name}", f"gdc info {orig_index}")
            buttons.data_button("🗑️", f"gdc del {orig_index}", style=ButtonStyle.DANGER)
        if items_no > LIST_LIMIT:
            for i in [1, 2, 4, 6, 10]:
                buttons.data_button(i, f"gdc ps {i}", position="header")
            buttons.data_button("<< Previous", "gdc pre", position="footer")
            buttons.data_button("Next >>", "gdc nex", position="footer")
        if len(self.parents) > 1:
            buttons.data_button("Back", "gdc back", position="footer")
        if len(self.parents) > 1:
            buttons.data_button(
                "Back To Root",
                "gdc root",
                position="footer",
                style=ButtonStyle.SUCCESS,
            )
        buttons.data_button(
            "Cancel",
            "gdc cancel",
            position="footer",
            style=ButtonStyle.DANGER,
        )
        button = buttons.build_menu(2)
        path_str = "/".join(i["name"] for i in self.parents)
        msg = "<b>Google Drive Clean</b>"
        msg += f"\n\nItems: {items_no}"
        if items_no > LIST_LIMIT:
            msg += f" | Page: {int(page)}/{pages} | Page Step: {self.page_step}"
        msg += f"\n\nCurrent ID: <code>{self.id}</code>"
        msg += f"\nCurrent Path: <code>{path_str}</code>"
        msg += f"\nToken Path: {self.token_path}"
        msg += f"\nTimeout: {get_readable_time(self._timeout - (time() - self._time))}"
        await self._send_list_message(msg, button)

    async def get_items(self):
        try:
            files = self.get_files_by_folder_id(self.id)
            if self.listener.is_cancelled:
                return
        except Exception as err:
            if isinstance(err, RetryError):
                LOGGER.info(f"Total Attempts: {err.last_attempt.attempt_number}")
                err = err.last_attempt.exception()
            self._error_msg = str(err).replace(">", "").replace("<", "")
            self.id = self._error_msg
            self.listener.is_cancelled = True
            self.event.set()
            return
        self.items_list = natsorted(files)
        self.iter_start = 0
        await self.get_items_buttons()

    async def list_drives(self):
        self.service = self.authorize()
        try:
            result = self.service.drives().list(pageSize="100").execute()
        except Exception as e:
            self._error_msg = str(e)
            self.id = self._error_msg
            self.listener.is_cancelled = True
            self.event.set()
            return
        drives = result["drives"]
        if len(drives) == 0 and not self.use_sa:
            self.drives = [{"id": "root", "name": "root"}]
            self.parents = [{"id": "root", "name": "root"}]
            self.id = "root"
            await self.get_items()
        elif len(drives) == 0:
            msg = "Service accounts Doesn't have access to any drive!"
            buttons = ButtonMaker()
            if self._token_user and self._token_owner:
                buttons.data_button("Back", "gdc back", position="footer")
            buttons.data_button(
                "Cancel", "gdc cancel", position="footer", style=ButtonStyle.DANGER
            )
            button = buttons.build_menu(2)
            await self._send_list_message(msg, button)
        elif self.use_sa and len(drives) == 1:
            self.id = drives[0]["id"]
            self.drives = [{"id": self.id, "name": drives[0]["name"]}]
            self.parents = [{"id": self.id, "name": drives[0]["name"]}]
            await self.get_items()
        else:
            msg = "<b>Choose Drive:</b>"
            msg += f"\nToken Path: {self.token_path}"
            msg += (
                f"\nTimeout: {get_readable_time(self._timeout - (time() - self._time))}"
            )
            buttons = ButtonMaker()
            self.drives.clear()
            self.parents.clear()
            if not self.use_sa:
                buttons.data_button("root", "gdc dr 0")
                self.drives = [{"id": "root", "name": "root"}]
            for index, item in enumerate(drives, start=1):
                self.drives.append({"id": item["id"], "name": item["name"]})
                buttons.data_button(item["name"], f"gdc dr {index}")
            if self._token_user and self._token_owner:
                buttons.data_button("Back", "gdc back", position="footer")
            buttons.data_button(
                "Cancel", "gdc cancel", position="footer", style=ButtonStyle.DANGER
            )
            button = buttons.build_menu(2)
            await self._send_list_message(msg, button)

    async def choose_token(self):
        if (
            self._token_user
            and self._token_owner
            or self._sa_owner
            and self._token_owner
            or self._sa_owner
            and self._token_user
        ):
            msg = "<b>Choose Token:</b>"
            msg += (
                f"\nTimeout: {get_readable_time(self._timeout - (time() - self._time))}"
            )
            buttons = ButtonMaker()
            if self._token_owner:
                buttons.data_button("Owner Token", "gdc owner")
            if self._sa_owner:
                buttons.data_button("Service Accounts", "gdc sa")
            if self._token_user:
                buttons.data_button("My Token", "gdc user")
            buttons.data_button("Cancel", "gdc cancel", style=ButtonStyle.DANGER)
            button = buttons.build_menu(2)
            await self._send_list_message(msg, button)
        else:
            if self._token_owner:
                self.token_path = "token.pickle"
                self.use_sa = False
            elif self._token_user:
                self.token_path = self.user_token_path
                self.use_sa = False
            else:
                self.token_path = "accounts"
                self.use_sa = True
            await self.list_drives()

    async def get_pevious_id(self):
        if self.parents:
            self.parents.pop()
            if self.parents:
                self.id = self.parents[-1]["id"]
                await self.get_items()
            else:
                await self.list_drives()
        else:
            await self.list_drives()

    async def start(self, link=None, drive_id=None, cat_name=None):
        self._token_user, self._token_owner, self._sa_owner = await gather(
            aiopath.exists(self.user_token_path),
            aiopath.exists("token.pickle"),
            aiopath.exists("accounts"),
        )
        if not self._token_owner and not self._token_user and not self._sa_owner:
            self._error_msg = "token.pickle or service accounts do not exist!"
            self.id = self._error_msg
            self.listener.is_cancelled = True
            self.event.set()
            return

        if self._token_owner:
            self.token_path = "token.pickle"
            self.use_sa = False
        elif self._token_user:
            self.token_path = self.user_token_path
            self.use_sa = False
        else:
            self.token_path = "accounts"
            self.use_sa = True

        self.service = self.authorize()

        if link:
            try:
                file_id = self.get_id_from_url(link, self.listener.user_id)
            except (KeyError, IndexError):
                self._error_msg = (
                    "Google Drive ID could not be found in the provided link"
                )
                self.id = self._error_msg
                self.listener.is_cancelled = True
                self.event.set()
                return
            self.id = file_id
            try:
                meta = self.get_file_metadata(file_id)
            except Exception as err:
                if isinstance(err, RetryError):
                    LOGGER.info(f"Total Attempts: {err.last_attempt.attempt_number}")
                    err = err.last_attempt.exception()
                self._error_msg = str(err).replace(">", "").replace("<", "")
                self.id = self._error_msg
                self.listener.is_cancelled = True
                self.event.set()
                await self._event_handler()
                return
            name = meta.get("name", "root")
            self.parents = [{"id": file_id, "name": name}]
            if meta.get("mimeType") == self.G_DRIVE_DIR_MIME_TYPE:
                await self.get_items()
            else:
                self.items_list = [meta]
                await self.get_items_buttons()
            await self._event_handler()
        elif drive_id:
            self.id = drive_id
            self.parents = [{"id": drive_id, "name": "root"}]
            await self.get_items()
            await self._event_handler()
        else:
            await self.choose_token()
            await self._event_handler()
        if self._reply_to:
            await delete_message(self._reply_to)
        if not self.listener.is_cancelled:
            display_name = cat_name or "Selected"
            await send_message(
                self.listener.message,
                f"⌬ <b><i>Drive Cleaned</i></b>\n┟ <b>Category</b> → <code>{display_name}</code>\n┖ <b>Status</b> → <i>Completed</i>",
            )
        elif self._error_msg:
            await send_message(
                self.listener.message,
                f"⌬ <b><i>Drive Clean Error</i></b>\n┖ <b>Error</b> → <code>{self._error_msg}</code>",
            )
