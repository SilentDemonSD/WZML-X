import asyncio
import logging
from configparser import ConfigParser
from pathlib import Path

import aiofiles
from bot import config_dict as bot_config_dict
from rclone.webui import RcloneWebUI

# Initialize logger
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

async def main():
    # Load config
    config = ConfigParser()
    config_path = Path('config.ini')
    async with aiofiles.open(config_path, 'r') as f:
        config.read_file(await f.readlines())

    # Get rclone config
    rclone_config = config['RCLONE']

    # Initialize RcloneWebUI with bot_loop
    rclone_webui = RcloneWebUI(bot_loop, **rclone_config)

    # Run RcloneWebUI
    await rclone_webui.run()

if __name__ == '__main__':
    bot_loop = asyncio.get_event_loop()
    bot_loop.run_until_complete(main())
