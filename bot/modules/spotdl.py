from asyncio import Event, wait_for
from functools import partial
from time import time

from pyrogram.filters import regex, user
from pyrogram.handlers import CallbackQueryHandler

from .. import DOWNLOAD_DIR, LOGGER, bot_loop, task_dict_lock
from ..core.config_manager import Config
from ..helper.ext_utils.bot_utils import (
    COMMAND_USAGE,
    arg_parser,
    new_task,
    sync_to_async,
)
from ..helper.ext_utils.links_utils import is_url
from ..helper.ext_utils.task_manager import pre_task_check
from ..helper.ext_utils.status_utils import get_readable_file_size, get_readable_time
from ..helper.listeners.task_listener import TaskListener
from ..helper.mirror_leech_utils.download_utils.spotdl_download import SpotDLHelper
from ..helper.telegram_helper.button_build import ButtonMaker
from ..helper.telegram_helper.message_utils import (
    auto_delete_message,
    delete_links,
    delete_message,
    edit_message,
    send_message,
)


LOSSY_FORMATS = {"mp3": [64, 128, 192, 256, 320], "ogg": [64, 128, 192, 256, 320],
                 "opus": [64, 96, 128, 160, 192], "m4a": [64, 128, 192, 256, 320]}
LOSSLESS_FORMATS = {"flac", "wav"}

@new_task
async def select_format(_, query, obj):
    data = query.data.split()
    message = query.message
    await query.answer()
    if data[1] == "cancel":
        await edit_message(message, "Task has been cancelled.")
        obj.qual = None
        obj.listener.is_cancelled = True
        obj.event.set()
    elif data[1] == "back":
        await obj.format_menu()
    elif data[1] == "bitrate":
        await obj.bitrate_menu(data[2])
    elif data[1] == "pick":
        obj.qual = data[2]
        obj.event.set()
    elif data[1] in LOSSY_FORMATS:
        await obj.bitrate_menu(data[1])
    elif data[1] in LOSSLESS_FORMATS:
        obj.qual = data[1]
        obj.event.set()
    else:
        obj.qual = data[1]
        obj.event.set()


class SpotdlSelection:
    def __init__(self, listener):
        self.listener = listener
        self._reply_to = None
        self._time = time()
        self._timeout = 120
        self.event = Event()
        self.qual = None

    async def _event_handler(self):
        pfunc = partial(select_format, obj=self)
        handler = self.listener.client.add_handler(
            CallbackQueryHandler(
                pfunc, filters=regex("^spdl") & user(self.listener.user_id)
            ),
            group=-1,
        )
        try:
            await wait_for(self.event.wait(), timeout=self._timeout)
        except Exception:
            await edit_message(self._reply_to, "Timed Out. Task has been cancelled!")
            self.qual = None
            self.listener.is_cancelled = True
            self.event.set()
        finally:
            self.listener.client.remove_handler(*handler)

    async def format_menu(self):
        buttons = ButtonMaker()
        for f in ["mp3", "flac", "ogg", "opus", "m4a", "wav"]:
            buttons.data_button(f, f"spdl {f}")
        buttons.data_button("Cancel", "spdl cancel", "footer")
        menu = buttons.build_menu(3)
        msg = f"Choose Audio Format:\nTimeout: {get_readable_time(self._timeout - (time() - self._time))}"
        await edit_message(self._reply_to, msg, menu)

    async def bitrate_menu(self, fmt):
        buttons = ButtonMaker()
        for q in LOSSY_FORMATS.get(fmt, []):
            label = f"{q}k"
            buttons.data_button(label, f"spdl pick {fmt}:{label}")
        buttons.data_button("Back", "spdl back", "footer")
        buttons.data_button("Cancel", "spdl cancel", "footer")
        menu = buttons.build_menu(3)
        msg = f"Choose Bitrate for <b>{fmt}</b>:\nTimeout: {get_readable_time(self._timeout - (time() - self._time))}"
        await edit_message(self._reply_to, msg, menu)

    async def get_format(self):
        buttons = ButtonMaker()
        for f in ["mp3", "flac", "ogg", "opus", "m4a", "wav"]:
            buttons.data_button(f, f"spdl {f}")
        buttons.data_button("Cancel", "spdl cancel", "footer")
        self._main_buttons = buttons.build_menu(3)
        msg = f"Choose Audio Format:\nTimeout: {get_readable_time(self._timeout - (time() - self._time))}"
        self._reply_to = await send_message(
            self.listener.message, msg, self._main_buttons
        )
        await self._event_handler()
        if not self.listener.is_cancelled:
            await delete_message(self._reply_to)
        return self.qual


