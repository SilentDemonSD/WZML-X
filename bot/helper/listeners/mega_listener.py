from secrets import token_hex
from aiofiles.os import makedirs
from asyncio import create_subprocess_exec, subprocess
from re import search as re_search

from ... import LOGGER, task_dict, task_dict_lock
from ...core.config_manager import Config
from ..ext_utils.bot_utils import cmd_exec
from ..ext_utils.task_manager import (
    check_running_tasks,
    stop_duplicate_check,
    limit_checker,
)
from ..mirror_leech_utils.status_utils.mega_dl_status import MegaDownloadStatus
from ..mirror_leech_utils.status_utils.queue_status import QueueStatus
from ..telegram_helper.message_utils import send_status_message


class MegaAppListener:
    def __init__(self, listener):
        self.listener = listener
        self.process = None
        self.gid = token_hex(5)
        self.mega_status = None
        self.name = ""
        self.size = 0

    async def login(self):
        if (MEGA_EMAIL := Config.MEGA_EMAIL) and (
            MEGA_PASSWORD := Config.MEGA_PASSWORD
        ):
            try:
                await cmd_exec(["mega-login", MEGA_EMAIL, MEGA_PASSWORD])
            except Exception as e:
                LOGGER.error(f"Mega Login Failed: {e}")
        else:
            LOGGER.info(
                "MegaCmd: Skipping login (No credentials). Proceeding anonymously."
            )

    async def get_metadata(self):
        try:
            # -l provides details. Expected format varies but contains metadata or file list.
            stdout, stderr, ret = await cmd_exec(["mega-ls", "-l", self.listener.link])
            if ret != 0 or not stdout:
                LOGGER.error(f"Mega metadata fetch failed: {stderr}")
                return

            lines = stdout.strip().split("\n")
            is_file_link = "file" in self.listener.link or "/#" in self.listener.link

            if is_file_link:
                # Regex to match file details line:
                # Format: permissions type size date time name
                # Example: -rwxr-x--- 1 file 1234567 2023-01-01 12:00 filename.ext
                match = re_search(
                    r"\s(\d+)\s\d{4}-\d{2}-\d{2}\s\d{2}:\d{2}:\d{2}\s(.*)$", lines[0]
                )
                if match:
                    self.size = int(match.group(1))
                    self.name = match.group(2).strip()
            else:
                # Folder link logic could go here
                pass

        except Exception as e:
            LOGGER.error(f"Metadata parsing error: {e}")

        if not self.name:
            self.name = self.listener.name or f"MEGA_Download_{token_hex(2)}"

        self.listener.name = self.name
        self.listener.size = self.size

    async def download(self, path):
        await self.login()
        await self.get_metadata()

        msg, button = await stop_duplicate_check(self.listener)
        if msg:
            await self.listener.on_download_error(msg, button)
            return

        if limit_exceeded := await limit_checker(self.listener):
            await self.listener.on_download_error(limit_exceeded, is_limit=True)
            return

        added_to_queue, event = await check_running_tasks(self.listener)
        if added_to_queue:
            LOGGER.info(f"Added to Queue/Download: {self.name}")
            async with task_dict_lock:
                task_dict[self.listener.mid] = QueueStatus(
                    self.listener, self.gid, "Dl"
                )
            await self.listener.on_download_start()
            if self.listener.multi <= 1:
                await send_status_message(self.listener.message)
            await event.wait()
            if self.listener.is_cancelled:
                return

        self.mega_status = MegaDownloadStatus(self.listener, None, self.gid, "dl")
        async with task_dict_lock:
            task_dict[self.listener.mid] = self.mega_status

        if added_to_queue:
            LOGGER.info(f"Start Queued Download from Mega: {self.name}")
        else:
            LOGGER.info(f"Download from Mega: {self.name}")
            await self.listener.on_download_start()
            if self.listener.multi <= 1:
                await send_status_message(self.listener.message)

        await makedirs(path, exist_ok=True)

        command = ["mega-get", self.listener.link, path]

        self.process = await create_subprocess_exec(
            *command,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )

        while True:
            try:
                line_bytes = await self.process.stdout.readuntil(b"\r")
            except Exception:
                break

            line = line_bytes.decode().strip()
            if not line:
                if self.process.returncode is not None:
                    break
                continue

            self._parse_progress(line)

            if self.process.returncode is not None:
                break

        await self.process.wait()

        if self.process.returncode == 0:
            await self.listener.on_download_complete()
        else:
            await self.listener.on_download_error(
                f"MegaCMD exited with {self.process.returncode}"
            )

    def _parse_progress(self, line):
        pct_match = re_search(r"\((\d+\.?\d*)%\)", line)
        if pct_match:
            pct = float(pct_match.group(1))
            if self.size > 0:
                self.mega_status._downloaded_bytes = int(self.size * pct / 100)

        speed_match = re_search(r"(\d+\.?\d*)\s([KMGT]?B)/s", line)
        if speed_match:
            val = float(speed_match.group(1))
            unit = speed_match.group(2)
            multipliers = {"K": 1024, "M": 1024**2, "G": 1024**3, "T": 1024**4, "B": 1}
            unit_char = unit[0].upper()
            mult = multipliers.get(unit_char, 1)
            self.mega_status._speed = int(val * mult)

    async def cancel_task(self):
        if self.process:
            self.process.kill()
