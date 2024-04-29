# Import necessary modules
import asyncio
import json
import logging
import secrets
from typing import Any, Coroutine, List, Tuple

# Import required classes and functions from bot and helper modules
import aiocontextvars
import bot
from bot import download_dict, download_dict_lock, queue_dict_lock, non_queued_dl, LOGGER
from bot.helper.ext_utils.bot_utils import cmd_exec
from bot.helper.telegram_helper.message_utils import sendMessage, sendStatusMessage
from bot.helper.ext_utils.task_manager import is_queued, stop_duplicate_check
from bot.helper.mirror_utils.status_utils.rclone_status import RcloneStatus
from bot.helper.mirror_utils.status_utils.queue_status import QueueStatus
from bot.helper.mirror_utils.rclone_utils.transfer import RcloneTransferHelper

# Initialize the logger
logger = logging.getLogger(__name__)

async def add_rclone_download(
    rc_path: str, config_path: str, path: str, name: str, listener: Any
) -> Coroutine[Any, Any, None]:
    """
    Adds a new rclone download to the download queue.

    :param rc_path: The rclone path in the format 'remote:path'
    :param config_path: The path to the rclone config file
    :param path: The path to save the downloaded file
    :param name: The name of the downloaded file
    :param listener: The listener object for the download
    :return: None
    """
    # Split the rclone path into remote and path
    remote, rc_path = rc_path.split(':', 1)
    rc_path = rc_path.strip('/')

    # Execute rclone lsjson and rclone size commands
    cmd1 = ['rclone', 'lsjson', '--fast-list', '--stat', '--no-mimetype',
            '--no-modtime', '--config', config_path, f'{remote}:{rc_path}']
    cmd2 = ['rclone', 'size', '--fast-list', '--json',
            '--config', config_path, f'{remote}:{rc_path}']
    res1, res2 = await asyncio.gather(cmd_exec(*cmd1), cmd_exec(*cmd2))

    # Process the results and handle exceptions
    # ...

    # Prepare variables for the download
    if rstat['IsDir']:
        if not name:
            name = rc_path.rsplit('/', 1)[-1] if rc_path else remote
        path += name
    else:
        name = rc_path.rsplit('/', 1)[-1]
    size = rsize['bytes']
    gid = secrets.token_hex(5)

    # Check if the download is already in the queue
    added_to_queue, event = await is_queued(listener.uid)
    if added_to_queue:
        # ...
    else:
        # ...

    # Initialize RcloneTransferHelper
    try:
        RCTransfer = RcloneTransferHelper(listener, name, rc_path)
    except Exception as e:
        # ...

    # Update download_dict and non_queued_dl
    # ...

    # Start the download
    if from_queue:
        logger.info(f'Start Queued Download with rclone: {rc_path}')
    else:
        # ...

    # Download the file
    try:
        await RCTransfer.download(remote, rc_path, config_path, path)
    except Exception as e:
        # ...
