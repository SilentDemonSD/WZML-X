import asyncio
import os
import re
import json
from typing import List, Tuple, Dict, Union, Any

from asyncio import create_subprocess_exec, gather
from asyncio.subprocess import PIPE
from configparser import ConfigParser
from aiofiles import open as aiopen
from aiofiles.os import path as aiopath, mkdir, listdir
from bot import config_dict, GLOBAL_EXTENSION_FILTER
from bot.helper.ext_utils.bot_utils import cmd_exec, sync_to_async
from bot.helper.ext_utils.fs_utils import get_mime_type, count_files_and_folders

LOGGER = getLogger(__name__)


class RcloneTransferHelper:
    def __init__(self, listener=None, name=''):
        self.__listener = listener
        self.__proc = None
        self.__transferred_size = '0 B'
        self.__eta = '-'
        self.__percentage = '0%'
        self.__speed = '0 B/s'
        self.__size = '0 B'
        self.__is_cancelled = False
        self.__is_download = False
        self.__is_upload = False
        self.__sa_count = 1
        self.__sa_index = 0
        self.__sa_number = 0
        self.name = name

    @property
    def transferred_size(self) -> str:
        return self.__transferred_size

    @property
    def percentage(self) -> str:
        return self.__percentage

    @property
    def speed(self) -> str:
        return self.__speed

    @property
    def eta(self) -> str:
        return self.__eta

    @property
    def size(self) -> str:
        return self.__size

    async def __progress(self) -> None:
        while not (self.__proc is None or self.__is_cancelled):
            try:
                data = (await self.__proc.stdout.readline()).decode()
            except:
                continue
            if not data:
                break
            if data := re.findall(r'Transferred:\s+([\d.]+\s*\w+)\s+/\s+([\d.]+\s*\w+),\s+([\d.]+%)\s*,\s+([\d.]+\s*\w+/s),\s+ETA\s+([\dwdhms]+)', data):
                self.__transferred_size, self.__size, self.__percentage, self.__speed, self.__eta = data[0]

    def __switchServiceAccount(self) -> str:
        if self.__sa_index == self.__sa_number - 1:
            self.__sa_index = 0
        else:
            self.__sa_index += 1
        self.__sa_count += 1
        remote = f'sa{self.__sa_index:03}'
        LOGGER.info(f"Switching to {remote} remote")
        return remote

    async def __create_rc_sa(self, remote: str, remote_opts: Dict[str, str]) -> str:
        sa_conf_dir = 'rclone_sa'
        sa_conf_file = f'{sa_conf_dir}/{remote}.conf'
        if not await aiopath.isdir(sa_conf_dir):
            await mkdir(sa_conf_dir)
        elif await aiopath.isfile(sa_conf_file):
            return sa_conf_file

        if gd_id := remote_opts.get('team_drive'):
            option = 'team_drive'
        elif gd_id := remote_opts.get('root_folder_id'):
            option = 'root_folder_id'
        else:
            return 'rclone.conf'

        files = await listdir('accounts')
        text = ''.join(f"[sa{i:03}]\ntype = drive\nscope = drive\nservice_account_file = accounts/{sa}\n{option} = {gd_id}\n\n"
                       for i, sa in enumerate(files))

        async with aiopen(sa_conf_file, 'w') as f:
            await f.write(text)
        return sa_conf_file

    async def __start_download(self, cmd: List[str], remote_type: str) -> None:
        self.__proc = await create_subprocess_exec(*cmd, stdout=PIPE, stderr=PIPE)
        _, return_code = await gather(self.__progress(), self.__proc.wait())

        if self.__is_cancelled:
            return

        if return_code == 0:
            await self.__listener.onDownloadComplete()
        elif return_code != -9:
            error = (await self.__proc.stderr.read()).decode().strip()
            if not error and remote_type == 'drive' and config_dict['USE_SERVICE_ACCOUNTS']:
                error = "Mostly your service accounts don't have access to this drive!"
            LOGGER.error(error)

            if self.__sa_number != 0 and remote_type == 'drive' and 'RATE_LIMIT_EXCEEDED' in error and config_dict['USE_SERVICE_ACCOUNTS']:
                if self.__sa_count < self.__sa_number:
                    remote = self.__switchServiceAccount()
                    cmd[6] = f"{remote}:{cmd[6].split(':', 1)[1]}"
                    if self.__is_cancelled:
                        return
                    await self.__start_download(cmd, remote_type)
                else:
                    LOGGER.info(
                        f"Reached maximum number of service accounts switching, which is {self.__sa_count}")

            await self.__listener.onDownloadError(error[:4000])

    async def download(self, remote: str, rc_path: str, config_path: str, path: str) -> None:
        self.__is_download = True
        try:
            remote_opts = await self.__get_remote_options(config_path, remote)
        except Exception as err:
            await self.__listener.onDownloadError(str(err))
            return
        remote_type = remote_opts['type']

        if remote_type == 'drive' and config_dict['USE_SERVICE_ACCOUNTS'] and os.path.isdir('accounts') and not remote_opts.get('service_account_file'):
            config_path = await self.__create_rc_sa(remote, remote_opts)
            if config_path != 'rclone.conf':
                sa_files = await listdir('accounts')
                self.__sa_number = len(sa_files)
                self.__sa_index = os.urandom(1).hex()[-3:]
                remote = f'sa{self.__sa_index:03}'
                LOGGER.info(f'Download with service account {remote}')

        rcflags = self.__listener.rcFlags or config_dict['RCLONE_FLAGS']
        cmd = self.__getUpdatedCommand(
            config_path, f'{remote}:{rc_path}', path, rcflags, 'copy')

        if remote_type == 'drive' and not config_dict['RCLONE_FLAGS'] and not self.__listener.rcFlags:
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
            LOGGER.error(
                f'while getting drive link. Path: {destination}. Stderr: {err}')
            link = ''
        return link, destination

    async def __start_upload(self, cmd: List[str], remote_type: str) -> bool:
        self.__proc = await create_subprocess_exec(*cmd, stdout=PIPE, stderr=PIPE)
        _, return_code = await gather(self.__progress(), self.__proc.wait())

        if self.__is_cancelled:
            return False

        if return_code == -9:
            return False
        elif return_code != 0:
            error = (await self.__proc.stderr.read()).decode().strip()
            if not error and remote_type == 'drive' and config_dict['USE_SERVICE_ACCOUNTS']:
                error = "Mostly your service accounts don't have access to this drive!"
            LOGGER.error(error)
            if self.__sa_number != 0 and remote_type == 'drive' and 'RATE_LIMIT_EXCEEDED' in error and config_dict['USE_SERVICE_ACCOUNTS']:
                if self.__sa_count < self.__sa_number:
                    remote = self.__switchServiceAccount()
                    cmd[7] = f"{remote}:{cmd[7].split(':', 1)[1]}"
                    return False if self.__is_cancelled else await self.__start_upload(cmd, remote_type)
                else:
                    LOGGER.info(
                        f"Reached maximum number of service accounts switching, which is {self.__sa_count}")
            await self.__listener.onUploadError(error[:4000])
            return False
        else:
            return True

    async def upload(self, path: str, size: int) -> None:
        self.__is_upload = True
        rc_path = self.__listener.upPath.strip('/')
        if rc_path.startswith('mrcc:'):
            rc_path = rc_path.split('mrcc:', 1)[1]
            oconfig_path = f'rclone/{self.__listener.message.from_user.id}.conf'
        else:
            oconfig_path = 'rclone.conf'

        oremote, rc_path = rc_path.split(':', 1)

        if os.path.isdir(path):
            mime_type = 'Folder'
            folders, files = await count_files_and_folders(path)
            rc_path += f"/{self.name}" if rc_path else self.name
        else:
            if path.lower().endswith(tuple(GLOBAL_EXTENSION_FILTER)):
                await self.__listener.onUploadError('This file extension is excluded by extension filter!')
                return
            mime_type = await sync_to_async(get_mime_type, path)
            folders = 0
            files = 1

        try:
            remote_opts = await self.__get_remote_options(oconfig_path, oremote)
        except Exception as err:
            await self.__listener.onUploadError(str(err))
            return
        remote_type = remote_opts['type']

        fremote = oremote
        fconfig_path = oconfig_path
        if remote_type == 'drive' and config_dict['USE_SERVICE_ACCOUNTS'] and fconfig_path == 'rclone.conf' \
                and os.path.isdir('accounts') and not remote_opts.get('service_account_file'):
            fconfig_path = await self.__create_rc_sa(oremote, remote_opts)
            if fconfig_path != 'rclone.conf':
                sa_files = await listdir('accounts')
                self.__sa_number = len(sa_files)
                self.__sa_index = os.urandom(1).hex()[-3:]
                fremote = f'sa{self.__sa_index:03}'
                LOGGER.info(f'Upload with service account {fremote}')

        rcflags = self.__listener.rcFlags or config_dict['RCLONE_FLAGS']
        method = 'move' if not self.__listener.seed or self.__listener.newDir else 'copy'
        cmd = self.__getUpdatedCommand(
            fconfig_path, path, f'{fremote}:{rc_path}', rcflags, method)
        if remote_type == 'drive' and not config_dict['RCLONE_FLAGS'] and not self.__listener.rcFlags:
            cmd.extend(('--drive-chunk-size', '64M',
                       '--drive-upload-cutoff', '32M'))
        elif remote_type != 'drive':
            cmd.extend(('--retries-sleep', '3s'))

        result = await self.__start_upload(cmd, remote_type)
        if not result:
            return

        if remote_type == 'drive':
            link, destination = await self.__get_gdrive_link(oconfig_path, oremote, rc_path, mime_type)
        else:
            if mime_type == 'Folder':
                destination = f"{oremote}:{rc_path}"
            elif rc_path:
                destination = f"{oremote}:{rc_path}/{self.name}"
            else:
                destination = f"{oremote}:{self.name}"

            cmd = ['rclone', 'link', '--config', oconfig_path, destination]
            res, err, code = await cmd_exec(cmd)

            if code == 0:
                link = res
            elif code != -9:
                LOGGER.error(
                    f'while getting link. Path: {destination} | Stderr: {err}')
                link = ''
        if self.__is_cancelled:
            return
        LOGGER.info(f'Upload Done. Path: {destination}')
        await self.__listener.onUploadComplete(link, size, files, folders, mime_type, self.name, destination)

    def __getUpdatedCommand(self, config_path: str, source: str, destination: str, rcflags: str, method: str) -> List[str]:
        ext = '*.{' + ','.join(GLOBAL_EXTENSION_FILTER) + '}'
        cmd = ['rclone', method, '--fast-list', '--config', config_path, '-P', source, destination,
               '--exclude', ext, '--ignore-case', '--low-level-retries', '1', '-M', '--log-file',
               'rlog.txt', '--log-level', 'DEBUG']
        if rcflags:
            rcflags = rcflags.split('|')
            for flag in rcflags:
                if ":" in flag:
                    key, value = flag.split(':', 1)
                    cmd.extend([key, value])
                else:
                    cmd.append(flag)
        return cmd

    async def __get_remote_options(self, config_path: str, remote: str) -> Dict[str, Union[str, int]]:
        config = ConfigParser()
        try:
            async with aiopen(config_path, 'r') as f:
                contents = await f.read()
                config.read_string(contents)
        except Exception as e:
            LOGGER.error(f"Error reading config file: {e}")
            return {}

        options = config.options(remote)
        return {opt: config.get(remote, opt) for opt in options}

    async def cancel_download(self) -> None:
        self.__is_cancelled = True
        if self.__proc is not None:
            try:
                self.__proc.kill()
            except:
                pass
        if self.__is_download:
            LOGGER.info(f"Cancelling Download: {self.name}")
            await self.__listener.onDownloadError('Download stopped by user!')
        elif self.__is_upload:
            LOGGER.info(f"Cancelling Upload: {self.name}")
            await self.__listener.onUploadError('your upload has been stopped!')
        else:
            LOGGER.info(f"Cancelling Clone: {self.name}")
            await self.__listener.onUploadError('your clone has been stopped!')
