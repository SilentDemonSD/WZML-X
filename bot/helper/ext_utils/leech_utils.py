import asyncio
import json
import os
import shlex
from contextlib import suppress
from pathlib import Path
from typing import List, Tuple

import aiofiles
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
        # Use asyncio.create_subprocess_exec instead of cmd_exec
        process = await asyncio.create_subprocess_exec(
            "ffprobe", "-hide_banner", "-loglevel", "error", "-print_format", "json", "-show_streams", str(path),
            stdout="pipe", stderr="pipe"
        )
        stdout, stderr = await process.communicate()
    except Exception as e:
        bot.LOGGER.error(f"Get Video Streams: {e}. Mostly File not found!")
        return False

    if stderr:
        bot.LOGGER.warning(f"Get Video Streams: {stderr.decode()}")

    try:
        result = json.loads(stdout.decode())
    except json.JSONDecodeError:
        bot.LOGGER.warning(f"Get Video Streams: Invalid JSON data!")
        return False

    if not result.get("streams"):
        bot.LOGGER.warning(f"get_video_streams: Empty list of streams!")
        return False

    videos = 0
    audios = 0
    for stream in result["streams"]:
        if stream.get("codec_type") == "video":
            videos += 1
        elif stream.get("codec_type") == "audio":
            audios += 1

    return videos > 1 or audios > 1
