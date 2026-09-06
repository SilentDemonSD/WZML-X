from asyncio import gather
from json import loads
from secrets import token_hex

from aiofiles.os import remove

from .. import LOGGER, bot_loop, task_dict, task_dict_lock
from ..core.config_manager import BinConfig
from ..helper.ext_utils.bot_utils import (
    COMMAND_USAGE,
    arg_parser,
    cmd_exec,
    sync_to_async,
)
from ..core.tg_client import TgClient
from ..helper.ext_utils.session_vault import UserSession
from ..helper.ext_utils.exceptions import (
    DirectDownloadLinkException,
    TgLinkException,
)
from ..helper.ext_utils.filter_utils import file_name_of, size_of
from ..helper.ext_utils.links_utils import (
    is_gdrive_id,
    is_telegram_link,
    is_gdrive_link,
    is_mega_link,
    is_mega_folder_link,
    is_rclone_path,
    is_share_link,
)
from ..helper.ext_utils.task_manager import (
    check_running_tasks,
    pre_task_check,
    start_from_queued,
    stop_duplicate_check,
    limit_checker,
)
from ..helper.ext_utils.status_utils import get_readable_file_size
from ..helper.listeners.task_listener import TaskListener
from ..helper.mirror_leech_utils.download_utils.direct_link_generator import (
    direct_link_generator,
)
from ..helper.mirror_leech_utils.gdrive_utils.clone import GoogleDriveClone
from ..helper.mirror_leech_utils.gdrive_utils.count import GoogleDriveCount
from ..helper.mirror_leech_utils.rclone_utils.transfer import RcloneTransferHelper
from ..helper.mirror_leech_utils.upload_utils.mega_clone import add_mega_clone
from ..helper.mirror_leech_utils.status_utils.gdrive_status import GoogleDriveStatus
from ..helper.mirror_leech_utils.status_utils.queue_status import QueueStatus
from ..helper.mirror_leech_utils.status_utils.rclone_status import RcloneStatus
from ..helper.mirror_leech_utils.status_utils.tg_clone_status import (
    TelegramCloneStatus,
)
from ..helper.mirror_leech_utils.telegram_utils.clone import (
    MAX_CLONE_MESSAGES,
    TelegramClone,
    build_units,
)
from ..helper.telegram_helper.button_build import ButtonMaker
from ..helper.telegram_helper.prompt import PromptUnreachable
from ..helper.telegram_helper.message_utils import (
    TgSource,
    auto_delete_message,
    delete_links,
    delete_message,
    send_message,
    send_status_message,
)


def _pm_button():
    btns = ButtonMaker()
    btns.url_button("Open in PM", f"https://t.me/{TgClient.BNAME}")
    return btns.build_menu(1)


