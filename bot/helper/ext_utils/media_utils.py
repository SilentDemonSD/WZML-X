from contextlib import suppress
from PIL import Image
from hashlib import md5
from aiofiles.os import remove, path as aiopath, makedirs
import json
from asyncio import (
    create_subprocess_exec,
    gather,
    wait_for,
    sleep,
)
import re
import glob
from asyncio.subprocess import PIPE
from os import path as ospath
from re import search as re_search, escape, findall
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


def extract_episode_info(filename):
    """
    Extract season and episode information from filename using multiple patterns.
    Enhanced version with better pattern matching.
    
    Returns:
        tuple: (season, episode, title_part) or (None, None, None) if no match
    """
    # Remove file extension for matching
    name_without_ext = ospath.splitext(filename)[0]
    original_name = name_without_ext
    
    LOGGER.debug(f"Analyzing filename: {filename}")
    
    # Pattern 1: S##E## format (most common) - more flexible
    pattern1 = r'[Ss](\d{1,2})[Ee](\d{1,2})'
    match = re_search(pattern1, name_without_ext)
    if match:
        season = int(match.group(1))
        episode = int(match.group(2))
        # Extract title part (everything before season info)
        title_part = name_without_ext[:match.start()].strip(' -_[]')
        LOGGER.debug(f"Pattern 1 matched: S{season}E{episode}, title: '{title_part}'")
        return season, episode, title_part
    
    # Pattern 2: Season ## Episode ## format
    pattern2 = r'[Ss]eason\s*(\d{1,2})\s*[Ee]pisode\s*(\d{1,2})'
    match = re_search(pattern2, name_without_ext, re.IGNORECASE)
    if match:
        season = int(match.group(1))
        episode = int(match.group(2))
        title_part = name_without_ext[:match.start()].strip(' -_[]')
        LOGGER.debug(f"Pattern 2 matched: Season {season} Episode {episode}, title: '{title_part}'")
        return season, episode, title_part
    
    # Pattern 3: Episode number at the end (assumes season 1)
    pattern3 = r'[Ee]pisode?\s*(\d{1,2})(?:\s|$|[^\w])'
    match = re_search(pattern3, name_without_ext)
    if match:
        season = 1
        episode = int(match.group(1))
        title_part = name_without_ext[:match.start()].strip(' -_[]')
        LOGGER.debug(f"Pattern 3 matched: Episode {episode}, title: '{title_part}'")
        return season, episode, title_part
    
    # Pattern 4: Just numbers like "- 01", "- 02" etc. (more precise)
    pattern4 = r'[- _](\d{2})(?:[- _]|[\[\(]|$)'
    matches = findall(pattern4, name_without_ext)
    if matches:
        # Take the last number as episode
        episode = int(matches[-1])
        season = 1
        # Remove the episode number part
        title_match = re_search(r'^(.+?)[- _]\d{2}(?:[- _]|[\[\(]|$)', name_without_ext)
        if title_match:
            title_part = title_match.group(1).strip(' -_[]')
        else:
            title_part = name_without_ext
        LOGGER.debug(f"Pattern 4 matched: Episode {episode}, title: '{title_part}'")
        return season, episode, title_part
    
    # Pattern 5: Single digit episodes like "- 1", "- 2"
    pattern5 = r'[- _](\d{1})(?:[- _]|[\[\(]|$)'
    matches = findall(pattern5, name_without_ext)
    if matches:
        episode = int(matches[-1])
        season = 1
        title_match = re_search(r'^(.+?)[- _]\d{1}(?:[- _]|[\[\(]|$)', name_without_ext)
        if title_match:
            title_part = title_match.group(1).strip(' -_[]')
        else:
            title_part = name_without_ext
        LOGGER.debug(f"Pattern 5 matched: Episode {episode}, title: '{title_part}'")
        return season, episode, title_part
    
    LOGGER.debug(f"No pattern matched for: {filename}")
    return None, None, None


