import asyncio
import logging
from configparser import ConfigParser
from pathlib import Path

import aiofiles
from bot import config_dict, bot_loop
from rclone.webui import RcloneWebUI

logger = logging.getLogger(__name__)

async def load_config():
    config_path = Path("config.ini")
    if not config_path.exists():
        logger.error("Config file not found")
        raise FileNotFoundError("Config file not found")

    config = ConfigParser()
    async with aiofiles.open(config_path, mode="r") as f:
        config.read_file(await f.readlines())

    return config

async def main():
    config = await load_config()
    rclone_webui = RcloneWebUI(config, bot_loop)
    await rclone_webui.start()

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    try:
        asyncio.run(main())
    except Exception as e:
        logger.error(f"Error occurred: {e}", exc_info=True)
