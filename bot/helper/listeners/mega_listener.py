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
        self.temp_path = f"/wzml_{self.gid}"
        self.is_cancelled = False

    async def login(self):
        if (MEGA_EMAIL := Config.MEGA_EMAIL) and (MEGA_PASSWORD := Config.MEGA_PASSWORD):
            try:
                await cmd_exec(["mega-login", MEGA_EMAIL, MEGA_PASSWORD])
            except Exception as e:
                raise Exception(f"Mega Login Failed: {e}")
        else:
            raise Exception("MegaCMD: Credentials Missing! Login required")

    async def create_temp_path(self):
        await cmd_exec(["mega-mkdir", self.temp_path])

    async def import_link(self):
        stdout, stderr, ret = await cmd_exec(["mega-import", self.listener.link, self.temp_path])
        if ret != 0:
            raise Exception(f"Mega Import Failed: {stderr}")

    async def get_metadata_and_target(self):
        stdout, _, ret = await cmd_exec(["mega-ls", "-l", self.temp_path])
        if ret != 0 or not stdout:
            raise Exception("Mega Metadata Failed")

        lines = [line for line in stdout.strip().split('\n') if line.strip()]
        if not lines:
            raise Exception("Mega Import: No items found")

        # Parse: FLAGS VERS SIZE DATE TIME NAME
        # Sample: ---- 1 1290207679 15Jun2025 18:10:36 Name.rar
        # Regex matches: Size (Number/-), Date (Any non-space), Time (XX:XX:XX), Name (Rest)
        for line in lines:
            match = re_search(r'\s(\d+|-)\s+\S+\s+\d{2}:\d{2}:\d{2}\s+(.*)$', line)
            if match:
                size_str = match.group(1)
                self.name = match.group(2).strip()
                self.size = int(size_str) if size_str.isdigit() else 0
                break
            
        if not self.name:
            s_stdout, _, _ = await cmd_exec(["mega-ls", self.temp_path])
            if s_stdout:
                 self.name = s_stdout.strip().split('\n')[0].strip()

        if not self.name:
            self.name = self.listener.name or f"MEGA_Download_{self.gid}"

        self.listener.name = self.name
        self.listener.size = self.size
        
        return f"{self.temp_path}/{self.name}"

    async def cleanup(self):
        try:
            await cmd_exec(["mega-rm", "-r", self.temp_path])
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
                    task_dict[self.listener.mid] = QueueStatus(self.listener, self.gid, "Dl")
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
            
            command = ["mega-get", target_node, path]
            
            self.process = await create_subprocess_exec(
                *command,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
            )
            
            while True:
                try:
                    line_bytes = await self.process.stdout.readuntil(b'\r')
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
                await self.listener.on_download_error(f"MegaCMD exited with {self.process.returncode}")
        except Exception as e:
            LOGGER.error(f"Mega Download Logic Error: {e}")
            await self.listener.on_download_error(str(e))
        finally:
            await self.cleanup()

    def _parse_progress(self, line):
        # Format: TRANSFERRING ||...||(31/1230 MB:   2.53 %)
        # Regex: \(([\d\.]+)/([\d\.]+)\s([KMGT]?B):\s*([\d\.]+)%\)
        # Group 1: DL, Group 2: Total, Group 3: Unit, Group 4: Pct
        
        match = re_search(r'\(([\d\.]+)/([\d\.]+)\s([KMGT]?B):\s*([\d\.]+)%\)', line)
        if match:
            dl_val = float(match.group(1))
            total_val = float(match.group(2))
            unit = match.group(3)
            pct = float(match.group(4))
            
            multipliers = {'K': 1024, 'M': 1024**2, 'G': 1024**3, 'T': 1024**4, 'B': 1}
            unit_char = unit[0].upper()
            mult = multipliers.get(unit_char, 1)
            
            current_bytes = int(dl_val * mult)
            self.mega_status._downloaded_bytes = current_bytes
            
            # self.listener.size = int(total_val * mult)
            
        speed_match = re_search(r'(\d+\.?\d*)\s([KMGT]?B)/s', line)
        if speed_match:
             val = float(speed_match.group(1))
             unit = speed_match.group(2)
             multipliers = {'K': 1024, 'M': 1024**2, 'G': 1024**3, 'T': 1024**4, 'B': 1}
             unit_char = unit[0].upper()
             mult = multipliers.get(unit_char, 1)
             self.mega_status._speed = int(val * mult)
            
    async def cancel_task(self):
        self.is_cancelled = True
        if self.process:
            self.process.kill()
