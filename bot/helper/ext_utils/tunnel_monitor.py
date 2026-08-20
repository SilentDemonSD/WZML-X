from asyncio import sleep
from os import environ

from aiofiles import open as aiopen
from aiofiles.os import path as aiopath

from ... import LOGGER, bot_loop
from ...core.config_manager import Config


TUNNEL_URL_FILE = environ.get("TUNNEL_URL_FILE", "/data/tunnel_url.txt")


async def _read_tunnel_url():
    try:
        if not await aiopath.isfile(TUNNEL_URL_FILE):
            return None
        async with aiopen(TUNNEL_URL_FILE, "r") as f:
            url = (await f.read()).strip()
        return url or None
    except Exception as e:
        LOGGER.warning(f"tunnel_monitor: read failed: {e}")
        return None


async def _tunnel_monitor_loop():
    LOGGER.info("tunnel_monitor: started")
    while True:
        try:
            url = await _read_tunnel_url()
            if url and Config.BASE_URL != url:
                Config.BASE_URL = url
                LOGGER.info(f"tunnel_monitor: BASE_URL = {url}")
        except Exception as e:
            LOGGER.error(f"tunnel_monitor: {e}")
        await sleep(5)


async def apply_tunnel_url_once():
    url = await _read_tunnel_url()
    if url:
        Config.BASE_URL = url
        LOGGER.info(f"tunnel_monitor: initial BASE_URL = {url}")
    return url


def start_tunnel_monitor():
    bot_loop.create_task(_tunnel_monitor_loop())
    LOGGER.info("tunnel_monitor: background monitor started")
