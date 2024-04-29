import asyncio
import os
import re
import json
from typing import List, Tuple, Dict, Any, Union, Optional
from asyncio.subprocess import PIPE
import aiofiles
import aiofiles.os
import configparser
import logging
import shutil
import tarfile
from bot.helper.ext_utils.bot_utils import cmd_exec
from bot.helper.ext_utils.fs_utils import get_mime_type, count_files_and_folders

logger = logging.getLogger(__name__)

class RcloneTransferHelper:
    def __init__(self, listener: Any, name: str):
        self.listener = listener
        self.name = name
        self.proc = None
        self.transferred_size = "0 B"
        self.eta = "-"
        self.percentage = "0%"
        self.speed = "0 B/s"
        self.size = "0 B"
        self.is_cancelled = False
        self.is_download = False
        self.is_upload = False
        self.sa_count = 1
        self.sa_index = 0
        self.sa_number = 0

    @property
    def transferred_size(self):
        return self.__transferred_size

    @transferred_size.setter
    def transferred_size(self, value: str):
        self.__transferred_size = value

    @property
    def percentage(self):
        return self.__percentage

    @percentage.setter
    def percentage(self, value: str):
        self.__percentage = value

    @property
    def speed(self):
        return self.__speed

    @speed.setter
    def speed(self, value: str):
        self.__speed = value

    @property
    def eta(self):
        return self.__eta

    @eta.setter
    def eta(self, value: str):
        self.__eta = value

    @property
    def size(self):
        return self.__size

    @size.setter
    def size(self, value: str):
        self.__size = value

    async def __progress(self):
        while not (self.proc is None or self.is_cancelled):
            try:
                data = (await self.proc.stdout.readline()).decode()
            except Exception as e:
                logger.error(f"Error reading progress: {e}")
                continue
            if not data:
                break
            if match := re.findall(r'Transferred:\s+([\d.]+\s*\w+)\s+/\s+([\d.]+\s*\w+),\s+([\d.]+%)\s*,\s+([\d.]+\s*\w+/s),\s+ETA\s+([\dwdhms]+)', data):
                self.transferred_size, self.size, self.percentage, self.speed, self.eta = match[0]

    def __switch_service_account(self):
        if self.sa_index == self.sa_number - 1:
            self.sa_index = 0
        else:
            self.sa_index += 1
        self.sa_count += 1
        remote = f'sa{self.sa_index:03}'
        logger.info(f"Switching to {remote} remote")
        return remote

    async def __create_rc_sa(self, remote: str, remote_opts: Dict[str, str]) -> str:
        sa_conf_dir = 'rclone_sa'
        sa_conf_file = f'{sa_conf_dir}/{remote}.conf'
        if not await aiofiles.os.path.isdir(sa_conf_dir):
            await aiofiles.os.mkdir(sa_conf_dir)
        elif await aiofiles.os.path.isfile(sa_conf_file):
            return sa_conf_file

        if gd_id := remote_opts.get('team_drive'):
            option = 'team_drive'
        elif gd_id := remote_opts.get('root_folder_id'):
            option = 'root_folder_id'
        else:
            return 'rclone.conf'

        files = await aiofiles.os.listdir('accounts')
        text = ''.join(f"[sa{i:03}]\ntype = drive\nscope = drive\nservice_account_file = accounts/{sa}\n{option} = {gd_id}\n\n"
                       for i, sa in enumerate(files))

        async with aiofiles.open(sa_conf_file, 'w') as f:
            await f.write(text)
        return sa_conf_file

    async def __start_download(self, cmd: List[str], remote_type: str):
        self.proc = await asyncio.create_subprocess_exec(*cmd, stdout=PIPE, stderr=PIPE)
        await self.__progress()
        if self.is_cancelled:
            return

        stdout, stderr = self.proc.communicate()
        if stdout:
            logger.debug(f"Download stdout: {stdout.decode()}")
        if stderr:
            logger.debug(f"Download stderr: {stderr.decode()}")

        if self.is_cancelled:
            return

        if self.proc.returncode == 0:
            await self.listener.on_download_complete()
        elif self.proc.returncode != -9:
            error = stderr.decode().strip()
            if not error and remote_type == 'drive' and config_dict['USE_SERVICE_ACCOUNTS']:
                error = "Mostly your service accounts don't have access to this drive!"
            logger.error(error)

            if self.sa_number != 0 and remote_type == 'drive' and 'RATE_LIMIT_EXCEEDED' in error and config_dict['USE_SERVICE_ACCOUNTS']:
                if self.sa_count < self.sa_number:
                    remote = self.__switch_service_account()
                    cmd[6] = f"{remote}:{cmd[6].split(':', 1)[1]}"
                    if self.is_cancelled:
                        return
                    return await self.__start_download(cmd, remote_type)
                else:
                    logger.info(
                        f"Reached maximum number of service accounts switching, which is {self.sa_count}")

            await self.listener.on_download_error(error[:4000])

    async def download(self, remote: str, rc_path: str, config_path: str, path: str):
        self.is_download = True
        try:
            remote_opts = await self.__get_remote_options(config_path, remote)
        except Exception as err:
            await self.listener.on_download_error(str(err))
            return
        remote_type = remote_opts['type']

        if remote_type == 'drive' and config_dict['USE_SERVICE_ACCOUNTS'] and config_path == 'rclone.conf' \
                and await aiofiles.os.path.isdir('accounts') and not remote_opts.get('service_account_file'):
            config_path = await self.__create_rc_sa(remote, remote_opts)
            if config_path != 'rclone.conf':
                sa_files = await aiofiles.os.listdir('accounts')
                self.sa_number = len(sa_files)
                self.sa_index = randrange(self.sa_number)
                remote = f'sa{self.sa_index:03}'
                logger.info(f'Download with service account {remote}')

        rcflags = self.listener.rc_flags or config_dict['RCLONE_FLAGS']
        cmd = self.__get_updated_command(
            config_path, f'{remote}:{rc_path}', path, rcflags, 'copy')

        if remote_type == 'drive' and not config_dict['RCLONE_FLAGS'] and not self.listener.rc_flags:
            cmd.append('--drive-acknowledge-abuse')
        elif remote_type != 'drive':
            cmd.extend(('--retries-sleep', '3s'))

        await self.__start_download(cmd, remote_type)

    async def __get_gdrive_link(self, config_path: str, remote: str, rc_path: str, mime_type: str) -> Tuple[str, str]:
        if mime_type == 'Folder':
            epath = rc_path.strip('/').rsplit('/', 1)
            epath = f'{remote}:{epath[0]}' if len(
                epath) > 1 else f'{remote}:'
            destination = f'{remote}:{rc_path}'
        elif rc_path:
            epath = f"{remote}:{rc_path}/{self.name}"
            destination = f'{remote}:{rc_path}/{self.name}'
        else:
            epath = f"{remote}:{rc_path}{self.name}"
            destination = f'{remote}:{rc_path}{self.name}'

        cmd = ['rclone', 'lsjson', '--fast-list', '--no-mimetype',
               '--no-modtime', '--config', config_path, epath]
        res, err, code = await cmd_exec(cmd)

        if code == 0:
            result = json.loads(res)
            fid = next((r['ID']
                       for r in result if r['Path'] == self.name), 'err')
            link = f'https://drive.google.com/drive/folders/{fid}' if mime_type == 'Folder' else f'https://drive.google.com/uc?id={fid}&export=download'
        elif code != -9:
            logger.error(
                f'while getting drive link. Path: {destination}. Stderr: {err}')
            link = ''
        return link, destination

    async def __start_upload(self, cmd: List[str], remote_type: str) -> bool:

