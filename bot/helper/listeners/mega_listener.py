from time import time
from secrets import token_hex
from aiofiles.os import makedirs
from asyncio import create_subprocess_exec, subprocess, wait_for
from re import search as re_search
from contextlib import suppress

from ... import LOGGER, task_dict, task_dict_lock
from ...core.config_manager import Config
from ..ext_utils.status_utils import MirrorStatus
from ..ext_utils.bot_utils import cmd_exec
from ..ext_utils.task_manager import (
    check_running_tasks,
    stop_duplicate_check,
    limit_checker,
)
from ..mirror_leech_utils.status_utils.mega_status import MegaDownloadStatus
from ..mirror_leech_utils.status_utils.queue_status import QueueStatus
from ..telegram_helper.message_utils import send_status_message


mega_tasks = {}


async def mega_cleanup():
    if not mega_tasks:
        return
    LOGGER.info("Running Mega Cleanup...")
    for path in list(mega_tasks.values()):
        try:
            await cmd_exec(["mega-rm", "-r", "-f", path])
        except Exception as e:
            LOGGER.error(f"Mega Restart Cleanup Failed for {path}: {e}")
    mega_tasks.clear()


class MegaAppListener:
    def __init__(self, listener):
        self.listener = listener
        self.process = None
        self.gid = token_hex(5)
        self.mega_status = None
        self.name = ""
        self.size = 0
        self.temp_path = f"/wzml_{self.gid}"
        self.mega_tags = set()
        self._is_cleaned = False
        self._last_time = time()
        self._val_last = 0
        mega_tasks[self.gid] = self.temp_path

    async def login(self):
        if (MEGA_EMAIL := Config.MEGA_EMAIL) and (
            MEGA_PASSWORD := Config.MEGA_PASSWORD
        ):
            try:
                await cmd_exec(["mega-login", MEGA_EMAIL, MEGA_PASSWORD])
            except Exception as e:
                raise Exception(f"Mega Login Failed: {e}")
        else:
            raise Exception("MegaCMD: Credentials Missing! Login required")

    async def create_temp_path(self):
        await cmd_exec(["mega-mkdir", self.temp_path])

    async def import_link(self):
        stdout, stderr, ret = await cmd_exec(
            ["mega-import", self.listener.link, self.temp_path]
        )
        if ret != 0:
            raise Exception(f"Mega Import Failed: {stderr}")

    async def get_metadata_and_target(self):
        stdout, _, ret = await cmd_exec(["mega-ls", "-l", self.temp_path])
        if ret != 0 or not stdout:
            raise Exception("Mega Metadata Failed")

        lines = [line for line in stdout.strip().split("\n") if line.strip()]
        if not lines:
            raise Exception("Mega Import: No items found")

        for line in lines:
            match = re_search(r"\s(\d+|-)\s+\S+\s+\d{2}:\d{2}:\d{2}\s+(.*)$", line)
            if match:
                size_str = match.group(1)
                self.name = match.group(2).strip()
                self.size = int(size_str) if size_str.isdigit() else 0
                break

        if not self.name:
            s_stdout, _, _ = await cmd_exec(["mega-ls", self.temp_path])
            if s_stdout:
                self.name = s_stdout.strip().split("\n")[0].strip()

        if not self.name:
            self.name = self.listener.name or f"MEGA_Download_{self.gid}"

        self.listener.name = self.name
        self.listener.size = self.size

        return f"{self.temp_path}/{self.name}"

    async def cleanup(self):
        if self._is_cleaned:
            return
        self._is_cleaned = True
        try:
            LOGGER.info(f"Cleaning up Mega Task: {self.name}")
            await cmd_exec(["mega-rm", "-r", "-f", self.temp_path])
            if self.gid in mega_tasks:
                del mega_tasks[self.gid]
        except Exception as e:
            LOGGER.error(f"Mega Cleanup Failed: {e}")

    async def download(self, path):
        try:
            await self.login()
            await self.create_temp_path()
            await self.import_link()
            target_node = await self.get_metadata_and_target()

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

            self.mega_status = MegaDownloadStatus(
                self.listener, self, self.gid, MirrorStatus.STATUS_DOWNLOAD
            )
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

            command = ["mega-get", target_node, path]

            self.process = await create_subprocess_exec(
                *command,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
            )

            while True:
                if self.listener.is_cancelled:
                    break

                try:
                    line_bytes = await wait_for(
                        self.process.stdout.readuntil(b"\r"), timeout=5
                    )
                    line = line_bytes.decode().strip()
                    if not line:
                        if self.process.returncode is not None:
                            break
                        continue
                    self._parse_progress(line)
                except TimeoutError:
                    await self.update_daemon_status()
                    if self.process.returncode is not None:
                        break
                    continue
                except Exception:
                    break

                if self.process.returncode is not None:
                    break

            await self.process.wait()

            if self.process.returncode == 0:
                await self.cleanup()
                await self.listener.on_download_complete()
            else:
                if self.listener.is_cancelled:
                    return
                if self.process.returncode != -9:
                    await self.listener.on_download_error(
                        f"MegaCMD exited with {self.process.returncode}"
                    )
        except Exception as e:
            if self.listener.is_cancelled:
                return
            LOGGER.error(f"Mega Download Logic Error: {e}")
            await self.listener.on_download_error(str(e))
        finally:
            await self.cleanup()

    def _parse_progress(self, line):
        multipliers = {"K": 1024, "M": 1024**2, "G": 1024**3, "T": 1024**4, "B": 1}
        match = re_search(r"\(([\d\.]+)/([\d\.]+)\s([KMGT]?B)", line)
        if match:
            dl_val = float(match.group(1))
            unit_char = (match.group(3))[0].upper()
            mult = multipliers.get(unit_char, 1)
            self.mega_status._downloaded_bytes = int(dl_val * mult)

            if not self.listener.size or self.listener.size == 0:
                total_val = float(match.group(2))
                self.mega_status._size = int(total_val * mult)
                self.listener.size = self.mega_status._size

            cur_time = time()
            if cur_time - self._last_time >= 2:
                self.mega_status._speed = int(
                    (self.mega_status._downloaded_bytes - self._val_last)
                    / (cur_time - self._last_time)
                )
                self._last_time = cur_time
                self._val_last = self.mega_status._downloaded_bytes

    async def update_daemon_status(self):
        try:
            stdout, _, _ = await cmd_exec(["mega-transfers", "--col-separator=|"])
            for line in stdout.splitlines():
                if self.gid in line:
                    parts = line.split("|")
                    if len(parts) > 1:
                        self.mega_tags.add(parts[1].strip())
                        if len(parts) > 4:
                            status = parts[5].strip().capitalize()
                            if self.mega_status._status != "Downloading":
                                self.mega_status._status = status
        except Exception:
            pass

    async def cancel_task(self):
        LOGGER.info(f"Cancelling {self.mega_status._status}: {self.name}")
        self.listener.is_cancelled = True

        await self.update_daemon_status()

        for tag in self.mega_tags:
            try:
                LOGGER.info(f"Cancelling Transfer Tag: {tag}")
                await cmd_exec(["mega-transfers", "-c", tag])
            except Exception as e:
                LOGGER.error(f"Mega Transfer Cancel Failed for {tag}: {e}")

        try:
            stdout, _, _ = await cmd_exec(["mega-transfers"])
            for line in stdout.splitlines():
                if self.gid in line:
                    parts = line.split()
                    if (
                        len(parts) > 1
                        and (tag := parts[1])
                        and tag not in self.mega_tags
                    ):
                        LOGGER.info(f"Cancelling Straggler Tag: {tag}")
                        await cmd_exec(["mega-transfers", "-c", tag])
        except Exception as e:
            LOGGER.error(f"Mega Final Cancel Check Failed: {e}")

        if self.process is not None:
            with suppress(Exception):
                self.process.kill()
