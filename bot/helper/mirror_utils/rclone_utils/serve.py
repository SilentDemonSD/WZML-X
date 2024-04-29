from asyncio import create_subprocess_exec, TimeoutError
from aiofiles.os import path as aiopath
from aiofiles import open as aiopen
from configparser import ConfigParser

from bot import config_dict, bot_loop

RcloneServe: list[asyncio.subprocess.Process] = []

async def rclone_serve_booter() -> None:
    """
    Starts or stops the rclone serve process based on the configuration.
    """
    if not config_dict['RCLONE_SERVE_URL'] or not await aiopath.exists('rclone.conf'):
        if RcloneServe:
            for proc in RcloneServe:
                try:
                    proc.kill()
                except ProcessLookupError:
                    pass
            RcloneServe.clear()
        return
    config = ConfigParser()
    async with aiopen('rclone.conf', 'r') as f:
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
        for proc in RcloneServe:
            try:
                proc.kill()
            except ProcessLookupError:
                pass
        RcloneServe.clear()
    if not await aiopath.exists('/usr/bin/rclone'):
        raise FileNotFoundError('rclone not found in /usr/bin/')
    if not config_dict['RCLONE_SERVE_PORT'].isdigit() or int(config_dict['RCLONE_SERVE_PORT']) <= 0 or int(config_dict['RCLONE_SERVE_PORT']) > 65535:
        raise ValueError('Invalid RCLONE_SERVE_PORT value')
    cmd = ["rclone", "serve", "http", "--config", "rclone.conf", "--no-modtime",
           "combine:", "--addr", f":{config_dict['RCLONE_SERVE_PORT']}",
           "--vfs-cache-mode", "full", "--vfs-cache-max-age", "1m0s",
           "--buffer-size", "64M"]
    if (user := config_dict['RCLONE_SERVE_USER']) and (pswd := config_dict['RCLONE_SERVE_PASS']):
        cmd.extend(("--user", user, "--pass", pswd))
    try:
        rcs = await create_subprocess_exec(*cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE, limit=1024*1024)
    except TimeoutError:
        raise TimeoutError('Subprocess creation timed out')
    RcloneServe.append(rcs)

bot_loop.run_until_complete(rclone_serve_booter())