class Clone(TaskListener):
    def __init__(
        self,
        client,
        message,
        bulk=None,
        multi_tag=None,
        options="",
        **kwargs,
    ):
        if bulk is None:
            bulk = []
        self.message = message
        self.client = client
        self.multi_tag = multi_tag
        self.options = options
        self.same_dir = {}
        self.bulk = bulk
        super().__init__()
        self.is_clone = True

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
            "link": "",
            "-i": 0,
            "-b": False,
            "-n": "",
            "-up": "",
            "-gc": "",
            "-rcf": "",
            "-sync": False,
            "-ud": "",
            "-ct": "",
            "-ex": "",
            "-mn": "",
            "-xn": "",
            "-mc": "",
            "-xc": "",
            "-fwd": False,
        }

        arg_parser(input_list[1:], args)

        try:
            self.multi = int(args["-i"])
        except Exception:
            self.multi = 0

        self.up_dest = args["-up"]
        self.category = args["-gc"]
        self.rc_flags = args["-rcf"]
        self.link = args["link"]
        self.name = args["-n"]
        self.dump_dest = args["-ud"]
        self.clone_content_type = args["-ct"].strip().lower()
        self.clone_excluded = args["-ex"]
        self.clone_regex = {key: args[f"-{key}"] for key in ("mn", "xn", "mc", "xc")}
        self.clone_forward = bool(args["-fwd"])

        is_bulk = args["-b"]
        sync = args["-sync"]
        bulk_start = 0
        bulk_end = 0

        if not isinstance(is_bulk, bool):
            dargs = is_bulk.split(":")
            bulk_start = dargs[0] or 0
            if len(dargs) == 2:
                bulk_end = dargs[1] or 0
            is_bulk = True

        if is_bulk:
            await self.init_bulk(input_list, bulk_start, bulk_end, Clone)
            return

        await self.get_tag(text)

        if not self.link and (reply_to := self.message.reply_to_message):
            self.link = (reply_to.text or "").split("\n", 1)[0].strip() or (
                reply_to.link or ""
            )

        await self.run_multi(input_list, Clone)

        if len(self.link) == 0:
            await send_message(
                self.message, COMMAND_USAGE["clone"][0], COMMAND_USAGE["clone"][1]
            )
            await delete_links(self.message)
            return
        self.is_tg_clone = is_telegram_link(self.link)
        if is_mega_link(self.link) and self.up_dest not in ("mega", "mega:"):
            self.up_dest = "mega:"
        LOGGER.info(self.link)
        try:
            await self.before_start()
        except Exception as e:
            await send_message(self.message, e)
            await delete_links(self.message)
            return

        self._set_mode_engine()

        await self._proceed_to_clone(sync)
        await delete_links(self.message)

    async def _proceed_tg_clone(self):
        if UserSession.exists(self.user_id):
            try:
                await UserSession.unlock(self.user_id)
            except TgLinkException as e:
                await send_message(self.message, f"ERROR: {e}")
                return
            except PromptUnreachable as e:
                await send_message(self.message, f"ERROR: {e}", _pm_button())
                return
            async with UserSession.borrow(self.user_id) as mine:
                await self._relay_from(mine)
            return
        await self._relay_from(None)

    async def _relay_from(self, mine):
        try:
            messages, asked, _session, source = await TgSource.resolve(
                self.link, MAX_CLONE_MESSAGES, extra=mine
            )
        except TgLinkException as e:
            await send_message(self.message, f"ERROR: {e}")
            return
        self.clone_source = source
        client = {"bot": TgClient.bot, "user": TgClient.user, "usess": mine}[_session]
        units = await build_units(client, source.chat, messages)
        kept = []
        dropped = 0
        for unit in units:
            passed = [one for one in unit if self.clone_filter.keep(one)]
            if not passed:
                dropped += len(unit)
                continue
            if len(passed) == len(unit):
                kept.append(unit)
            else:
                dropped += len(unit) - len(passed)
                kept.extend([[one] for one in passed])
        if not kept:
            await send_message(
                self.message, "No messages matched the filters, nothing to clone."
            )
            return

        self.size = sum(size_of(one) for unit in kept for one in unit)
        if not self.name:
            self.name = (
                f"{source.chat} [{source.start_id}-{source.end_id}]"
                if asked > 1
                else file_name_of(kept[0][0]) or f"message {source.start_id}"
            )
        if limit_exceeded := await limit_checker(self):
            await send_message(
                self.message,
                f"""〶 <b><i><u>Limit Breached:</u></i></b>
│
┟ <b>Task Size</b> → {get_readable_file_size(self.size)}
┠ <b>In Mode</b> → {self.mode[0]}
┠ <b>Out Mode</b> → {self.mode[1]}
{limit_exceeded}""",
            )
            return

        gid = token_hex(5)
        worker = TelegramClone(self, client, kept, self.clone_dests, self.clone_forward)
        add_to_queue, event = await check_running_tasks(self, "up")
        await start_from_queued()
        if add_to_queue:
            LOGGER.info(f"Added to Queue/Clone: {self.name}")
            async with task_dict_lock:
                task_dict[self.mid] = QueueStatus(self, gid, "up")
            await self.on_download_start()
            if self.multi <= 1:
                await send_status_message(self.message)
            await event.wait()
            if self.is_cancelled:
                return
        else:
            await self.on_download_start()

        async with task_dict_lock:
            task_dict[self.mid] = TelegramCloneStatus(self, worker, gid)
        if self.multi <= 1:
            await send_status_message(self.message)

        LOGGER.info(
            f"Clone Started: {self.name} - {len(kept)} units "
            f"to {len(self.clone_dests)} chats"
        )
        await worker.relay()
        if self.is_cancelled:
            return
        self.clone_stats = {
            "copied": worker.copied,
            "asked": asked,
            "dests": len(self.clone_dests),
            "dropped": dropped + (asked - len(messages)),
            "restricted": worker.restricted,
            "failed": worker.failed,
            "dead": worker.dead_dests,
            "link": self.link,
        }
        await self.on_upload_complete(
            worker.first_link, worker.copied, len(worker._dests), "Telegram"
        )
        LOGGER.info(f"Cloning Done: {self.name}")

    async def _proceed_to_clone(self, sync):
        if self.is_tg_clone:
            await self._proceed_tg_clone()
            return
        if is_share_link(self.link):
            try:
                self.link = await sync_to_async(direct_link_generator, self.link)
                LOGGER.info(f"Generated link: {self.link}")
            except DirectDownloadLinkException as e:
                LOGGER.error(str(e))
                if str(e).startswith("ERROR:"):
                    await send_message(self.message, str(e))
                    return
        if is_gdrive_link(self.link) or is_gdrive_id(self.link):
            self.name, mime_type, self.size, files, _ = await sync_to_async(
                GoogleDriveCount().count, self.link, self.user_id
            )
            if mime_type is None:
                await send_message(self.message, self.name)
                return
            msg, button = await stop_duplicate_check(self)
            if msg:
                await send_message(self.message, msg, button)
                return
            if limit_exceeded := await limit_checker(self):
                await send_message(
                    self.message,
                    f"""〶 <b><i><u>Limit Breached:</u></i></b>
│
┟ <b>Task Size</b> → {get_readable_file_size(self.size)}
┠ <b>In Mode</b> → {self.mode[0]}
┠ <b>Out Mode</b> → {self.mode[1]}
{limit_exceeded}""",
                )
                return
            await self.on_download_start()
            LOGGER.info(f"Clone Started: Name: {self.name} - Source: {self.link}")
            drive = GoogleDriveClone(self)
            if files <= 10:
                msg = await send_message(
                    self.message, f"Cloning: <code>{self.link}</code>"
                )
            else:
                msg = ""
                gid = token_hex(5)
                async with task_dict_lock:
                    task_dict[self.mid] = GoogleDriveStatus(self, drive, gid, "cl")
                if self.multi <= 1:
                    await send_status_message(self.message)
            flink, mime_type, files, folders, dir_id = await sync_to_async(drive.clone)
            if msg:
                await delete_message(msg)
            if not flink:
                return
            await self.on_upload_complete(
                flink, files, folders, mime_type, dir_id=dir_id
            )
            LOGGER.info(f"Cloning Done: {self.name}")
        elif is_rclone_path(self.link):
            if self.link.startswith("mrcc:"):
                self.link = self.link.replace("mrcc:", "", 1)
                self.up_dest = self.up_dest.replace("mrcc:", "", 1)
                config_path = f"rclone/{self.user_id}.conf"
            else:
                config_path = "rclone.conf"

            remote, src_path = self.link.split(":", 1)
            self.link = src_path.strip("/")
            if self.link.startswith("rclone_select"):
                mime_type = "Folder"
                src_path = ""
                if not self.name:
                    self.name = self.link
            else:
                src_path = self.link
                cmd = [
                    BinConfig.RCLONE_NAME,
                    "lsjson",
                    "--fast-list",
                    "--stat",
                    "--no-modtime",
                    "--config",
                    config_path,
                    f"{remote}:{src_path}",
                ]
                res = await cmd_exec(cmd)
                if res[2] != 0:
                    if res[2] != -9:
                        msg = f"Error: While getting rclone stat. Path: {remote}:{src_path}. Stderr: {res[1][:4000]}"
                        await send_message(self.message, msg)
                    return
                rstat = loads(res[0])
                if rstat["IsDir"]:
                    if not self.name:
                        self.name = src_path.rsplit("/", 1)[-1] if src_path else remote
                    self.up_dest += (
                        self.name if self.up_dest.endswith(":") else f"/{self.name}"
                    )
                    mime_type = "Folder"
                else:
                    if not self.name:
                        self.name = src_path.rsplit("/", 1)[-1]
                    mime_type = rstat["MimeType"]

            await self.on_download_start()

            RCTransfer = RcloneTransferHelper(self)
            LOGGER.info(
                f"Clone Started: Name: {self.name} - Source: {self.link} - Destination: {self.up_dest}"
            )
            gid = token_hex(5)
            async with task_dict_lock:
                task_dict[self.mid] = RcloneStatus(self, RCTransfer, gid, "cl")
            if self.multi <= 1:
                await send_status_message(self.message)
            method = "sync" if sync else "copy"
            flink, destination = await RCTransfer.clone(
                config_path,
                remote,
                src_path,
                mime_type,
                method,
            )
            if self.link.startswith("rclone_select"):
                await remove(self.link)
            if not destination:
                return
            LOGGER.info(f"Cloning Done: {self.name}")
            cmd1 = [
                BinConfig.RCLONE_NAME,
                "lsf",
                "--fast-list",
                "-R",
                "--files-only",
                "--config",
                config_path,
                destination,
            ]
            cmd2 = [
                BinConfig.RCLONE_NAME,
                "lsf",
                "--fast-list",
                "-R",
                "--dirs-only",
                "--config",
                config_path,
                destination,
            ]
            cmd3 = [
                BinConfig.RCLONE_NAME,
                "size",
                "--fast-list",
                "--json",
                "--config",
                config_path,
                destination,
            ]
            res1, res2, res3 = await gather(
                cmd_exec(cmd1),
                cmd_exec(cmd2),
                cmd_exec(cmd3),
            )
            if res1[2] != 0 or res2[2] != 0 or res3[2] != 0:
                if res1[2] == -9:
                    return
                files = None
                folders = None
                self.size = 0
                error = res1[1] or res2[1] or res3[1]
                msg = f"Error: While getting rclone stat. Path: {destination}. Stderr: {error[:4000]}"
                await self.on_upload_error(msg)
            else:
                files = len(res1[0].split("\n"))
                folders = len(res2[0].strip().split("\n")) if res2[0] else 0
                rsize = loads(res3[0])
                self.size = rsize["bytes"]
                await self.on_upload_complete(
                    flink, files, folders, mime_type, destination
                )
        elif is_mega_link(self.link):
            if is_mega_folder_link(self.link):
                await send_message(
                    self.message,
                    "Mega folder clone is not supported. Only file links can be cloned.",
                )
                return

            mega_email = self.user_dict.get("MEGA_EMAIL") or ""
            mega_password = self.user_dict.get("MEGA_PASSWORD") or ""
            if not mega_email or not mega_password:
                await send_message(
                    self.message, "Mega credentials not configured for this user."
                )
                return

            if not self.name:
                self.name = f"mega_file_{token_hex(4)}"

            self.size = 0
            await self.on_download_start()

            gid = token_hex(5)
            LOGGER.info(f"Clone Started: Name: {self.name} - Source: {self.link}")

            flink, files, folders = await add_mega_clone(
                self, self.link, mega_email, mega_password, gid
            )
            if not flink:
                return
            mime_type = "Folder" if folders else "application/octet-stream"
            await self.on_upload_complete(flink, files, folders, mime_type, dir_id=None)
            LOGGER.info(f"Cloning Done: {self.name}")
        else:
            await send_message(
                self.message, COMMAND_USAGE["clone"][0], COMMAND_USAGE["clone"][1]
            )


async def clone_node(client, message):
    bot_loop.create_task(Clone(client, message).new_event())