def normalize_title(title):
    """
    Normalize title for better matching by removing special characters and extra spaces.
    """
    import re
    # Remove brackets and their contents
    title = re.sub(r'\[.*?\]', '', title)
    title = re.sub(r'\(.*?\)', '', title)
    # Remove special characters and normalize spaces
    title = re.sub(r'[^\w\s]', ' ', title)
    title = re.sub(r'\s+', ' ', title)
    return title.strip().lower()


def find_episode_pairs_method1(mkv_files, srt_files):
    """
    Method 1: Exact base name matching (original method)
    """
    file_pairs = []
    for mkv_file in mkv_files:
        mkv_base = ospath.splitext(ospath.basename(mkv_file))[0]
        for srt_file in srt_files:
            srt_base = ospath.splitext(ospath.basename(srt_file))[0]
            if mkv_base == srt_base:
                file_pairs.append((mkv_file, srt_file, mkv_base))
                break
    return file_pairs


def find_episode_pairs_method2(mkv_files, srt_files):
    """
    Method 2: Season/Episode matching with title similarity - Enhanced
    """
    file_pairs = []
    mkv_episodes = []
    srt_episodes = []
    
    # Extract episode info for all files with better logging
    LOGGER.info("Extracting episode info from MKV files:")
    for mkv_file in mkv_files:
        filename = ospath.basename(mkv_file)
        season, episode, title = extract_episode_info(filename)
        LOGGER.info(f"  {filename} -> S{season}E{episode} | Title: '{title}'")
        if season is not None and episode is not None:
            mkv_episodes.append((mkv_file, season, episode, title, filename))
    
    LOGGER.info("Extracting episode info from SRT files:")
    for srt_file in srt_files:
        filename = ospath.basename(srt_file)
        season, episode, title = extract_episode_info(filename)
        LOGGER.info(f"  {filename} -> S{season}E{episode} | Title: '{title}'")
        if season is not None and episode is not None:
            srt_episodes.append((srt_file, season, episode, title, filename))
    
    # Sort episodes by season and episode number for proper matching
    mkv_episodes.sort(key=lambda x: (x[1], x[2]))  # Sort by season, episode
    srt_episodes.sort(key=lambda x: (x[1], x[2]))  # Sort by season, episode
    
    used_srt = set()
    
    # Match by season/episode and title similarity
    for mkv_file, mkv_season, mkv_episode, mkv_title, mkv_filename in mkv_episodes:
        best_match = None
        best_score = 0
        best_srt_info = None
        
        LOGGER.info(f"Looking for match for MKV: S{mkv_season:02d}E{mkv_episode:02d} - {mkv_title}")
        
        for srt_file, srt_season, srt_episode, srt_title, srt_filename in srt_episodes:
            if srt_file in used_srt:
                continue
                
            # Must match season and episode exactly
            if mkv_season == srt_season and mkv_episode == srt_episode:
                # Calculate title similarity
                mkv_norm = normalize_title(mkv_title)
                srt_norm = normalize_title(srt_title)
                
                # Simple similarity score based on common words
                mkv_words = set(mkv_norm.split())
                srt_words = set(srt_norm.split())
                
                if mkv_words and srt_words:
                    common_words = mkv_words.intersection(srt_words)
                    total_words = mkv_words.union(srt_words)
                    score = len(common_words) / len(total_words) if total_words else 0
                else:
                    score = 1.0 if mkv_norm == srt_norm else 0.0
                
                LOGGER.info(f"    Checking SRT: S{srt_season:02d}E{srt_episode:02d} - {srt_title} | Similarity: {score:.2f}")
                
                if score > best_score:
                    best_score = score
                    best_match = srt_file
                    best_srt_info = (srt_season, srt_episode, srt_title)
        
        if best_match and best_score > 0.1:  # Lower threshold for better matching
            base_name = f"S{mkv_season:02d}E{mkv_episode:02d}"
            file_pairs.append((mkv_file, best_match, base_name))
            used_srt.add(best_match)
            LOGGER.info(f"    ✅ MATCHED: {base_name} | Score: {best_score:.2f}")
        else:
            LOGGER.warning(f"    ❌ NO MATCH FOUND for S{mkv_season:02d}E{mkv_episode:02d}")
    
    return file_pairs


