import asyncio
import os
import shlex
from contextlib import suppress
from pathlib import Path
from typing import Tuple

import telegraph
from langcodes import Language

from bot import LOGGER, MAX_SPLIT_SIZE, config_dict, user_data
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
        LOGGER.error(f"Get Video Streams: {e}. Mostly File not found!")
        return False
    if res := result[1]:
        LOGGER.warning(f"Get Video Streams: {res}")
    fields = eval(result[0]).get("streams")
    if fields is None:
        LOGGER.error(f"get_video_streams: {result}")
        return False
    videos = 0
    audios = 0
    for stream in fields:
        if stream.get("codec_type") == "video":
            videos += 1
        elif stream.get("codec_type") == "audio":
            audios += 1
    return videos > 1 or audios > 1

async def get_media_info(path: str, metadata: bool = False) -> Tuple[int, str, str]:
    """Get media information."""
    try:
        result = await cmd_exec(
            ["ffprobe", "-hide_banner", "-loglevel", "error", "-print_format", "json", "-show_format", "-show_streams", path]
        )
    except Exception as e:
        LOGGER.error(f"Media Info: {e}. Mostly File not found!")
        return (0, "", "") if metadata else (0, None, None)
    if res := result[1]:
        LOGGER.warning(f"Media Info FF: {res}")
    ffresult = eval(result[0])
    fields = ffresult.get("format")
    if fields is None:
        LOGGER.error(f"Media Info Sections: {result}")
        return (0, "", "") if metadata else (0, None, None)
    duration = round(float(fields.get("duration", 0)), 2)
    size = os.path.getsize(path)
    mime_type = get_mime_type(path)
    file_name = os.path.basename(path)
    file_size = get_readable_file_size(size)
    file_extension = os.path.splitext(path)[-1].lower()[1:]
    if not metadata:
        return size, file_name, mime_type
    return size, file_name, mime_type, duration, file_size, file_extension

async def upload_to_telegraph(file_path: str) -> str:
    """Upload file to telegraph."""
    try:
        with open(file_path, "rb") as f:
            response = await telegraph.create_page(
                [{"title": "File", "type": "uploaded_file", "src": f.read()}],
                Lang(Language.ANY_LANGUAGE),
            )
    except Exception as e:
        LOGGER.error(f"Error uploading file to telegraph: {e}")
        return ""
    return response["url"]

async def process_file(file_path: str, metadata: bool = False) -> Tuple[int, str, str, int, str, str]:
    """Process file and get media information."""
    size, file_name, mime_type = await asyncio.get_running_loop().run_in_executor(None, get_media_info, file_path, metadata)
    if mime_type.startswith("video/") or mime_type.startswith("audio/"):
        if await is_multi_streams(file_path):
            mime_type += " [Multiple Streams]"
    if metadata:
        url = await upload_to_telegraph(file_path)
        return size, file_name, mime_type, url
    return size, file_name, mime_type
