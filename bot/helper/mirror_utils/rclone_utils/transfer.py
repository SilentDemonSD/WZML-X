import asyncio
import os
import re
import json
from typing import List, Tuple, Dict, Union, Any, Callable, Coroutine

# Importing required modules using asyncio
from asyncio import create_subprocess_exec, gather, PIPE

# Importing required modules from bot
from bot import config_dict
from bot.helper.ext_utils.bot_utils import cmd_exec, async_to_sync
from bot.helper.ext_utils.fs_utils import get_mime_type, count_files_and_folders

# Importing logging module
import logging

# Creating logger object
LOGGER = logging.getLogger(__name__)

# Importing required modules using aiofiles
import aiofiles
from aiofiles import open as aiopen
from aiofiles.os import path as aiopath, mkdir, listdir

async def run_command(command: List[str]) -> Tuple[int, str]:
    """
    This function asynchronously runs a command using asyncio.create_subprocess_exec and returns the exit code and output.
    :param command: List of command arguments
    :return: Tuple of exit code and output
    """
    process = await asyncio.create_subprocess_exec(
        *command, stdout=PIPE, stderr=PIPE)

