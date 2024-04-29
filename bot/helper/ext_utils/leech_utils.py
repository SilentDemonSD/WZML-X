import asyncio
import os
import shlex
from contextlib import suppress
from pathlib import Path
from typing import Tuple

import telegraph
from langcodes import Language

import bot
from bot.modules.mediainfo import parseinfo
from bot.helper.ext_utils.bot_utils import cmd_exec, sync_to_async, get_readable_file_size, get_readable_time
from bot.helper.ext_utils.fs_utils import ARCH_EXT, get_mime_type
from bot.helper.ext_utils.telegraph_helper import telegraph

async def is_multi_streams(path: str) -> bool:
    """Check if the file has multiple audio or video streams."""
    try:
        result = await cmd_exec(
            ["ffprobe", "-hide_banner", "-loglevel", "error", "-print_format", "json", "-show_streams", path]
        )
    except Exception as e:
        bot.LOGGER.error(f"Get Video Streams: {e}. Mostly File not found!")
        return False
    if res := result[1]:
        bot.LOGGER.warning(f"Get Video Streams: {res}")
    fields = eval(result[0]).get("streams")
    if fields is None:
        bot.LOGGER.error(f"get_video_streams: {result}")
        return False
    videos = 0
    audios = 0
    for stream in fields:
        if stream.get("codec_type") == "video":
            videos += 1
        elif stream.get("codec_type") == "audio":
            audios += 1
    return videos > 1 or audios > 1
