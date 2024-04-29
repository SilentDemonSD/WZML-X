from hashlib import md5
from time import strftime, gmtime, time
from re import sub as re_sub, search as re_search
from shlex import split as ssplit
from natsort import natsorted
from os import path as ospath, remove as aioremove, mkdir, makedirs, listdir
from aioshutil import rmtree as aiormtree
from contextlib import suppress
from asyncio import create_subprocess_exec, create_task, gather, Semaphore
from asyncio.subprocess import PIPE
from telegraph import upload_file
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
        if res := result[1]:
            LOGGER.warning(f"Get Video Streams: {res}")
    except Exception as e:
        LOGGER.error(f"Get Video Streams: {e}. Mostly File not found!")
        return False
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


async def get_media_info(path: str, metadata: bool = False) -> tuple[int, str, str]:
    """Get media information."""
    try:
        result = await cmd_exec(
            ["ffprobe", "-hide_banner", "-loglevel", "error", "-print_format", "json", "-show_format", "-show_streams", path]
        )
        if res := result[1]:
            LOGGER.warning(f"Media Info FF: {res}")
    except Exception as e:
        LOGGER.error(f"Media Info: {e}. Mostly File not found!")
        return (0, "", "") if metadata else (0, None, None)
    ffresult = eval(result[0])
    fields = ffresult.get("format")
    if fields is None:
        LOGGER.error(f"Media Info Sections: {result}")
        return (0, "", "") if metadata else (0, None, None)
    duration = round(float(fields.get("duration", 
