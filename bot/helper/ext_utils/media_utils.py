def load_ffmpeg_configs(self) -> Dict[str, List[str]]:
        """Load FFmpeg configurations from JSON or default configs - Enhanced version"""
        default_configs = {
            # Basic subtitle embedding
            "srt": [
                "-i", "INPUT_VIDEO", "-i", "INPUT_SUBTITLE", 
                "-map", "0:v", "-map", "0:a", "-map", "1", 
                "-c", "copy", "-c:s:0", "srt", 
                "-metadata:s:s:0", "language=sin", 
                "-metadata:s:s:0", "title=FLIXORA", 
                "-disposition:s:0", "default", "-disposition:s:0", "forced", 
                "OUTPUT_FILE"
            ],
            
            # Multiple subtitles
            "multi_srt": [
                "-i", "INPUT_VIDEO", "-i", "INPUT_SUBTITLE1", "-i", "INPUT_SUBTITLE2",
                "-map", "0:v", "-map", "0:a", "-map", "1", "-map", "2",
                "-c", "copy", "-c:s", "copy",
                "-metadata:s:s:0", "language=sin", "-metadata:s:s:0", "title=SINHALA",
                "-metadata:s:s:1", "language=eng", "-metadata:s:s:1", "title=ENGLISH",
                "-disposition:s:0", "default", "-disposition:s:1", "0",
                "OUTPUT_FILE"
            ],
            
            # Audio embedding
            "audio_embed": [
                "-i", "INPUT_VIDEO", "-i", "INPUT_AUDIO",
                "-map", "0", "-map", "1:a",
                "-c", "copy", "-c:a:1", "aac",
                "-metadata:s:a:1", "language=sin",
                "-metadata:s:a:1", "title=SINHALA",
                "OUTPUT_FILE"
            ],
            
            # Extract audio only
            "extract_audio": [
                "-i", "INPUT_VIDEO",
                "-vn", "-acodec", "copy",
                "OUTPUT_FILE"
            ],
            
            # Basic compression
            "compress": [
                "-i", "INPUT_VIDEO",
                "-c:v", "libx264", "-crf", "23", "-preset", "medium",
                "-c:a", "aac", "-b:a", "128k",
                "OUTPUT_FILE"
            ],
            
            # High quality compression
            "hq_compress": [
                "-i", "INPUT_VIDEO",
                "-c:v", "libx264", "-crf", "18", "-preset", "slower",
                "-c:a", "aac", "-b:a", "192k",
                "OUTPUT_FILE"
            ],
            
            # HEVC encoding
            "hevc": [
                "-i", "INPUT_VIDEO",
                "-c:v", "libx265", "-crf", "28", "-preset", "medium",
                "-c:a", "copy", "-c:s", "copy",
                "OUTPUT_FILE"
            ],
            
            # Convert to MP4
            "mp4": [
                "-i", "INPUT_VIDEO",
                "-c:v", "libx264", "-c:a", "aac",
                "-c:s", "mov_text", "-movflags", "faststart",
                "OUTPUT_FILE"
            ],
            
            # Convert any format to MKV
            "mkv": [
                "-i", "INPUT_VIDEO",
                "-c", "copy",
                "OUTPUT_FILE"
            ],
            
            # Anime optimization
            "anime": [
                "-i", "INPUT_VIDEO",
                "-c:v", "libx264", "-crf", "20", "-preset", "slower",
                "-tune", "animation", "-c:a", "aac", "-b:a", "160k",
                "OUTPUT_FILE"
            ],
            
            # 4K/HDR preserve
            "hdr": [
                "-i", "INPUT_VIDEO",
                "-c:v", "libx265", "-crf", "22", "-preset", "medium",
                "-x265-params", "hdr-opt=1:repeat-headers=1:colorprim=bt2020:transfer=smpte2084:colormatrix=bt2020nc",
                "-c:a", "copy", "-c:s", "copy",
                "OUTPUT_FILE"
            ],
            
            # Everything together
            "all": [
                "-i", "INPUT_VIDEO", "-i", "INPUT_SUBTITLE", "-i", "INPUT_AUDIO",
                "-map", "0:v", "-map", "0:a", "-map", "2:a", "-map", "1",
                "-c", "copy", "-c:a:1", "aac", "-c:s", "srt",
                "-metadata:s:a:0", "language=eng", "-metadata:s:a:0", "title=ORIGINAL",
                "-metadata:s:a:1", "language=sin", "-metadata:s:a:1", "title=SINHALA",
                "-metadata:s:s:0", "language=sin", "-metadata:s:s:0", "title=SINHALA",
                "-disposition:a:0", "default", "-disposition:a:1", "0",
                "-disposition:s:0", "default", "-disposition:s:0", "forced",
                "OUTPUT_FILE"
            ],
            
            # Format conversion configs
            "to_mp4": [
                "-i", "INPUT_VIDEO",
                "-c:v", "copy", "-c:a", "copy", "-c:s", "mov_text",
                "-movflags", "faststart",
                "OUTPUT_FILE"
            ],
            
            "to_mkv": [
                "-i", "INPUT_VIDEO",
                "-c", "copy",
                "OUTPUT_FILE"
            ],
            
            "to_avi": [
                "-i", "INPUT_VIDEO",
                "-c:v", "libx264", "-c:a", "mp3",
                "OUTPUT_FILE"
            ],
            
            # Resolution scaling
            "720p": [
                "-i", "INPUT_VIDEO",
                "-vf", "scale=1280:720", "-c:v", "libx264", "-crf", "23",
                "-c:a", "copy", "-c:s", "copy",
                "OUTPUT_FILE"
            ],
            
            "1080p": [
                "-i", "INPUT_VIDEO",
                "-vf", "scale=1920:1080", "-c:v", "libx264", "-crf", "21",
                "-c:a", "copy", "-c:s", "copy",
                "OUTPUT_FILE"
            ],
            
            # Audio extraction with different formats
            "extract_mp3": [
                "-i", "INPUT_VIDEO",
                "-vn", "-acodec", "libmp3lame", "-ab", "192k",
                "OUTPUT_FILE"
            ],
            
            "extract_flac": [
                "-i", "INPUT_VIDEO", 
                "-vn", "-acodec", "flac",
                "OUTPUT_FILE"
            ],
            
            # Subtitle extraction
            "extract_srt": [
                "-i", "INPUT_VIDEO",
                "-an", "-vn", "-c:s", "srt",
                "OUTPUT_FILE"
            ],
            
            # Fix corrupted files
            "fix": [
                "-i", "INPUT_VIDEO",
                "-c", "copy", "-avoid_negative_ts", "make_zero",
                "-fflags", "+genpts", "-map", "0",
                "OUTPUT_FILE"
            ],
            
            # Fast preview/sample
            "sample": [
                "-i", "INPUT_VIDEO",
                "-ss", "00:01:00", "-t", "00:02:00",
                "-c", "copy",
                "OUTPUT_FILE"
            ],
            
            # Remove metadata
            "clean": [
                "-i", "INPUT_VIDEO",
                "-c", "copy", "-map_metadata", "-1",
                "OUTPUT_FILE"
            ],
            
            # Normalize audio
            "normalize": [
                "-i", "INPUT_VIDEO",
                "-c:v", "copy", "-af", "loudnorm", "-c:a", "aac",
                "OUTPUT_FILE"
            ],
            
            # Deinterlace
            "deinterlace": [
                "-i", "INPUT_VIDEO",
                "-vf", "yadif", "-c:a", "copy",
                "OUTPUT_FILE"
            ],
            
            # Rotate video
            "rotate_90": [
                "-i", "INPUT_VIDEO",
                "-vf", "transpose=1", "-c:a", "copy",
                "OUTPUT_FILE"
            ],
            
            "rotate_180": [
                "-i", "INPUT_VIDEO", 
                "-vf", "transpose=2,transpose=2", "-c:a", "copy",
                "OUTPUT_FILE"
            ],
            
            "rotate_270": [
                "-i", "INPUT_VIDEO",
                "-vf", "transpose=2", "-c:a", "copy", 
                "OUTPUT_FILE"
            ]
        }
        
        # Try to load from external config file
        config_path = ospath.join(DOWNLOAD_DIR, "ffmpeg_configs.json")
        if ospath.exists(config_path):
            try:
                with open(config_path, 'r') as f:
                    custom_configs = json.load(f)
                    default_configs.update(custom_configs)
                    LOGGER.info(f"✅ Loaded custom FFmpeg configs from {config_path}")
            except Exception as e:
                LOGGER.error(f"❌ Error loading custom FFmpeg configs: {e}")
        
        return default_configsfrom contextlib import suppress