class Spotdl(TaskListener):
    def __init__(
        self,
        client,
        message,
        is_leech=False,
        same_dir=None,
        bulk=None,
        multi_tag=None,
        options="",
        **kwargs,
    ):
        if same_dir is None:
            same_dir = {}
        if bulk is None:
            bulk = []
        self.message = message
        self.client = client
        self.multi_tag = multi_tag
        self.options = options
        self.same_dir = same_dir
        self.bulk = bulk
        super().__init__()
        self.is_spotdl = True
        self.is_leech = is_leech

    async def new_event(self):
        text = self.message.text.split("\n")
        input_list = text[0].split(" ")

        check_msg, check_button = await pre_task_check(self.message)
        if check_msg:
            await delete_links(self.message)
            await auto_delete_message(
                await send_message(self.message, check_msg, check_button)
            )
            return

        args = {
            "-doc": False,
            "-med": False,
            "-s": False,
            "-b": False,
            "-z": False,
            "-sv": False,
            "-ss": False,
            "-f": False,
            "-fd": False,
            "-fu": False,
            "-hl": False,
            "-bt": False,
            "-ut": False,
            "-i": 0,
            "-sp": 0,
            "link": "",
            "-m": "",
            "-meta": "",
            "-n": "",
            "-up": "",
            "-gc": "",
            "-rcf": "",
            "-t": "",
            "-ca": "",
            "-cv": "",
            "-ns": "",
            "-tl": "",
            "-ff": set(),
            "-fmt": "",
        }

        arg_parser(input_list[1:], args)

        if Config.DISABLE_FF_MODE and args.get("-ff"):
            await send_message(self.message, "FFmpeg commands are currently disabled.")
            return

        try:
            self.multi = int(args["-i"])
        except Exception:
            self.multi = 0

        self.select = args["-s"]
        self.name = args["-n"]
        self.up_dest = args["-up"]
        self.category = args["-gc"]
        self.rc_flags = args["-rcf"]
        self.link = args["link"]
        self.compress = args["-z"]
        self.thumb = args["-t"]
        self.split_size = args["-sp"]
        self.sample_video = args["-sv"]
        self.screen_shots = args["-ss"]
        self.force_run = args["-f"]
        self.force_download = args["-fd"]
        self.force_upload = args["-fu"]
        self.convert_audio = args["-ca"]
        self.convert_video = args["-cv"]
        self.name_swap = args["-ns"]
        self.hybrid_leech = args["-hl"]
        self.thumbnail_layout = args["-tl"]
        self.as_doc = args["-doc"]
        self.as_med = args["-med"]
        self.folder_name = f"/{args['-m']}".rstrip("/") if len(args["-m"]) > 0 else ""
        self.bot_trans = args["-bt"]
        self.user_trans = args["-ut"]
        self.metadata_dict = self.default_metadata_dict.copy()
        self.audio_metadata_dict = self.audio_metadata_dict.copy()
        self.video_metadata_dict = self.video_metadata_dict.copy()
        self.subtitle_metadata_dict = self.subtitle_metadata_dict.copy()
        if meta := args["-meta"]:
            self.metadata_dict = self.metadata_processor.merge_dicts(
                self.default_metadata_dict, self.metadata_processor.parse_string(meta)
            )

        output_format = args["-fmt"]

        is_bulk = args["-b"]

        bulk_start = 0
        bulk_end = 0
        reply_to = None

        if not isinstance(is_bulk, bool):
            dargs = is_bulk.split(":")
            bulk_start = dargs[0] or None
            if len(dargs) == 2:
                bulk_end = dargs[1] or None
            is_bulk = True

        if not is_bulk:
            if self.multi > 0:
                if self.folder_name:
                    async with task_dict_lock:
                        if self.folder_name in self.same_dir:
                            self.same_dir[self.folder_name]["tasks"].add(self.mid)
                            for fd_name in self.same_dir:
                                if fd_name != self.folder_name:
                                    self.same_dir[fd_name]["total"] -= 1
                        elif self.same_dir:
                            self.same_dir[self.folder_name] = {
                                "total": self.multi,
                                "tasks": {self.mid},
                            }
                            for fd_name in self.same_dir:
                                if fd_name != self.folder_name:
                                    self.same_dir[fd_name]["total"] -= 1
                        else:
                            self.same_dir = {
                                self.folder_name: {
                                    "total": self.multi,
                                    "tasks": {self.mid},
                                }
                            }
                elif self.same_dir:
                    async with task_dict_lock:
                        for fd_name in self.same_dir:
                            self.same_dir[fd_name]["total"] -= 1
        else:
            await self.init_bulk(input_list, bulk_start, bulk_end, Spotdl)
            return

        if len(self.bulk) != 0:
            del self.bulk[0]

        path = f"{DOWNLOAD_DIR}{self.mid}{self.folder_name}"

        await self.get_tag(text)

        if not self.link and (reply_to := self.message.reply_to_message):
            if reply_to.text:
                self.link = reply_to.text.split("\n", 1)[0].strip()

        if not (is_url(self.link) or "open.spotify.com" in self.link):
            await send_message(
                self.message, COMMAND_USAGE["spotdl"][0], COMMAND_USAGE["spotdl"][1]
            )
            await self.remove_from_same_dir()
            await delete_links(self.message)
            return

        try:
            await self.before_start()
        except Exception as e:
            await send_message(self.message, e)
            await self.remove_from_same_dir()
            await delete_links(self.message)
            return

        self._set_mode_engine()

        if self.select or not output_format:
            output_format = await SpotdlSelection(self).get_format()
            if output_format is None:
                await self.remove_from_same_dir()
                return

        LOGGER.info(f"Downloading with SpotDL: {self.link}")
        await delete_links(self.message)

        spdl = SpotDLHelper(self)
        await spdl.add_download(path, output_format)


async def spotdl(client, message):
    if Config.DISABLE_SPOTDL:
        await message.reply("SpotDL downloads are currently disabled by the Bot Owner.")
        return
    bot_loop.create_task(Spotdl(client, message).new_event())


async def spotdl_leech(client, message):
    if Config.DISABLE_SPOTDL:
        await message.reply("SpotDL downloads are currently disabled by the Bot Owner.")
        return
    bot_loop.create_task(Spotdl(client, message, is_leech=True).new_event())