def find_episode_pairs_method3(mkv_files, srt_files):
    """
    Method 3: Fuzzy matching based on filename similarity
    """
    def similarity_score(str1, str2):
        """Calculate similarity between two strings"""
        str1_norm = normalize_title(str1)
        str2_norm = normalize_title(str2)
        
        words1 = set(str1_norm.split())
        words2 = set(str2_norm.split())
        
        if not words1 and not words2:
            return 1.0
        if not words1 or not words2:
            return 0.0
        
        intersection = words1.intersection(words2)
        union = words1.union(words2)
        
        return len(intersection) / len(union)
    
    file_pairs = []
    used_srt = set()
    
    for mkv_file in mkv_files:
        mkv_name = ospath.splitext(ospath.basename(mkv_file))[0]
        best_match = None
        best_score = 0
        
        for srt_file in srt_files:
            if srt_file in used_srt:
                continue
                
            srt_name = ospath.splitext(ospath.basename(srt_file))[0]
            score = similarity_score(mkv_name, srt_name)
            
            if score > best_score and score > 0.5:  # Minimum 50% similarity
                best_score = score
                best_match = srt_file
        
        if best_match:
            used_srt.add(best_match)
            # Try to extract episode info for better naming
            season, episode, title = extract_episode_info(mkv_name)
            if season and episode:
                base_name = f"S{season:02d}E{episode:02d}"
            else:
                base_name = ospath.splitext(ospath.basename(mkv_file))[0]
            file_pairs.append((mkv_file, best_match, base_name))
    
    return file_pairs


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
        base_name, ext = ospath.splitext(f_path)
        dir, base_name = base_name.rsplit("/", 1)
        
        # Check for -del flag
        delete_originals = False
        if "-del" in ffmpeg:
            delete_originals = True
            ffmpeg = [item for item in ffmpeg if item != "-del"]
        
        # Check if we're using wildcards for multiple file processing
        has_mkv_wildcard = "*.mkv" in ffmpeg
        has_srt_wildcard = "*.srt" in ffmpeg
        
        if has_mkv_wildcard and has_srt_wildcard:
            # Multiple file processing mode
            return await self._process_multiple_files(ffmpeg, f_path, dir, delete_originals)
        else:
            # Single file processing mode (original logic)
            return await self._process_single_file(ffmpeg, f_path, dir, base_name, ext, delete_originals)
    
    async def _process_multiple_files(self, ffmpeg, f_path, dir, delete_originals):
        """Process multiple video-subtitle pairs in the directory with enhanced matching and detailed logging"""
        
        # Find all MKV and SRT files in the directory
        mkv_pattern = ospath.join(dir, "*.mkv")
        srt_pattern = ospath.join(dir, "*.srt")
        
        mkv_files = glob.glob(mkv_pattern)
        srt_files = glob.glob(srt_pattern)
        
        if not mkv_files:
            LOGGER.error("No MKV files found in directory!")
            return False
        
        if not srt_files:
            LOGGER.error("No SRT files found in directory!")
            return False
        
        LOGGER.info(f"Found {len(mkv_files)} MKV files and {len(srt_files)} SRT files")
        
        # Log all files for debugging
        LOGGER.info("Available MKV files:")
        for i, mkv in enumerate(mkv_files, 1):
            LOGGER.info(f"  {i}. {ospath.basename(mkv)}")
        
        LOGGER.info("Available SRT files:")
        for i, srt in enumerate(srt_files, 1):
            LOGGER.info(f"  {i}. {ospath.basename(srt)}")
        
        # Try different matching methods
        file_pairs = []
        matching_method = ""
        
        # Method 1: Exact base name matching
        LOGGER.info("\n=== TRYING METHOD 1: Exact base name matching ===")
        file_pairs = find_episode_pairs_method1(mkv_files, srt_files)
        if file_pairs:
            matching_method = "Method 1 (Exact base name)"
            LOGGER.info(f"✅ Method 1 succeeded! Found {len(file_pairs)} pairs")
        
        # Method 2: Season/Episode matching if Method 1 fails
        if not file_pairs:
            LOGGER.info("\n=== METHOD 1 FAILED - TRYING METHOD 2: Season/Episode matching ===")
            file_pairs = find_episode_pairs_method2(mkv_files, srt_files)
            if file_pairs:
                matching_method = "Method 2 (Season/Episode)"
                LOGGER.info(f"✅ Method 2 succeeded! Found {len(file_pairs)} pairs")
        
        # Method 3: Fuzzy matching if Method 2 fails
        if not file_pairs:
            LOGGER.info("\n=== METHOD 2 FAILED - TRYING METHOD 3: Fuzzy filename matching ===")
            file_pairs = find_episode_pairs_method3(mkv_files, srt_files)
            if file_pairs:
                matching_method = "Method 3 (Fuzzy matching)"
                LOGGER.info(f"✅ Method 3 succeeded! Found {len(file_pairs)} pairs")
        
        if not file_pairs:
            LOGGER.error("\n❌ ALL MATCHING METHODS FAILED!")
            LOGGER.error("Please check that your MKV and SRT files have matching episode information")
            LOGGER.error("Supported formats: S01E01, Season 1 Episode 1, Episode 01, - 01, etc.")
            return False
        
        LOGGER.info(f"\n🎉 SUCCESS: Using {matching_method}")
        LOGGER.info("Final matched pairs:")
        for i, (mkv_file, srt_file, base_name) in enumerate(file_pairs, 1):
            LOGGER.info(f"  {i}. {base_name}")
            LOGGER.info(f"     Video: {ospath.basename(mkv_file)}")
            LOGGER.info(f"     Sub:   {ospath.basename(srt_file)}")
        
        # Process each pair
        all_outputs = []
        files_to_delete = []
        
        LOGGER.info(f"\n🔄 Starting processing of {len(file_pairs)} pairs...")
        
        for pair_num, (mkv_file, srt_file, base_name) in enumerate(file_pairs, 1):
            LOGGER.info(f"\n--- Processing pair {pair_num}/{len(file_pairs)}: {base_name} ---")
            LOGGER.info(f"Video: {ospath.basename(mkv_file)}")
            LOGGER.info(f"Sub:   {ospath.basename(srt_file)}")
            
            # Get duration for this specific video
            self._total_time = (await get_media_info(mkv_file))[0]
            LOGGER.info(f"Duration: {self._total_time} seconds")
            
            # Create FFmpeg command for this specific pair
            current_ffmpeg = []
            for item in ffmpeg:
                if item == "*.mkv":
                    current_ffmpeg.append(mkv_file)
                elif item == "*.srt":
                    current_ffmpeg.append(srt_file)
                elif item.startswith("mltb"):
                    if item == "mltb.Sub.mkv":
                        output_file = f"{dir}/{base_name}.Sub.mkv"
                        current_ffmpeg.append(output_file)
                        all_outputs.append(output_file)
                    elif item == "mltb.mkv":
                        output_file = f"{dir}/{base_name}.mkv"
                        current_ffmpeg.append(output_file)
                        all_outputs.append(output_file)
                    else:
                        # Handle other mltb variations
                        output_file = f"{dir}/{item.replace('mltb', base_name)}"
                        current_ffmpeg.append(output_file)
                        all_outputs.append(output_file)
                else:
                    current_ffmpeg.append(item)
            
            # Track files for deletion
            if delete_originals:
                files_to_delete.extend([mkv_file, srt_file])
            
            LOGGER.info(f"FFmpeg command: {' '.join(current_ffmpeg)}")
            
            # Execute FFmpeg for this pair
            if self._listener.is_cancelled:
                LOGGER.warning("Processing cancelled by user")
                return False
                
            self._listener.subproc = await create_subprocess_exec(
                *current_ffmpeg, stdout=PIPE, stderr=PIPE
            )
            await self._ffmpeg_progress()
            _, stderr = await self._listener.subproc.communicate()
            code = self._listener.subproc.returncode
            
            if self._listener.is_cancelled:
                LOGGER.warning("Processing cancelled by user")
                return False
                
            if code != 0:
                try:
                    stderr = stderr.decode().strip()
                except Exception:
                    stderr = "Unable to decode the error!"
                LOGGER.error(f"❌ Failed to process {ospath.basename(mkv_file)}: {stderr}")
                # Clean up any partial outputs
                for output in all_outputs:
                    if await aiopath.exists(output):
                        await remove(output)
                return False
            
            LOGGER.info(f"✅ Successfully processed: {base_name}")
        
        # Delete original files if requested and all processing succeeded
        if delete_originals:
            LOGGER.info(f"\n🗑️  Deleting {len(files_to_delete)} original files...")
            for file_to_delete in files_to_delete:
                try:
                    if await aiopath.exists(file_to_delete):
                        await remove(file_to_delete)
                        LOGGER.info(f"Deleted: {ospath.basename(file_to_delete)}")
                except Exception as e:
                    LOGGER.error(f"Failed to delete file {file_to_delete}: {e}")
        
        LOGGER.info(f"\n🎉 COMPLETE: Successfully processed {len(file_pairs)} video-subtitle pairs using {matching_method}")
        return all_outputs
    
    async def _process_single_file(self, ffmpeg, f_path, dir, base_name, ext, delete_originals):
        """Original single file processing logic"""
        self._total_time = (await get_media_info(f_path))[0]
        
        # Handle wildcards in ffmpeg command before processing mltb replacements
        expanded_ffmpeg = []
        input_files = []
        for i, item in enumerate(ffmpeg):
            if '*' in item and not item.startswith('mltb'):
                wildcard_pattern = ospath.join(dir, item)
                matches = glob.glob(wildcard_pattern)
                if matches:
                    expanded_file = matches[0]
                    expanded_ffmpeg.append(expanded_file)
                    if i > 0 and ffmpeg[i-1] == "-i":
                        input_files.append(expanded_file)
                else:
                    expanded_ffmpeg.append(item)
            else:
                expanded_ffmpeg.append(item)
        
        ffmpeg = expanded_ffmpeg
        
        # Find mltb placeholders for output files only
        indices = []
        for index, item in enumerate(ffmpeg):
            if item.startswith("mltb") or item == "mltb":
                is_output = True
                if index > 0 and ffmpeg[index-1] == "-i":
                    is_output = False
                if is_output:
                    indices.append(index)
        
        outputs = []
        for index in indices:
            output_file = ffmpeg[index]
            if output_file != "mltb" and output_file.startswith("mltb"):
                if "." in output_file:
                    output = f"{dir}/{output_file.replace('mltb', base_name)}"
                else:
                    output = f"{dir}/{output_file.replace('mltb', base_name)}{ext}"
            else:
                output = f"{dir}/{base_name}{ext}"
            
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
            if delete_originals:
                for input_file in input_files:
                    try:
                        if await aiopath.exists(input_file):
                            await remove(input_file)
                            LOGGER.info(f"Deleted original file: {input_file}")
                    except Exception as e:
                        LOGGER.error(f"Failed to delete file {input_file}: {e}")
            return outputs
        elif code == -9:
            self._listener.is_cancelled = True
            return False
        else:
            try:
                stderr = stderr.decode().strip()
            except Exception:
                stderr = "Unable to decode the error!"
            LOGGER.error(f"{stderr}. Something went wrong while running ffmpeg cmd, mostly file requires different/specific arguments. Path: {f_path}")
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