import asyncio
import logging
from configparser import ConfigParser
from pathlib import Path

# Import the necessary modules
# asyncio is used for asynchronous programming
# logging is used for logging messages
# ConfigParser is used to read configuration files
# Path is used to handle file paths

import aiofiles
from bot import config_dict as bot_config_dict
from rclone.webui import RcloneWebUI

# Initialize the logger
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
# Configure the logger to log messages with a timestamp, log level, and message
# The log level is set to INFO, which means that all messages with a log level of INFO or higher will be logged

async def main():
    # Define the main function, which is an asynchronous function

    # Load config
    config = ConfigParser()
    config_path = Path('config.ini')
    async with aiofiles.open(config_path, 'r') as f:
        # Open the config file asynchronously in read mode
        # Use aiofiles to handle the file I/O asynchronously
        config.read_file(await f.readlines())
        # Read the contents of the file and populate the config object

    # Get rclone config
    rclone_config = config['RCLONE']
    # Get the rclone configuration from the config object

    # Initialize RcloneWebUI with bot_loop
    rclone_webui = RcloneWebUI(bot_loop, **rclone_config)
    # Initialize the RcloneWebUI object with the event loop and rclone configuration

    # Run RcloneWebUI
    await rclone_webui.run()
    # Run the RcloneWebUI object asynchronously

if __name__ == '__main__':
    # This block is executed when the script is run directly

    bot_loop = asyncio.get_event_loop()
    # Get the default event loop for asynchronous programming

    bot_loop.run_until_complete(main())
    # Run the main function asynchronously until it completes