from PIL import Image
from hashlib import md5
from aiofiles.os import remove, path as aiopath, makedirs
import json
import os
import re
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from collections import defaultdict
from difflib import SequenceMatcher
from asyncio import (
    create_subprocess_exec,
    gather,
    wait_for,
    sleep,
)
from asyncio.subprocess import PIPE
from os import path as ospath
from re import search as re_search, escape
from time import time
from aioshutil import rmtree
from langcodes import Language

from ... import LOGGER, cpu_no, DOWNLOAD_DIR
from ...core.config_manager import BinConfig
from .bot_utils import cmd_exec, sync_to_async
from .files_utils import get_mime_type, is_archive, is_archive_split
from .status_utils import time_to_seconds


def get_md5_hash(up_path):
    md5_hash = md5()
    with open(up_path, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            md5_hash.update(byte_block)
        return md5_hash.hexdigest()


async def create_thumb(msg, _id=""):
    if not _id:
        _id = time()
        path = f"{DOWNLOAD_DIR}thumbnails"
    else:
        path = "thumbnails"
    await makedirs(path, exist_ok=True)
    photo_dir = await msg.download()
    output = ospath.join(path, f"{_id}.jpg")
    await sync_to_async(Image.open(photo_dir).convert("RGB").save, output, "JPEG")
    await remove(photo_dir)
    return output


async def get_media_info(path, extra_info=False):
    try:
        result = await cmd_exec(
            [
                "ffprobe",
                "-hide_banner",
                "-loglevel",
                "error",
                "-print_format",
                "json",
                "-show_format",
                "-show_streams",
                path,
            ]
        )
    except Exception as e:
        LOGGER.error(f"Get Media Info: {e}. Mostly File not found! - File: {path}")
        return (0, "", "", "") if extra_info else (0, None, None)
    if result[0] and result[2] == 0:
        ffresult = eval(result[0])
        fields = ffresult.get("format")
        if fields is None:
            LOGGER.error(f"get_media_info: {result}")
            return (0, "", "", "") if extra_info else (0, None, None)
        duration = round(float(fields.get("duration", 0)))
        if extra_info:
            lang, qual, stitles = "", "", ""
            if (streams := ffresult.get("streams")) and streams[0].get(
                "codec_type"
            ) == "video":
                qual = int(streams[0].get("height"))
                qual = f"{480 if qual <= 480 else 540 if qual <= 540 else 720 if qual <= 720 else 1080 if qual <= 1080 else 2160 if qual <= 2160 else 4320 if qual <= 4320 else 8640}p"
                for stream in streams:
                    if stream.get("codec_type") == "audio" and (
                        lc := stream.get("tags", {}).get("language")
                    ):
                        with suppress(Exception):
                            lc = Language.get(lc).display_name()
                        if lc not in lang:
                            lang += f"{lc}, "
                    if stream.get("codec_type") == "subtitle" and (
                        st := stream.get("tags", {}).get("language")
                    ):
                        with suppress(Exception):
                            st = Language.get(st).display_name()
                        if st not in stitles:
                            stitles += f"{st}, "
            return duration, qual, lang[:-2], stitles[:-2]
        tags = fields.get("tags", {})
        artist = tags.get("artist") or tags.get("ARTIST") or tags.get("Artist")
        title = tags.get("title") or tags.get("TITLE") or tags.get("Title")
        return duration, artist, title
    return (0, "", "", "") if extra_info else (0, None, None)


async def get_document_type(path):
    is_video, is_audio, is_image = False, False, False
    if (
        is_archive(path)
        or is_archive_split(path)
        or re_search(r".+(\.|_)(rar|7z|zip|bin)(\.0*\d+)?$", path)
    ):
        return is_video, is_audio, is_image
    mime_type = await sync_to_async(get_mime_type, path)
    if mime_type.startswith("image"):
        return False, False, True
    try:
        result = await cmd_exec(
            [
                "ffprobe",
                "-hide_banner",
                "-loglevel",
                "error",
                "-print_format",
                "json",
                "-show_streams",
                path,
            ]
        )
        if result[1] and mime_type.startswith("video"):
            is_video = True
    except Exception as e:
        LOGGER.error(f"Get Document Type: {e}. Mostly File not found! - File: {path}")
        if mime_type.startswith("audio"):
            return False, True, False
        if not mime_type.startswith("video") and not mime_type.endswith("octet-stream"):
            return is_video, is_audio, is_image
        if mime_type.startswith("video"):
            is_video = True
        return is_video, is_audio, is_image
    if result[0] and result[2] == 0:
        fields = eval(result[0]).get("streams")
        if fields is None:
            LOGGER.error(f"get_document_type: {result}")
            return is_video, is_audio, is_image
        is_video = False
        for stream in fields:
            if stream.get("codec_type") == "video":
                codec_name = stream.get("codec_name", "").lower()
                if codec_name not in {"mjpeg", "png", "bmp"}:
                    is_video = True
            elif stream.get("codec_type") == "audio":
                is_audio = True
    return is_video, is_audio, is_image


async def get_streams(file):
    """
    Gets media stream information using ffprobe.

    Args:
        file: Path to the media file.

    Returns:
        A list of stream objects (dictionaries) or None if an error occurs
        or no streams are found.
    """
    cmd = [
        "ffprobe",
        "-hide_banner",
        "-loglevel",
        "error",
        "-print_format",
        "json",
        "-show_streams",
        file,
    ]
    process = await create_subprocess_exec(*cmd, stdout=PIPE, stderr=PIPE)
    stdout, stderr = await process.communicate()

    if process.returncode != 0:
        LOGGER.error(f"Error getting stream info: {stderr.decode().strip()}")
        return None

    try:
        return json.loads(stdout)["streams"]
    except KeyError:
        LOGGER.error(
            f"No streams found in the ffprobe output: {stdout.decode().strip()}",
        )
        return None


async def take_ss(video_file, ss_nb) -> bool:
    duration = (await get_media_info(video_file))[0]
    if duration != 0:
        dirpath, name = video_file.rsplit("/", 1)
        name, _ = ospath.splitext(name)
        dirpath = f"{dirpath}/{name}_mltbss"
        await makedirs(dirpath, exist_ok=True)
        interval = duration // (ss_nb + 1)
        cap_time = interval
        cmds = []
        for i in range(ss_nb):
            output = f"{dirpath}/SS.{name}_{i:02}.png"
            cmd = [
                BinConfig.FFMPEG_NAME,
                "-hide_banner",
                "-loglevel",
                "error",
                "-ss",
                f"{cap_time}",
                "-i",
                video_file,
                "-q:v",
                "1",
                "-frames:v",
                "1",
                "-threads",
                f"{max(1, cpu_no // 2)}",
                output,
            ]
            cap_time += interval
            cmds.append(cmd_exec(cmd))
        try:
            resutls = await wait_for(gather(*cmds), timeout=60)
            if resutls[0][2] != 0:
                LOGGER.error(
                    f"Error while creating sreenshots from video. Path: {video_file}. stderr: {resutls[0][1]}"
                )
                await rmtree(dirpath, ignore_errors=True)
                return False
        except Exception:
            LOGGER.error(
                f"Error while creating sreenshots from video. Path: {video_file}. Error: Timeout some issues with ffmpeg with specific arch!"
            )
            await rmtree(dirpath, ignore_errors=True)
            return False
        return dirpath
    else:
        LOGGER.error("take_ss: Can't get the duration of video")
        return False


async def get_audio_thumbnail(audio_file):
    output_dir = f"{DOWNLOAD_DIR}thumbnails"
    await makedirs(output_dir, exist_ok=True)
    output = ospath.join(output_dir, f"{time()}.jpg")
    cmd = [
        BinConfig.FFMPEG_NAME,
        "-hide_banner",
        "-loglevel",
        "error",
        "-i",
        audio_file,
        "-an",
        "-vcodec",
        "copy",
        "-threads",
        f"{max(1, cpu_no // 2)}",
        output,
    ]
    try:
        _, err, code = await wait_for(cmd_exec(cmd), timeout=60)
        if code != 0 or not await aiopath.exists(output):
            LOGGER.error(
                f"Error while extracting thumbnail from audio. Name: {audio_file} stderr: {err}"
            )
            return None
    except Exception:
        LOGGER.error(
            f"Error while extracting thumbnail from audio. Name: {audio_file}. Error: Timeout some issues with ffmpeg with specific arch!"
        )
        return None
    return output


async def get_video_thumbnail(video_file, duration):
    output_dir = f"{DOWNLOAD_DIR}thumbnails"
    await makedirs(output_dir, exist_ok=True)
    output = ospath.join(output_dir, f"{time()}.jpg")
    if duration is None:
        duration = (await get_media_info(video_file))[0]
    if duration == 0:
        duration = 3
    duration = duration // 2
    cmd = [
        BinConfig.FFMPEG_NAME,
        "-hide_banner",
        "-loglevel",
        "error",
        "-ss",
        f"{duration}",
        "-i",
        video_file,
        "-vf",
        "scale=640:-1",
        "-q:v",
        "5",
        "-vframes",
        "1",
        "-threads",
        "1",
        output,
    ]
    try:
        _, err, code = await wait_for(cmd_exec(cmd), timeout=60)
        if code != 0 or not await aiopath.exists(output):
            LOGGER.error(
                f"Error while extracting thumbnail from video. Name: {video_file} stderr: {err}"
            )
            return None
    except Exception:
        LOGGER.error(
            f"Error while extracting thumbnail from video. Name: {video_file}. Error: Timeout some issues with ffmpeg with specific arch!"
        )
        return None
    return output


async def get_multiple_frames_thumbnail(video_file, layout, keep_screenshots):
    ss_nb = layout.split("x")
    ss_nb = int(ss_nb[0]) * int(ss_nb[1])
    dirpath = await take_ss(video_file, ss_nb)
    if not dirpath:
        return None
    output_dir = f"{DOWNLOAD_DIR}thumbnails"
    await makedirs(output_dir, exist_ok=True)
    output = ospath.join(output_dir, f"{time()}.jpg")
    cmd = [
        BinConfig.FFMPEG_NAME,
        "-hide_banner",
        "-loglevel",
        "error",
        "-pattern_type",
        "glob",
        "-i",
        f"{escape(dirpath)}/*.png",
        "-vf",
        f"tile={layout}, thumbnail",
        "-q:v",
        "1",
        "-frames:v",
        "1",
        "-f",
        "mjpeg",
        "-threads",
        f"{max(1, cpu_no // 2)}",
        output,
    ]
    try:
        _, err, code = await wait_for(cmd_exec(cmd), timeout=60)
        if code != 0 or not await aiopath.exists(output):
            LOGGER.error(
                f"Error while combining thumbnails for video. Name: {video_file} stderr: {err}"
            )
            return None
    except Exception:
        LOGGER.error(
            f"Error while combining thumbnails from video. Name: {video_file}. Error: Timeout some issues with ffmpeg with specific arch!"
        )
        return None
    finally:
        if not keep_screenshots:
            await rmtree(dirpath, ignore_errors=True)
    return output


class SmartMediaMatcher:
    """Smart file matching system for media processing"""
    
    def __init__(self):
        # Comprehensive video format support
        self.video_extensions = {
            # Common formats
            '.mkv', '.mp4', '.avi', '.mov', '.wmv', '.flv', '.webm', '.m4v',
            # MPEG formats
            '.mpg', '.mpeg', '.m2v', '.m4p', '.m4v',
            # Advanced formats
            '.ts', '.mts', '.m2ts', '.vob', '.ogv', '.3gp', '.3g2',
            # Professional formats
            '.mxf', '.r3d', '.f4v', '.asf', '.rm', '.rmvb', '.divx', '.xvid',
            # Streaming formats
            '.m3u8', '.f4m', '.ismv', '.dash',
            # Raw formats
            '.yuv', '.raw', '.dv',
            # Other formats
            '.swf', '.qt', '.nsv', '.amv', '.mtv', '.roq', '.svi', '.smv'
        }
        
        # Comprehensive subtitle format support  
        self.subtitle_extensions = {
            # Text-based subtitles
            '.srt', '.ass', '.ssa', '.vtt', '.sub', '.sbv', '.scc', '.stl',
            # Image-based subtitles
            '.idx', '.sup', '.pgs', '.usf',
            # Professional formats
            '.ttml', '.dfxp', '.xml', '.cap', '.scr', '.rt', '.smi', '.sami',
            # Other formats
            '.lrc', '.txt', '.json'
        }
        
        # Comprehensive audio format support
        self.audio_extensions = {
            # Lossy formats
            '.mp3', '.aac', '.ogg', '.opus', '.wma', '.m4a', '.3gp',
            # Lossless formats
            '.flac', '.wav', '.aiff', '.alac', '.ape', '.wv', '.tta',
            # Professional formats
            '.ac3', '.dts', '.eac3', '.truehd', '.mlp', '.dts-hd',
            # Other formats
            '.ra', '.au', '.snd', '.gsm', '.amr', '.awb', '.vox', '.caf',
            # Uncompressed
            '.pcm', '.raw'
        }
        
    def similarity(self, a: str, b: str) -> float:
        """Calculate similarity between two strings"""
        return SequenceMatcher(None, a.lower(), b.lower()).ratio()
    
    def clean_filename(self, filename: str) -> str:
        """Clean filename for better matching"""
        # Remove extension
        name = Path(filename).stem
        
        # Remove common patterns that might interfere with matching
        patterns_to_remove = [
            r'\[.*?\]',  # Remove content in square brackets
            r'\(.*?\)',  # Remove content in parentheses  
            r'\.(?:x264|x265|h264|h265|hevc|avc|xvid)',  # Remove codec info
            r'\.(?:1080p|720p|480p|2160p|4k|hd|fhd|uhd)',  # Remove resolution info
            r'\.(?:bluray|bdrip|webrip|hdtv|dvdrip|camrip|ts|tc)',  # Remove source info
            r'\.(?:ac3|dts|aac|mp3|flac|atmos|truehd)',  # Remove audio codec info
            r'-(?:yify|rarbg|etrg|sparks|blow|evolve|killers)',  # Remove team info
            r'\.(?:internal|repack|proper|real|extended|unrated)',  # Remove special editions
            r'\d{4}',  # Remove years in some cases (be careful with this)
        ]
        
        for pattern in patterns_to_remove:
            name = re.sub(pattern, '', name, flags=re.IGNORECASE)
        
        # Replace dots, underscores, and hyphens with spaces
        name = re.sub(r'[._-]', ' ', name)
        
        # Remove extra spaces
        name = ' '.join(name.split())
        
        return name.strip()
    
    def extract_season_episode(self, filename: str) -> Tuple[Optional[int], Optional[int]]:
        """Extract season and episode numbers from filename - Enhanced version"""
        patterns = [
            # Standard formats
            r'[Ss](\d{1,2})[Ee](\d{1,3})',  # S01E01, s1e1
            r'[Ss]eason[\s._-]*(\d{1,2})[\s._-]*[Ee]pisode[\s._-]*(\d{1,3})',  # Season 1 Episode 1
            r'(\d{1,2})x(\d{1,3})',  # 1x01, 01x01
            r'[Ss](\d{1,2})[\s._-]*[Ee](\d{1,3})',  # S01 E01
            
            # Alternative formats
            r'[Ss](\d{1,2})[\s._-]+(\d{1,3})',  # S01 01
            r'(\d{1,2})\.(\d{1,3})',  # 1.01
            r'[Ee]pisode[\s._-]*(\d{1,2})[\s._-]*(\d{1,3})',  # Episode 1 01
            
            # International formats
            r'[Tt](\d{1,2})[Ee](\d{1,3})',  # T01E01 (Turkish style)
            r'[Pp](\d{1,2})[Ee](\d{1,3})',  # P01E01 (Part style)
            
            # Special cases
            r'(\d{1,2})[^\d]*(\d{1,3})(?:\.(?:mkv|mp4|avi|mov))',  # 01 01.mkv
        ]
        
        for pattern in patterns:
            match = re.search(pattern, filename, re.IGNORECASE)
            if match:
                season, episode = int(match.group(1)), int(match.group(2))
                # Validate reasonable ranges
                if 1 <= season <= 50 and 1 <= episode <= 999:
                    return season, episode
        
        return None, None
    
    def extract_movie_year(self, filename: str) -> Optional[int]:
        """Extract movie year from filename"""
        patterns = [
            r'[\[\(]?(19|20)\d{2}[\]\)]?',  # (2023) or [2023] or 2023
            r'\.(?:19|20)\d{2}\.',  # .2023.
        ]
        
        for pattern in patterns:
            match = re.search(pattern, filename)
            if match:
                year = int(match.group(0).strip('()[].,'))
                current_year = 2024  # Update as needed
                if 1900 <= year <= current_year + 2:  # Allow future releases
                    return year
        
        return None
    
    def is_tv_show(self, filename: str) -> bool:
        """Determine if file is likely a TV show"""
        season, episode = self.extract_season_episode(filename)
        return season is not None and episode is not None
    
    def group_files_by_type(self, folder_path: str) -> Dict[str, List[str]]:
        """Group files by their type (video, subtitle, audio) - Enhanced version"""
        grouped = {
            'video': [],
            'subtitle': [],
            'audio': [],
            'unknown': []
        }
        
        try:
            for file in os.listdir(folder_path):
                file_path = os.path.join(folder_path, file)
                if os.path.isfile(file_path):
                    file_type = self.get_file_type(file)
                    grouped[file_type].append(file)
                    
        except Exception as e:
            LOGGER.error(f"Error grouping files: {e}")
        
        # Log findings
        for file_type, files in grouped.items():
            if files:
                LOGGER.info(f"Found {len(files)} {file_type} files")
                for file in files[:5]:  # Show first 5 files
                    LOGGER.info(f"  - {file}")
                if len(files) > 5:
                    LOGGER.info(f"  ... and {len(files) - 5} more")
        
        return grouped
    
    def find_best_matches(self, video_file: str, candidates: List[str], threshold: float = 0.5) -> List[str]:
        """Find best matching files for a video file - Enhanced version"""
        video_clean = self.clean_filename(video_file)
        video_season, video_episode = self.extract_season_episode(video_file)
        video_year = self.extract_movie_year(video_file)
        
        matches = []
        
        for candidate in candidates:
            candidate_clean = self.clean_filename(candidate)
            similarity_score = self.similarity(video_clean, candidate_clean)
            
            # For TV shows, prioritize season/episode match
            if video_season is not None and video_episode is not None:
                candidate_season, candidate_episode = self.extract_season_episode(candidate)
                
                # Exact season/episode match with reasonable similarity
                if (candidate_season == video_season and 
                    candidate_episode == video_episode and 
                    similarity_score >= 0.3):  # Lower threshold for exact S/E match
                    matches.append((candidate, similarity_score + 0.5))  # Boost score
                # Good similarity without exact S/E match
                elif similarity_score >= threshold:
                    matches.append((candidate, similarity_score))
                    
            else:
                # For movies, check year match too
                if video_year:
                    candidate_year = self.extract_movie_year(candidate)
                    if candidate_year == video_year and similarity_score >= 0.3:
                        matches.append((candidate, similarity_score + 0.3))  # Boost for year match
                    elif similarity_score >= threshold:
                        matches.append((candidate, similarity_score))
                else:
                    # No year info, just use similarity
                    if similarity_score >= threshold:
                        matches.append((candidate, similarity_score))
        
        # Sort by score (descending) and return filenames
        matches.sort(key=lambda x: x[1], reverse=True)
        return [match[0] for match in matches]
    
    def detect_content_type(self, video_file: str) -> str:
        """Enhanced content type detection"""
        season, episode = self.extract_season_episode(video_file)
        year = self.extract_movie_year(video_file)
        clean_name = self.clean_filename(video_file).lower()
        
        # TV show indicators
        tv_indicators = [
            'season', 'episode', 'series', 'ep ', ' ep',
            'complete series', 'full season', 'tv show'
        ]
        
        # Movie indicators  
        movie_indicators = [
            'movie', 'film', 'cinema', 'feature',
            'directors cut', 'extended edition', 'theatrical'
        ]
        
        # Documentary indicators
        doc_indicators = [
            'documentary', 'docuseries', 'national geographic',
            'discovery', 'bbc', 'nature', 'history'
        ]
        
        # Anime indicators
        anime_indicators = [
            'anime', 'manga', 'otaku', 'sub', 'dub',
            'japanese', 'crunchyroll', 'funimation'
        ]
        
        if season and episode:
            return 'tv_show'
        elif any(indicator in clean_name for indicator in tv_indicators):
            return 'tv_show'
        elif any(indicator in clean_name for indicator in doc_indicators):
            return 'documentary'  
        elif any(indicator in clean_name for indicator in anime_indicators):
            return 'anime'
        elif any(indicator in clean_name for indicator in movie_indicators):
            return 'movie'
        elif year:
            return 'movie'  # Year usually indicates movie
        else:
            return 'unknown'
    
    def match_files(self, folder_path: str) -> List[Dict[str, any]]:
        """Match related files together intelligently - Enhanced version"""
        grouped = self.group_files_by_type(folder_path)
        matches = []
        
        video_files = grouped['video']
        subtitle_files = grouped['subtitle'] 
        audio_files = grouped['audio']
        
        if not video_files:
            LOGGER.warning("No supported video files found!")
            return matches
        
        LOGGER.info(f"Processing {len(video_files)} video files...")
        
        for video_file in video_files:
            # Enhanced content detection
            content_type = self.detect_content_type(video_file)
            season, episode = self.extract_season_episode(video_file)
            year = self.extract_movie_year(video_file)
            
            match_group = {
                'video': video_file,
                'subtitles': [],
                'audio': [],
                'type': content_type,
                'season': season,
                'episode': episode,
                'year': year,
                'clean_name': self.clean_filename(video_file),
                'file_size': 0,  # Can be populated later
                'duration': 0    # Can be populated later
            }
            
            # Find matching subtitles with multiple attempts
            matching_subs = self.find_best_matches(video_file, subtitle_files, threshold=0.4)
            match_group['subtitles'] = matching_subs
            
            # Find matching audio files
            matching_audio = self.find_best_matches(video_file, audio_files, threshold=0.4)
            match_group['audio'] = matching_audio
            
            matches.append(match_group)
            
            # Enhanced logging
            LOGGER.info(f"\n📹 Video: {video_file}")
            LOGGER.info(f"   📝 Type: {content_type}")
            if content_type == 'tv_show' and season and episode:
                LOGGER.info(f"   📺 S{season:02d}E{episode:02d}")
            elif year:
                LOGGER.info(f"   📅 Year: {year}")
            LOGGER.info(f"   📄 Subtitles ({len(matching_subs)}): {matching_subs}")
            LOGGER.info(f"   🔊 Audio ({len(matching_audio)}): {matching_audio}")
        
        return matches


class FFMpeg:
    def __init__(self, listener):
        self._listener = listener
        self._processed_bytes = 0
        self._last_processed_bytes = 0
        self._processed_time = 0
        self._last_processed_time = 0
        self._speed_raw = 0
        self._progress_raw = 0
        self._total_time = 0
        self._eta_raw = 0
        self._time_rate = 0.1
        self._start_time = 0

    @property
    def processed_bytes(self):
        return self._processed_bytes

    @property
    def speed_raw(self):
        return self._speed_raw

    @property
    def progress_raw(self):
        return self._progress_raw

    @property
    def eta_raw(self):
        return self._eta_raw

    def clear(self):
        self._start_time = time()
        self._processed_bytes = 0
        self._processed_time = 0
        self._speed_raw = 0
        self._progress_raw = 0
        self._eta_raw = 0
        self._time_rate = 0.1
        self._last_processed_time = 0
        self._last_processed_bytes = 0

    async def _ffmpeg_progress(self):
        while not (
            self._listener.subproc.returncode is not None
            or self._listener.is_cancelled
            or self._listener.subproc.stdout.at_eof()
        ):
            try:
                line = await wait_for(self._listener.subproc.stdout.readline(), 60)
            except Exception:
                break
            line = line.decode().strip()
            if not line:
                break
            if "=" in line:
                key, value = line.split("=", 1)
                if value != "N/A":
                    if key == "total_size":
                        self._processed_bytes = int(value) + self._last_processed_bytes
                        self._speed_raw = self._processed_bytes / (
                            time() - self._start_time
                        )
                    elif key == "speed":
                        self._time_rate = max(0.1, float(value.strip("x")))
                    elif key == "out_time":
                        self._processed_time = (
                            time_to_seconds(value) + self._last_processed_time
                        )
                        try:
                            self._progress_raw = (
                                self._processed_time * 100
                            ) / self._total_time
                            if (
                                hasattr(self._listener, "subsize")
                                and self._listener.subsize
                                and self._progress_raw > 0
                            ):
                                self._processed_bytes = int(
                                    self._listener.subsize * (self._progress_raw / 100)
                                )
                            if (time() - self._start_time) > 0:
                                self._speed_raw = self._processed_bytes / (
                                    time() - self._start_time
                                )
                            else:
                                self._speed_raw = 0
                            self._eta_raw = (
                                self._total_time - self._processed_time
                            ) / self._time_rate
                        except ZeroDivisionError:
                            self._progress_raw = 0
                            self._eta_raw = 0
            await sleep(0.05)

    async def ffmpeg_cmds(self, ffmpeg, f_path):
        self.clear()
        self._total_time = (await get_media_info(f_path))[0]
        base_name, ext = ospath.splitext(f_path)
        dir, base_name = base_name.rsplit("/", 1)
        indices = [
            index
            for index, item in enumerate(ffmpeg)
            if item.startswith("mltb") or item == "mltb"
        ]
        outputs = []
        for index in indices:
            output_file = ffmpeg[index]
            if output_file != "mltb" and output_file.startswith("mltb"):
                bo, oext = ospath.splitext(output_file)
                if oext:
                    if ext == oext:
                        prefix = f"ffmpeg{index}." if bo == "mltb" else ""
                    else:
                        prefix = ""
                    ext = ""
                else:
                    prefix = ""
            else:
                prefix = f"ffmpeg{index}."
            output = f"{dir}/{prefix}{output_file.replace('mltb', base_name)}{ext}"
            outputs.append(output)
            ffmpeg[index] = output
        if self._listener.is_cancelled:
            return False
        self._listener.subproc = await create_subprocess_exec(
            *ffmpeg, stdout=PIPE, stderr=PIPE
        )
        await self._ffmpeg_progress()
        _, stderr = await self._listener.subproc.communicate()
        code = self._listener.subproc.returncode
        if self._listener.is_cancelled:
            return False
        if code == 0:
            return outputs
        elif code == -9:
            self._listener.is_cancelled = True
            return False
        else:
            try:
                stderr = stderr.decode().strip()
            except Exception:
                stderr = "Unable to decode the error!"
            LOGGER.error(
                f"{stderr}. Something went wrong while running ffmpeg cmd, mostly file requires different/specific arguments. Path: {f_path}"
            )
            for op in outputs:
                if await aiopath.exists(op):
                    await remove(op)
            return False

    async def convert_video(self, video_file, ext, retry=False):
        self.clear()
        self._total_time = (await get_media_info(video_file))[0]
        base_name = ospath.splitext(video_file)[0]
        output = f"{base_name}.{ext}"
        if retry:
            cmd = [
                BinConfig.FFMPEG_NAME,
                "-hide_banner",
                "-loglevel",
                "error",
                "-progress",
                "pipe:1",
                "-i",
                video_file,
                "-map",
                "0",
                "-c:v",
                "libx264",
                "-c:a",
                "aac",
                "-threads",
                f"{max(1, cpu_no // 2)}",
                output,
            ]
            if ext == "mp4":
                cmd[14:14] = ["-c:s", "mov_text"]
            elif ext == "mkv":
                cmd[14:14] = ["-c:s", "ass"]
            else:
                cmd[14:14] = ["-c:s", "copy"]
        else:
            cmd = [
                BinConfig.FFMPEG_NAME,
                "-hide_banner",
                "-loglevel",
                "error",
                "-progress",
                "pipe:1",
                "-i",
                video_file,
                "-map",
                "0",
                "-c",
                "copy",
                "-threads",
                f"{max(1, cpu_no // 2)}",
                output,
            ]
        if self._listener.is_cancelled:
            return False
        self._listener.subproc = await create_subprocess_exec(
            *cmd, stdout=PIPE, stderr=PIPE
        )
        await self._ffmpeg_progress()
        _, stderr = await self._listener.subproc.communicate()
        code = self._listener.subproc.returncode
        if self._listener.is_cancelled:
            return False
        if code == 0:
            return output
        elif code == -9:
            self._listener.is_cancelled = True
            return False
        else:
            if await aiopath.exists(output):
                await remove(output)
            if not retry:
                return await self.convert_video(video_file, ext, True)
            try:
                stderr = stderr.decode().strip()
            except Exception:
                stderr = "Unable to decode the error!"
            LOGGER.error(
                f"{stderr}. Something went wrong while converting video, mostly file need specific codec. Path: {video_file}"
            )
        return False

    async def convert_audio(self, audio_file, ext):
        self.clear()
        self._total_time = (await get_media_info(audio_file))[0]
        base_name = ospath.splitext(audio_file)[0]
        output = f"{base_name}.{ext}"
        cmd = [
            BinConfig.FFMPEG_NAME,
            "-hide_banner",
            "-loglevel",
            "error",
            "-progress",
            "pipe:1",
            "-i",
            audio_file,
            "-threads",
            f"{max(1, cpu_no // 2)}",
            output,
        ]
        if self._listener.is_cancelled:
            return False
        self._listener.subproc = await create_subprocess_exec(
            *cmd, stdout=PIPE, stderr=PIPE
        )
        await self._ffmpeg_progress()
        _, stderr = await self._listener.subproc.communicate()
        code = self._listener.subproc.returncode
        if self._listener.is_cancelled:
            return False
        if code == 0:
            return output
        elif code == -9:
            self._listener.is_cancelled = True
            return False
        else:
            try:
                stderr = stderr.decode().strip()
            except Exception:
                stderr = "Unable to decode the error!"
            LOGGER.error(
                f"{stderr}. Something went wrong while converting audio, mostly file need specific codec. Path: {audio_file}"
            )
            if await aiopath.exists(output):
                await remove(output)
        return False

    async def sample_video(self, video_file, sample_duration, part_duration):
        self.clear()
        self._total_time = sample_duration
        dir, name = video_file.rsplit("/", 1)
        output_file = f"{dir}/SAMPLE.{name}"
        segments = [(0, part_duration)]
        duration = (await get_media_info(video_file))[0]
        remaining_duration = duration - (part_duration * 2)
        parts = (sample_duration - (part_duration * 2)) // part_duration
        time_interval = remaining_duration // parts
        next_segment = time_interval
        for _ in range(parts):
            segments.append((next_segment, next_segment + part_duration))
            next_segment += time_interval
        segments.append((duration - part_duration, duration))

        filter_complex = ""
        for i, (start, end) in enumerate(segments):
            filter_complex += (
                f"[0:v]trim=start={start}:end={end},setpts=PTS-STARTPTS[v{i}]; "
            )
            filter_complex += (
                f"[0:a]atrim=start={start}:end={end},asetpts=PTS-STARTPTS[a{i}]; "
            )

        for i in range(len(segments)):
            filter_complex += f"[v{i}][a{i}]"

        filter_complex += f"concat=n={len(segments)}:v=1:a=1[vout][aout]"

        cmd = [
            BinConfig.FFMPEG_NAME,
            "-hide_banner",
            "-loglevel",
            "error",
            "-progress",
            "pipe:1",
            "-i",
            video_file,
            "-filter_complex",
            filter_complex,
            "-map",
            "[vout]",
            "-map",
            "[aout]",
            "-c:v",
            "libx264",
            "-c:a",
            "aac",
            "-threads",
            f"{max(1, cpu_no // 2)}",
            output_file,
        ]

        if self._listener.is_cancelled:
            return False
        self._listener.subproc = await create_subprocess_exec(
            *cmd, stdout=PIPE, stderr=PIPE
        )
        await self._ffmpeg_progress()
        _, stderr = await self._listener.subproc.communicate()
        code = self._listener.subproc.returncode
        if self._listener.is_cancelled:
            return False
        if code == -9:
            self._listener.is_cancelled = True
            return False
        elif code == 0:
            return output_file
        else:
            try:
                stderr = stderr.decode().strip()
            except Exception:
                stderr = "Unable to decode the error!"
            LOGGER.error(
                f"{stderr}. Something went wrong while creating sample video, mostly file is corrupted. Path: {video_file}"
            )
            if await aiopath.exists(output_file):
                await remove(output_file)
            return False

    async def split(self, f_path, file_, parts, split_size):
        self.clear()
        multi_streams = True
        self._total_time = duration = (await get_media_info(f_path))[0]
        base_name, extension = ospath.splitext(file_)
        split_size -= 3000000
        start_time = 0
        i = 1
        while i <= parts or start_time < duration - 4:
            out_path = f_path.replace(file_, f"{base_name}.part{i:03}{extension}")
            cmd = [
                BinConfig.FFMPEG_NAME,
                "-hide_banner",
                "-loglevel",
                "error",
                "-progress",
                "pipe:1",
                "-ss",
                str(start_time),
                "-i",
                f_path,
                "-fs",
                str(split_size),
                "-map",
                "0",
                "-map_chapters",
                "-1",
                "-async",
                "1",
                "-strict",
                "-2",
                "-c",
                "copy",
                "-threads",
                f"{max(1, cpu_no // 2)}",
                out_path,
            ]
            if not multi_streams:
                del cmd[12]
                del cmd[12]
            if self._listener.is_cancelled:
                return False
            self._listener.subproc = await create_subprocess_exec(
                *cmd, stdout=PIPE, stderr=PIPE
            )
            await self._ffmpeg_progress()
            _, stderr = await self._listener.subproc.communicate()
            code = self._listener.subproc.returncode
            if self._listener.is_cancelled:
                return False
            if code == -9:
                self._listener.is_cancelled = True
                return False
            elif code != 0:
                try:
                    stderr = stderr.decode().strip()
                except Exception:
                    stderr = "Unable to decode the error!"
                with suppress(Exception):
                    await remove(out_path)
                if multi_streams:
                    LOGGER.warning(
                        f"{stderr}. Retrying without map, -map 0 not working in all situations. Path: {f_path}"
                    )
                    multi_streams = False
                    continue
                else:
                    LOGGER.warning(
                        f"{stderr}. Unable to split this video, if it's size less than {self._listener.max_split_size} will be uploaded as it is. Path: {f_path}"
                    )
                return False
            out_size = await aiopath.getsize(out_path)
            if out_size > self._listener.max_split_size:
                split_size -= (out_size - self._listener.max_split_size) + 5000000
                LOGGER.warning(
                    f"Part size is {out_size}. Trying again with lower split size!. Path: {f_path}"
                )
                await remove(out_path)
                continue
            lpd = (await get_media_info(out_path))[0]
            if lpd == 0:
                LOGGER.error(
                    f"Something went wrong while splitting, mostly file is corrupted. Path: {f_path}"
                )
                break
            elif duration == lpd:
                LOGGER.warning(
                    f"This file has been splitted with default stream and audio, so you will only see one part with less size from orginal one because it doesn't have all streams and audios. This happens mostly with MKV videos. Path: {f_path}"
                )
                break
            elif lpd <= 3:
                await remove(out_path)
                break
            self._last_processed_time += lpd
            self._last_processed_bytes += out_size
            start_time += lpd - 3
            i += 1
        return True


class EnhancedFFmpeg(FFMpeg):
    """Enhanced FFmpeg processor with smart file handling"""
    
    def __init__(self, listener):
        super().__init__(listener)
        self.matcher = SmartMediaMatcher()
        self.ffmpeg_configs = self.load_ffmpeg_configs()
    
    def load_ffmpeg_configs(self) -> Dict[str, List[str]]:
        """Load FFmpeg configurations from JSON or default configs"""
        default_configs = {
            "srt": [
                "-i", "INPUT_VIDEO", "-i", "INPUT_SUBTITLE", 
                "-map", "0:v", "-map", "0:a", "-map", "1", 
                "-c", "copy", "-c:s:0", "srt", 
                "-metadata:s:s:0", "language=sin", 
                "-metadata:s:s:0", "title=FLIXORA", 
                "-disposition:s:0", "default", 
                "-disposition:s:0", "forced", 
                "OUTPUT_FILE"
            ],
            "multi_srt": [
                "-i", "INPUT_VIDEO", "-i", "INPUT_SUBTITLE1", "-i", "INPUT_SUBTITLE2",
                "-map", "0:v", "-map", "0:a", "-map", "1", "-map", "2",
                "-c", "copy", "-c:s", "copy",
                "-metadata:s:s:0", "language=sin", "-metadata:s:s:0", "title=FLIXORA",
                "-metadata:s:s:1", "language=eng", "-metadata:s:s:1", "title=ENGLISH",
                "-disposition:s:0", "default", "-disposition:s:1", "0",
                "OUTPUT_FILE"
            ],
            "audio_embed": [
                "-i", "INPUT_VIDEO", "-i", "INPUT_AUDIO",
                "-map", "0", "-map", "1:a",
                "-c", "copy", "-c:a:1", "aac",
                "-metadata:s:a:1", "language=sin",
                "-metadata:s:a:1", "title=FLIXORA",
                "OUTPUT_FILE"
            ],
            "extract_audio": [
                "-i", "INPUT_VIDEO",
                "-vn", "-acodec", "copy",
                "OUTPUT_FILE"
            ],
            "compress": [
                "-i", "INPUT_VIDEO",
                "-c:v", "libx264", "-crf", "23", "-preset", "medium",
                "-c:a", "aac", "-b:a", "128k",
                "OUTPUT_FILE"
            ],
            "hevc": [
                "-i", "INPUT_VIDEO",
                "-c:v", "libx265", "-crf", "28", "-preset", "medium",
                "-c:a", "copy", "-c:s", "copy",
                "OUTPUT_FILE"
            ],
            "all": [
                "-i", "INPUT_VIDEO", "-i", "INPUT_SUBTITLE", "-i", "INPUT_AUDIO",
                "-map", "0:v", "-map", "0:a", "-map", "2:a", "-map", "1",
                "-c", "copy", "-c:a:1", "aac", "-c:s", "srt",
                "-metadata:s:a:1", "language=sin", "-metadata:s:a:1", "title=FLIXORA_AUDIO",
                "-metadata:s:s:0", "language=sin", "-metadata:s:s:0", "title=FLIXORA_SUB",
                "-disposition:a:0", "default", "-disposition:a:1", "0",
                "-disposition:s:0", "default", "-disposition:s:0", "forced",
                "OUTPUT_FILE"
            ]
        }
        
        # Try to load from external config file
        config_path = ospath.join(DOWNLOAD_DIR, "ffmpeg_configs.json")
        if ospath.exists(config_path):
            try:
                with open(config_path, 'r') as f:
                    custom_configs = json.load(f)
                    default_configs.update(custom_configs)
                    LOGGER.info(f"Loaded custom FFmpeg configs from {config_path}")
            except Exception as e:
                LOGGER.error(f"Error loading custom FFmpeg configs: {e}")
        
        return default_configs
    
    def get_output_extension(self, config_name: str, input_file: str) -> str:
        """Determine output file extension based on config and input"""
        input_ext = Path(input_file).suffix.lower()
        
        # Extension mapping for different configs
        extension_map = {
            'mp4': '.mp4',
            'to_mp4': '.mp4',
            'avi': '.avi', 
            'to_avi': '.avi',
            'extract_mp3': '.mp3',
            'extract_flac': '.flac',
            'extract_audio': '.aac',  # Default audio format
            'extract_srt': '.srt',
        }
        
        # Check if config specifies extension
        if config_name in extension_map:
            return extension_map[config_name]
        
        # For most processing, keep original extension or default to mkv
        if input_ext in self.video_extensions:
            return input_ext if input_ext in ['.mp4', '.mkv', '.avi'] else '.mkv'
        
        return '.mkv'  # Default fallback
    
    def build_ffmpeg_command(self, match_group: Dict, config_name: str, folder_path: str) -> Tuple[List[str], str]:
        """Build FFmpeg command from template and file matches - Enhanced version"""
        if config_name not in self.ffmpeg_configs:
            available = list(self.ffmpeg_configs.keys())
            raise ValueError(f"Unknown config: {config_name}. Available: {available}")
        
        template = self.ffmpeg_configs[config_name].copy()
        
        # Generate output filename with proper extension
        video_name = Path(match_group['video']).stem
        output_ext = self.get_output_extension(config_name, match_group['video'])
        
        # Create descriptive filename based on content type
        if match_group['type'] == 'tv_show' and match_group['season'] and match_group['episode']:
            season = f"S{match_group['season']:02d}"
            episode = f"E{match_group['episode']:02d}"
            output_name = f"{video_name}.{season}{episode}.FLIXORA{output_ext}"
        elif match_group['year']:
            output_name = f"{video_name}.{match_group['year']}.FLIXORA{output_ext}"
        else:
            output_name = f"{video_name}.FLIXORA{output_ext}"
        
        output_path = ospath.join(folder_path, output_name)
        
        # Build command with actual file paths
        cmd = [BinConfig.FFMPEG_NAME, "-hide_banner", "-loglevel", "error", "-progress", "pipe:1"]
        
        # Replace placeholders in template
        i = 0
        while i < len(template):
            arg = template[i]
            
            if arg == "INPUT_VIDEO":
                cmd.extend(["-i", ospath.join(folder_path, match_group['video'])])
            elif arg == "INPUT_SUBTITLE" and match_group['subtitles']:
                cmd.extend(["-i", ospath.join(folder_path, match_group['subtitles'][0])])
            elif arg == "INPUT_SUBTITLE1" and match_group['subtitles']:
                cmd.extend(["-i", ospath.join(folder_path, match_group['subtitles'][0])])
            elif arg == "INPUT_SUBTITLE2" and len(match_group['subtitles']) > 1:
                cmd.extend(["-i", ospath.join(folder_path, match_group['subtitles'][1])])
            elif arg == "INPUT_AUDIO" and match_group['audio']:
                cmd.extend(["-i", ospath.join(folder_path, match_group['audio'][0])])
            elif arg == "OUTPUT_FILE":
                cmd.append(output_path)
            elif not arg.startswith("INPUT_"):  # Skip unmatched INPUT_ placeholders
                cmd.append(arg)
            
            i += 1
        
        # Add threading optimization
        cmd.extend(["-threads", str(max(1, cpu_no // 2))])
        
        return cmd, output_path
    
    def validate_requirements(self, match_group: Dict, config_name: str) -> Tuple[bool, str]:
        """Validate if match group has required files for the config - Enhanced version"""
        requirements = {
            # Subtitle configs
            "srt": {"subtitles": 1},
            "multi_srt": {"subtitles": 2},
            "extract_srt": {},
            
            # Audio configs
            "audio_embed": {"audio": 1},
            "extract_audio": {},
            "extract_mp3": {},
            "extract_flac": {},
            "normalize": {},
            
            # Video processing (no additional files needed)
            "compress": {},
            "hq_compress": {},
            "hevc": {},
            "mp4": {},
            "mkv": {},
            "to_mp4": {},
            "to_mkv": {},
            "to_avi": {},
            "720p": {},
            "1080p": {},
            "anime": {},
            "hdr": {},
            "fix": {},
            "sample": {},
            "clean": {},
            "deinterlace": {},
            "rotate_90": {},
            "rotate_180": {},
            "rotate_270": {},
            
            # Combined configs
            "all": {"subtitles": 1, "audio": 1}
        }
        
        if config_name not in requirements:
            available = list(requirements.keys())
            return False, f"Unknown config: {config_name}. Available: {', '.join(available)}"
        
        req = requirements[config_name]
        
        # Check requirements
        for file_type, min_count in req.items():
            actual_count = len(match_group.get(file_type, []))
            if actual_count < min_count:
                return False, f"Need at least {min_count} {file_type} file(s), found {actual_count}"
        
        return True, "✅ Requirements met"
    
    async def process_single_match(self, match_group: Dict, config_name: str, folder_path: str) -> Optional[str]:
        """Process a single file match group"""
        try:
            # Validate requirements
            valid, msg = self.validate_requirements(match_group, config_name)
            if not valid:
                LOGGER.warning(f"Skipping {match_group['video']}: {msg}")
                return None
            
            # Build command
            cmd, output_path = self.build_ffmpeg_command(match_group, config_name, folder_path)
            
            LOGGER.info(f"Processing: {match_group['video']} -> {Path(output_path).name}")
            LOGGER.info(f"Command: {' '.join(cmd)}")
            
            # Execute FFmpeg
            video_path = ospath.join(folder_path, match_group['video'])
            result = await self.ffmpeg_cmds(cmd, video_path)
            
            if result:
                LOGGER.info(f"Successfully processed: {match_group['video']}")
                return output_path
            else:
                LOGGER.error(f"Failed to process: {match_group['video']}")
                return None
                
        except Exception as e:
            LOGGER.error(f"Error processing {match_group['video']}: {e}")
            return None
    
    async def process_folder(self, folder_path: str, config_name: str = "srt", delete_originals: bool = False) -> List[str]:
        """Process all matching files in a folder"""
        LOGGER.info(f"Starting folder processing: {folder_path}")
        LOGGER.info(f"Config: {config_name}, Delete originals: {delete_originals}")
        
        if not ospath.exists(folder_path):
            LOGGER.error(f"Folder does not exist: {folder_path}")
            return []
        
        # Match files
        matches = self.matcher.match_files(folder_path)
        
        if not matches:
            LOGGER.warning("No video files found in folder")
            return []
        
        processed_files = []
        successful_matches = []
        
        # Process each match group
        for match_group in matches:
            LOGGER.info(f"\n--- Processing {match_group['video']} ---")
            LOGGER.info(f"Type: {match_group['type']}")
            if match_group['type'] == 'tv_show':
                LOGGER.info(f"Season {match_group['season']}, Episode {match_group['episode']}")
            LOGGER.info(f"Subtitles: {match_group['subtitles']}")
            LOGGER.info(f"Audio: {match_group['audio']}")
            
            result = await self.process_single_match(match_group, config_name, folder_path)
            
            if result:
                processed_files.append(result)
                successful_matches.append(match_group)
            
        # Clean up original files if requested
        if delete_originals and successful_matches:
            await self.cleanup_originals(folder_path, successful_matches)
        
        LOGGER.info(f"\nProcessing complete! Successfully processed {len(processed_files)} files")
        for file in processed_files:
            LOGGER.info(f"Output: {file}")
        
        return processed_files
    
    async def cleanup_originals(self, folder_path: str, successful_matches: List[Dict]):
        """Clean up original files after successful processing"""
        LOGGER.info("Cleaning up original files...")
        
        files_to_delete = set()
        
        for match_group in successful_matches:
            # Add video file
            files_to_delete.add(match_group['video'])
            
            # Add subtitle files
            files_to_delete.update(match_group['subtitles'])
            
            # Add audio files  
            files_to_delete.update(match_group['audio'])
        
        for filename in files_to_delete:
            file_path = ospath.join(folder_path, filename)
            try:
                if await aiopath.exists(file_path):
                    await remove(file_path)
                    LOGGER.info(f"Deleted: {filename}")
            except Exception as e:
                LOGGER.error(f"Error deleting {filename}: {e}")


# Main processing function
async def process_media_folder(folder_path: str, config_name: str, listener, delete_originals: bool = False):
    """
    Main function to process a folder with media files
    
    Args:
        folder_path: Path to folder containing media files
        config_name: FFmpeg configuration to use
        listener: Your existing listener object
        delete_originals: Whether to delete original files after processing
    
    Returns:
        List of processed file paths
    """
    
    try:
        enhanced_ffmpeg = EnhancedFFmpeg(listener)
        processed_files = await enhanced_ffmpeg.process_folder(
            folder_path, 
            config_name, 
            delete_originals
        )
        return processed_files
        
    except Exception as e:
        LOGGER.error(f"Error in process_media_folder: {e}")
        return []


# Enhanced utility functions with format detection
async def smart_subtitle_embed(folder_path: str, listener, delete_originals: bool = False):
    """Smart subtitle embedding for all supported video formats"""
    return await process_media_folder(folder_path, "srt", listener, delete_originals)


async def smart_audio_embed(folder_path: str, listener, delete_originals: bool = False):
    """Smart audio embedding for all supported video formats"""
    return await process_media_folder(folder_path, "audio_embed", listener, delete_originals)


async def smart_compress(folder_path: str, listener, delete_originals: bool = False):
    """Smart video compression for all supported formats"""
    return await process_media_folder(folder_path, "compress", listener, delete_originals)


async def smart_convert_mp4(folder_path: str, listener, delete_originals: bool = False):
    """Convert any video format to MP4"""
    return await process_media_folder(folder_path, "to_mp4", listener, delete_originals)


async def smart_convert_mkv(folder_path: str, listener, delete_originals: bool = False):
    """Convert any video format to MKV"""
    return await process_media_folder(folder_path, "to_mkv", listener, delete_originals)


async def smart_hevc_encode(folder_path: str, listener, delete_originals: bool = False):
    """Convert to HEVC for better compression"""
    return await process_media_folder(folder_path, "hevc", listener, delete_originals)


async def smart_720p_scale(folder_path: str, listener, delete_originals: bool = False):
    """Scale videos to 720p"""
    return await process_media_folder(folder_path, "720p", listener, delete_originals)


async def smart_1080p_scale(folder_path: str, listener, delete_originals: bool = False):
    """Scale videos to 1080p"""  
    return await process_media_folder(folder_path, "1080p", listener, delete_originals)


async def smart_extract_audio(folder_path: str, listener, format_type: str = "aac"):
    """Extract audio from videos in specified format"""
    config_map = {
        "mp3": "extract_mp3",
        "flac": "extract_flac", 
        "aac": "extract_audio"
    }
    config = config_map.get(format_type, "extract_audio")
    return await process_media_folder(folder_path, config, listener, False)


async def smart_fix_corrupted(folder_path: str, listener, delete_originals: bool = False):
    """Fix corrupted video files"""
    return await process_media_folder(folder_path, "fix", listener, delete_originals)


async def smart_all_process(folder_path: str, listener, delete_originals: bool = False):
    """Process with subtitles and audio together for all formats"""
    return await process_media_folder(folder_path, "all", listener, delete_originals)


# Advanced batch processing functions
async def batch_process_by_type(folder_path: str, listener, delete_originals: bool = False):
    """Automatically choose best processing based on content type"""
    enhanced_ffmpeg = EnhancedFFmpeg(listener)
    matches = enhanced_ffmpeg.matcher.match_files(folder_path)
    
    results = []
    
    for match_group in matches:
        content_type = match_group['type']
        
        # Choose optimal config based on content type
        if content_type == 'anime' and match_group['subtitles']:
            config = 'srt'  # Anime usually needs subtitles
        elif content_type == 'tv_show' and match_group['subtitles']:
            config = 'srt'  # TV shows often need subtitles
        elif match_group['subtitles'] and match_group['audio']:
            config = 'all'  # Both available
        elif match_group['subtitles']:
            config = 'srt'  # Only subtitles
        elif match_group['audio']:
            config = 'audio_embed'  # Only audio
        else:
            config = 'mkv'  # Just convert to standard format
        
        LOGGER.info(f"Auto-selected '{config}' for {match_group['video']} (type: {content_type})")
        
        result = await enhanced_ffmpeg.process_single_match(match_group, config, folder_path)
        if result:
            results.append(result)
    
    if delete_originals and results:
        successful_matches = [m for i, m in enumerate(matches) if i < len(results)]
        await enhanced_ffmpeg.cleanup_originals(folder_path, successful_matches)
    
    return results


# Format detection and info functions
async def get_video_info(file_path: str):
    """Get comprehensive video information"""
    try:
        duration, quality, audio_langs, subtitle_langs = await get_media_info(file_path, extra_info=True)
        
        info = {
            'duration': duration,
            'quality': quality, 
            'audio_languages': audio_langs,
            'subtitle_languages': subtitle_langs,
            'file_size': await aiopath.getsize(file_path) if await aiopath.exists(file_path) else 0,
            'format': Path(file_path).suffix.lower(),
            'is_supported': Path(file_path).suffix.lower() in SmartMediaMatcher().video_extensions
        }
        
        return info
    except Exception as e:
        LOGGER.error(f"Error getting video info for {file_path}: {e}")
        return None


async def analyze_folder(folder_path: str) -> Dict:
    """Analyze folder contents and provide recommendations"""
    matcher = SmartMediaMatcher()
    grouped = matcher.group_files_by_type(folder_path)
    matches = matcher.match_files(folder_path)
    
    analysis = {
        'total_videos': len(grouped['video']),
        'total_subtitles': len(grouped['subtitle']),
        'total_audio': len(grouped['audio']),
        'content_types': {},
        'matched_groups': len(matches),
        'recommended_configs': [],
        'unsupported_formats': []
    }
    
    # Analyze content types
    for match in matches:
        content_type = match['type']
        analysis['content_types'][content_type] = analysis['content_types'].get(content_type, 0) + 1
    
    # Check for unsupported formats
    for video_file in grouped['video']:
        if not matcher.is_supported_video(video_file):
            analysis['unsupported_formats'].append(video_file)
    
    # Generate recommendations
    if analysis['total_subtitles'] > 0 and analysis['total_audio'] > 0:
        analysis['recommended_configs'].append('all')
    elif analysis['total_subtitles'] > 0:
        analysis['recommended_configs'].append('srt')
    elif analysis['total_audio'] > 0:
        analysis['recommended_configs'].append('audio_embed')
    else:
        analysis['recommended_configs'].extend(['compress', 'to_mkv'])
    
    return analysis


# Configuration management
def list_available_configs() -> List[str]:
    """List all available FFmpeg configurations"""
    enhanced_ffmpeg = EnhancedFFmpeg(None)  # Dummy listener for config loading
    return list(enhanced_ffmpeg.ffmpeg_configs.keys())


def get_config_info(config_name: str) -> Dict:
    """Get information about a specific config"""
    enhanced_ffmpeg = EnhancedFFmpeg(None)
    
    if config_name not in enhanced_ffmpeg.ffmpeg_configs:
        return {'error': f'Config {config_name} not found'}
    
    template = enhanced_ffmpeg.ffmpeg_configs[config_name]
    
    info = {
        'name': config_name,
        'requires_subtitle': 'INPUT_SUBTITLE' in template,
        'requires_audio': 'INPUT_AUDIO' in template, 
        'description': get_config_description(config_name),
        'template': template
    }
    
    return info


def get_config_description(config_name: str) -> str:
    """Get human-readable description of config"""
    descriptions = {
        'srt': 'Embed subtitle file into video',
        'multi_srt': 'Embed multiple subtitle files',
        'audio_embed': 'Add audio track to video',
        'extract_audio': 'Extract audio from video',
        'compress': 'Compress video with good quality',
        'hq_compress': 'High quality compression',
        'hevc': 'Convert to HEVC format',
        'mp4': 'Convert to MP4 format',
        'to_mkv': 'Convert to MKV format',
        'to_avi': 'Convert to AVI format',
        '720p': 'Scale video to 720p resolution',
        '1080p': 'Scale video to 1080p resolution',
        'anime': 'Optimized encoding for anime content',
        'hdr': 'Preserve HDR content',
        'all': 'Embed both subtitles and audio',
        'extract_mp3': 'Extract audio as MP3',
        'extract_flac': 'Extract audio as FLAC',
        'fix': 'Fix corrupted video files',
        'sample': 'Create short preview sample',
        'clean': 'Remove metadata from video',
        'normalize': 'Normalize audio levels',
        'deinterlace': 'Remove interlacing artifacts',
        'rotate_90': 'Rotate video 90 degrees clockwise',
        'rotate_180': 'Rotate video 180 degrees',
        'rotate_270': 'Rotate video 270 degrees clockwise'
    }
    
    return descriptions.get(config_name, 'Unknown configuration')