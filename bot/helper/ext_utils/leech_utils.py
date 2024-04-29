import hashlib
import os
import re
import shlex
from asyncio import create_subprocess_exec
from asyncio.subprocess import PIPE
from pathlib import Path
from typing import Any, Callable, List, Optional, Tuple

import aiofiles
from aiofiles.os import remove as aioremove, path as aiopath, mkdir
from bot import LOGGER, MAX_SPLIT_SIZE, config_dict, user_data
from bot.modules.mediainfo import parseinfo
from bot.helper.ext_utils.bot_utils import cmd_exec, sync_to_async, get_readable_file_size, get_readable_time
from bot.helper.ext_utils.fs_utils import ARCH_EXT, get_mime_type
from bot.helper.ext_utils.telegraph_helper import telegraph

async def is_multi_streams(path: str) -> bool:
    """Check if the media file has multiple video or audio streams."""
    try:

