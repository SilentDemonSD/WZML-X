import asyncio
import configparser
from typing import List, Optional

import aiofiles
from aiofiles.os import path as aiopath

config_dict = {}
bot_loop = asyncio.get_event_loop()

RcloneServe: List[Optional[asyncio.subprocess.Process]] = []

async def rclone_serve_booter():
    """
    Starts the rclone serve process if the required configuration is present.
    """
    if not config_dict.get('RCLONE_SERVE_URL') or not await aiopath.exists('rclone.conf'):
        if RcloneServe:
            try:
                RcloneServe[0].kill()
                RcloneServe.clear()
            except Exception as e:
                print(f"Error while killing rclone serve process: {e}")
        return

    config = configparser.ConfigParser()
    async with aiofiles.open('rclone.conf', 'r') as f:
        contents = await f.read()
        config.read_string(contents)

    if not config.has_section('combine'):
        upstreams = ' '.join(
            f'{remote}={remote}:' for remote in config.sections())
        config.add_section('combine')
        config.set('combine', 'type', 'combine')
        config.set('combine', 'upstreams', upstreams)

        with open('rclone.conf', 'w') as f:
            config.write(f, space_around_delimiters=False)

    if RcloneServe:
        try:
            RcloneServe[0].kill()
            RcloneServe.clear()
        except Exception as e:
            print(f"Error while killing rclone serve process: {e}")

    if shutil.which('rclone') is None:
        print("rclone command not found, please install rclone and try again.")
        return

    cmd = ["rclone", "serve", "http", "--config", "rclone.conf", "--no-modtime",
           "combine:", "--addr", f":{config_dict.get('RCLONE_SERVE_PORT')}",
           "--vfs-cache-mode", "full", "--vfs-cache-max-age", "1m0s",
           "--buffer-size", "64M"]

    user = config_dict.get('RCLONE_SERVE_USER')
    pswd = config_dict.get('RCLONE_SERVE_PASS')

    if user and pswd:
        cmd.extend(("--user", user, "--pass", pswd))

    rcs = await asyncio.create_subprocess_exec(*cmd)
    RcloneServe.append(rcs)

bot_loop.run_until_complete(rclone_serve_booter())
