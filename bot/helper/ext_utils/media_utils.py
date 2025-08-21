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

import glob
from asyncio.subprocess import PIPE
from os import path as ospath
from re import search as re_search, escape
from time import time
from aioshutil import rmtree
from langcodes import Language
from difflib import SequenceMatcher
import re

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


class SmartFilematcher:
    """Enhanced file matching system for mixed movie and TV show environments"""
    
    def __init__(self):
        # TV show patterns (more comprehensive)
        self.tv_patterns = [
            r'[Ss](\d{1,2})[Ee](\d{1,2})',  # S01E01, s1e1
            r'Season\s*(\d{1,2})\s*Episode\s*(\d{1,2})',  # Season 1 Episode 1
            r'(\d{1,2})x(\d{1,2})',  # 1x01
            r'[Ee]pisode\s*(\d{1,2})',  # Episode 01 (season implied)
            r'[Ee]p\s*(\d{1,2})',  # Ep 01
            r'Part\s*(\d{1,2})',  # Part 1 (for multi-part episodes)
            r'Chapter\s*(\d{1,2})',  # Chapter 1
        ]
        
        # Movie indicator words
        self.movie_indicators = [
            'movie', 'film', 'cinema', 'dvdrip', 'brrip', 'webrip',
            'bluray', 'hdcam', 'ts', 'cam', 'dvdscr', 'hdrip',
            '1080p', '720p', '480p', '4k', 'uhd', 'hd',
            'director.cut', 'extended', 'uncut', 'remastered'
        ]
        
        # Common quality/encoding patterns to ignore for matching
        self.noise_patterns = [
            r'\b(1080p|720p|480p|4k|uhd|hd)\b',
            r'\b(x264|x265|hevc|h264|h265)\b',
            r'\b(bluray|brrip|webrip|dvdrip|hdrip|hdcam)\b',
            r'\b(aac|ac3|dts|mp3|flac)\b',
            r'\b(10bit|8bit|2ch|5\.1|7\.1)\b',
            r'\b(psa|yts|rarbg|etrg|yify)\b',
            r'\[(.*?)\]',  # Remove anything in brackets
            r'\{(.*?)\}',  # Remove anything in braces
        ]
        
    def normalize_filename(self, filename):
        """Remove noise from filename for better matching"""
        base_name = ospath.splitext(ospath.basename(filename))[0]
        
        # Remove noise patterns
        for pattern in self.noise_patterns:
            base_name = re.sub(pattern, ' ', base_name, flags=re.IGNORECASE)
        
        # Clean up extra spaces and normalize
        base_name = re.sub(r'\s+', ' ', base_name).strip().lower()
        
        return base_name
    
    def extract_tv_info(self, filename):
        """Extract TV show information with enhanced pattern matching"""
        base_name = ospath.splitext(ospath.basename(filename))[0]
        
        for pattern in self.tv_patterns:
            match = re.search(pattern, base_name, re.IGNORECASE)
            if match:
                if len(match.groups()) == 2:
                    season, episode = match.groups()
                    season = int(season) if season.isdigit() else 1
                    episode = int(episode)
                    
                    # Extract show name (text before the episode pattern)
                    show_name = re.split(pattern, base_name, flags=re.IGNORECASE)[0]
                    show_name = self.normalize_filename(show_name)
                    
                    return {
                        'type': 'tv',
                        'season': season,
                        'episode': episode,
                        'show_name': show_name,
                        'episode_code': f"S{season:02d}E{episode:02d}",
                        'normalized_name': show_name
                    }
                elif len(match.groups()) == 1:
                    # Single number patterns (episode only)
                    episode = int(match.group(1))
                    
                    show_name = re.split(pattern, base_name, flags=re.IGNORECASE)[0]
                    show_name = self.normalize_filename(show_name)
                    
                    return {
                        'type': 'tv',
                        'season': 1,  # Default to season 1
                        'episode': episode,
                        'show_name': show_name,
                        'episode_code': f"S01E{episode:02d}",
                        'normalized_name': show_name
                    }
        
        # Check if it's likely a movie
        normalized = self.normalize_filename(filename)
        is_movie = any(indicator in normalized for indicator in self.movie_indicators)
        
        return {
            'type': 'movie' if is_movie else 'unknown',
            'season': None,
            'episode': None,
            'show_name': None,
            'episode_code': None,
            'normalized_name': normalized
        }
    
    def similarity_score(self, str1, str2):
        """Calculate similarity between two strings"""
        return SequenceMatcher(None, str1, str2).ratio()
    
    def find_best_match(self, video_file, subtitle_files, threshold=0.6):
        """Find the best matching subtitle for a video file"""
        video_info = self.extract_tv_info(video_file)
        best_match = None
        best_score = 0
        match_reason = ""
        
        LOGGER.info(f"🎬 Matching video: {ospath.basename(video_file)}")
        LOGGER.info(f"   Type: {video_info['type']}, Info: {video_info}")
        
        for subtitle_file in subtitle_files:
            subtitle_info = self.extract_tv_info(subtitle_file)
            score = 0
            reason = ""
            
            if video_info['type'] == 'tv' and subtitle_info['type'] == 'tv':
                # TV show matching
                if (video_info['season'] == subtitle_info['season'] and 
                    video_info['episode'] == subtitle_info['episode']):
                    # Exact episode match
                    score = 0.9
                    reason = f"Exact Episode Match ({video_info['episode_code']})"
                    
                    # Bonus for show name similarity
                    if video_info['show_name'] and subtitle_info['show_name']:
                        name_similarity = self.similarity_score(
                            video_info['show_name'], 
                            subtitle_info['show_name']
                        )
                        score += name_similarity * 0.1
                        reason += f" + Name similarity ({name_similarity:.2f})"
                
                elif video_info['show_name'] and subtitle_info['show_name']:
                    # Show name similarity without episode match
                    name_similarity = self.similarity_score(
                        video_info['show_name'], 
                        subtitle_info['show_name']
                    )
                    if name_similarity > threshold:
                        score = name_similarity * 0.7
                        reason = f"Show Name Match ({name_similarity:.2f})"
            
            elif video_info['type'] == 'movie' or subtitle_info['type'] == 'movie':
                # Movie matching - use normalized filename similarity
                similarity = self.similarity_score(
                    video_info['normalized_name'], 
                    subtitle_info['normalized_name']
                )
                if similarity > threshold:
                    score = similarity
                    reason = f"Movie Name Match ({similarity:.2f})"
            
            else:
                # General similarity matching for unknown types
                similarity = self.similarity_score(
                    video_info['normalized_name'], 
                    subtitle_info['normalized_name']
                )
                if similarity > threshold:
                    score = similarity * 0.8
                    reason = f"General Similarity ({similarity:.2f})"
            
            # Exact filename match (without extension) - highest priority
            video_base = ospath.splitext(ospath.basename(video_file))[0]
            subtitle_base = ospath.splitext(ospath.basename(subtitle_file))[0]
            if video_base == subtitle_base:
                score = 1.0
                reason = "Exact Filename Match"
            
            if score > best_score:
                best_score = score
                best_match = subtitle_file
                match_reason = reason
        
        if best_match:
            LOGGER.info(f"   ✅ Best match: {ospath.basename(best_match)} (Score: {best_score:.3f}, {match_reason})")
        else:
            LOGGER.warning(f"   ❌ No suitable match found (threshold: {threshold})")
        
        return best_match, best_score, match_reason
    
    def group_by_content(self, video_files, subtitle_files):
        """Group files by content type (movies vs TV shows vs series)"""
        groups = {
            'tv_shows': {},  # {show_name: [(video, subtitle), ...]}
            'movies': [],
            'unknown': []
        }
        
        # Analyze all files
        video_infos = [(f, self.extract_tv_info(f)) for f in video_files]
        subtitle_infos = [(f, self.extract_tv_info(f)) for f in subtitle_files]
        
        # Group TV shows by show name
        for video_file, video_info in video_infos:
            if video_info['type'] == 'tv' and video_info['show_name']:
                show_key = video_info['show_name']
                if show_key not in groups['tv_shows']:
                    groups['tv_shows'][show_key] = []
                groups['tv_shows'][show_key].append((video_file, video_info))
        
        # Match subtitles to TV shows
        for show_name, episodes in groups['tv_shows'].items():
            for i, (video_file, video_info) in enumerate(episodes):
                best_subtitle = None
                best_score = 0
                
                # Find matching subtitles for this show
                for sub_file, sub_info in subtitle_infos:
                    if (sub_info['type'] == 'tv' and 
                        sub_info['season'] == video_info['season'] and
                        sub_info['episode'] == video_info['episode']):
                        
                        # Check show name similarity
                        if sub_info['show_name']:
                            similarity = self.similarity_score(show_name, sub_info['show_name'])
                            if similarity > best_score:
                                best_score = similarity
                                best_subtitle = sub_file
                        else:
                            best_subtitle = sub_file
                            break
                
                # Update with matched subtitle
                groups['tv_shows'][show_name][i] = (video_file, best_subtitle, video_info)
        
        # Handle movies and unknown types
        used_subtitles = set()
        for show_episodes in groups['tv_shows'].values():
            for episode_data in show_episodes:
                if len(episode_data) > 2 and episode_data[1]:  # Has subtitle
                    used_subtitles.add(episode_data[1])
        
        for video_file, video_info in video_infos:
            if video_info['type'] in ['movie', 'unknown']:
                available_subs = [f for f, _ in subtitle_infos if f not in used_subtitles]
                best_match, score, reason = self.find_best_match(video_file, available_subs)
                
                if best_match:
                    used_subtitles.add(best_match)
                    if video_info['type'] == 'movie':
                        groups['movies'].append((video_file, best_match, video_info, reason))
                    else:
                        groups['unknown'].append((video_file, best_match, video_info, reason))
                else:
                    if video_info['type'] == 'movie':
                        groups['movies'].append((video_file, None, video_info, "No match"))
                    else:
                        groups['unknown'].append((video_file, None, video_info, "No match"))
        
        return groups


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
        self.file_matcher = SmartFileMatching()

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

    async def _process_multiple_files_enhanced(self, ffmpeg, f_path, dir, delete_originals):
        """Enhanced multiple file processing with smart content grouping"""
        
        # Get all video and subtitle files
        video_extensions = ['*.mkv', '*.mp4', '*.avi', '*.mov', '*.m4v', '*.webm']
        subtitle_extensions = ['*.srt', '*.ass', '*.ssa', '*.vtt', '*.sub']
        
        video_files = []
        subtitle_files = []
        
        for ext in video_extensions:
            video_files.extend(glob.glob(ospath.join(dir, ext)))
        
        for ext in subtitle_extensions:
            subtitle_files.extend(glob.glob(ospath.join(dir, ext)))
        
        # Sort files for consistency
        video_files.sort()
        subtitle_files.sort()
        
        LOGGER.info(f"🎬 Found {len(video_files)} video files and {len(subtitle_files)} subtitle files")
        
        if not video_files:
            LOGGER.error("❌ No video files found!")
            return False
        
        # Use smart file matcher to group content
        matcher = SmartFileMatching()
        groups = matcher.group_by_content(video_files, subtitle_files)
        
        LOGGER.info(f"📊 Content analysis:")
        LOGGER.info(f"   📺 TV Shows: {len(groups['tv_shows'])} series")
        LOGGER.info(f"   🎭 Movies: {len(groups['movies'])} files")
        LOGGER.info(f"   ❓ Unknown: {len(groups['unknown'])} files")
        
        # Process all matched pairs
        all_pairs = []
        
        # Add TV show episodes
        for show_name, episodes in groups['tv_shows'].items():
            LOGGER.info(f"📺 Processing series: {show_name}")
            for episode_data in episodes:
                if len(episode_data) >= 3:
                    video_file, subtitle_file, video_info = episode_data[:3]
                    if subtitle_file:
                        all_pairs.append((video_file, subtitle_file, f"{show_name}.{video_info['episode_code']}"))
                    else:
                        LOGGER.warning(f"   ⚠️ No subtitle for: {ospath.basename(video_file)}")
        
        # Add movies
        for movie_data in groups['movies']:
            video_file, subtitle_file, video_info, reason = movie_data
            if subtitle_file:
                movie_name = ospath.splitext(ospath.basename(video_file))[0]
                all_pairs.append((video_file, subtitle_file, f"Movie.{movie_name}"))
            else:
                LOGGER.warning(f"   ⚠️ No subtitle for movie: {ospath.basename(video_file)}")
        
        # Add unknown type files
        for unknown_data in groups['unknown']:
            video_file, subtitle_file, video_info, reason = unknown_data
            if subtitle_file:
                file_name = ospath.splitext(ospath.basename(video_file))[0]
                all_pairs.append((video_file, subtitle_file, f"Unknown.{file_name}"))
            else:
                LOGGER.warning(f"   ⚠️ No subtitle for: {ospath.basename(video_file)}")
        
        if not all_pairs:
            LOGGER.error("❌ No matching video-subtitle pairs found!")
            return False
        
        LOGGER.info(f"🎯 Processing {len(all_pairs)} matched pairs...")
        
        # Process each pair
        all_outputs = []
        files_to_delete = []
        
        for i, (video_file, subtitle_file, base_name) in enumerate(all_pairs, 1):
            LOGGER.info(f"🎬 Processing pair {i}/{len(all_pairs)}: {ospath.basename(video_file)} + {ospath.basename(subtitle_file)}")
            
            # Get video duration for progress tracking
            self._total_time = (await get_media_info(video_file))[0]
            
            # Build FFmpeg command for this specific pair
            current_ffmpeg = []
            for item in ffmpeg:
                if item in ['*.mkv', '*.mp4', '*.avi']:
                    current_ffmpeg.append(video_file)
                elif item in ['*.srt', '*.ass', '*.ssa', '*.vtt']:
                    current_ffmpeg.append(subtitle_file)
                elif item.startswith("mltb"):
                    # Generate output filename
                    if item == "mltb.Sub.mkv":
                        output_file = f"{dir}/{base_name}.Sub.mkv"
                    elif item == "mltb.mkv":
                        output_file = f"{dir}/{base_name}.mkv"
                    elif item == "mltb.mp4":
                        output_file = f"{dir}/{base_name}.mp4"
                    else:
                        # Handle custom naming patterns
                        clean_base = base_name.replace('Movie.', '').replace('Unknown.', '')
                        output_file = f"{dir}/{item.replace('mltb', clean_base)}"
                    
                    current_ffmpeg.append(output_file)
                    all_outputs.append(output_file)
                else:
                    current_ffmpeg.append(item)
            
            # Track files for deletion if requested
            if delete_originals:
                files_to_delete.extend([video_file, subtitle_file])
            
            # Check for cancellation
            if self._listener.is_cancelled:
                LOGGER.info("❌ Processing cancelled by user")
                return False
            
            # Execute FFmpeg command
            LOGGER.info(f"   🔄 Processing: {ospath.basename(video_file)}...")
            self._listener.subproc = await create_subprocess_exec(
                *current_ffmpeg, stdout=PIPE, stderr=PIPE
            )
            
            # Monitor progress
            await self._ffmpeg_progress()
            _, stderr = await self._listener.subproc.communicate()
            code = self._listener.subproc.returncode
            
            if self._listener.is_cancelled:
                LOGGER.info("❌ Processing cancelled during execution")
                return False
            
            if code != 0:
                try:
                    stderr = stderr.decode().strip()
                except Exception:
                    stderr = "Unable to decode the error!"
                
                LOGGER.error(f"   ❌ Failed to process {ospath.basename(video_file)}: {stderr}")
                
                # Clean up any partial outputs
                for output in all_outputs:
                    if await aiopath.exists(output):
                        await remove(output)
                        LOGGER.info(f"   🗑️ Cleaned up partial output: {ospath.basename(output)}")
                
                return False
            
            LOGGER.info(f"   ✅ Successfully processed: {ospath.basename(video_file)}")
        
        # Delete original files if requested
        if delete_originals:
            LOGGER.info("🗑️ Deleting original files...")
            for file_to_delete in files_to_delete:
                try:
                    if await aiopath.exists(file_to_delete):
                        await remove(file_to_delete)
                        LOGGER.info(f"   ✅ Deleted: {ospath.basename(file_to_delete)}")
                except Exception as e:
                    LOGGER.error(f"   ❌ Failed to delete {ospath.basename(file_to_delete)}: {e}")
        
        LOGGER.info(f"🎉 Successfully processed {len(all_pairs)} video-subtitle pairs!")
        return all_outputs

    async def _process_single_file_enhanced(self, ffmpeg, f_path, dir, base_name, ext, delete_originals):
        """Enhanced single file processing with smart subtitle matching"""
        
        self._total_time = (await get_media_info(f_path))[0]
        
        # Handle wildcards and smart subtitle matching
        expanded_ffmpeg = []
        input_files = []
        matcher = SmartFileMatching()
        
        for i, item in enumerate(ffmpeg):
            if '*' in item and not item.startswith('mltb'):
                # Handle different wildcard patterns
                if item in ['*.srt', '*.ass', '*.ssa', '*.vtt']:
                    # Smart subtitle matching for single file processing
                    subtitle_files = []
                    for ext_pattern in ['*.srt', '*.ass', '*.ssa', '*.vtt', '*.sub']:
                        subtitle_files.extend(glob.glob(ospath.join(dir, ext_pattern)))
                    
                    if subtitle_files:
                        best_match, score, reason = matcher.find_best_match(f_path, subtitle_files)
                        
                        if best_match:
                            LOGGER.info(f"🎯 Selected subtitle: {ospath.basename(best_match)} ({reason})")
                            expanded_ffmpeg.append(best_match)
                            if i > 0 and ffmpeg[i-1] == "-i":
                                input_files.append(best_match)
                        else:
                            LOGGER.warning(f"⚠️ No suitable subtitle found for: {ospath.basename(f_path)}")
                            expanded_ffmpeg.append(item)  # Keep original wildcard
                    else:
                        expanded_ffmpeg.append(item)
                        
                elif item in ['*.mkv', '*.mp4', '*.avi', '*.mov', '*.m4v', '*.webm']:
                    # Handle video wildcards
                    wildcard_pattern = ospath.join(dir, item)
                    matches = glob.glob(wildcard_pattern)
                    
                    if matches:
                        # Use the current file if it matches, otherwise use first match
                        if f_path in matches:
                            expanded_file = f_path
                        else:
                            expanded_file = matches[0]
                        
                        expanded_ffmpeg.append(expanded_file)
                        if i > 0 and ffmpeg[i-1] == "-i":
                            input_files.append(expanded_file)
                    else:
                        expanded_ffmpeg.append(item)
                else:
                    # Handle other wildcards normally
                    wildcard_pattern = ospath.join(dir, item)
                    matches = glob.glob(wildcard_pattern)
                    
                    if matches:
                        expanded_ffmpeg.append(matches[0])
                        if i > 0 and ffmpeg[i-1] == "-i":
                            input_files.append(matches[0])
                    else:
                        expanded_ffmpeg.append(item)
            else:
                expanded_ffmpeg.append(item)
        
        ffmpeg = expanded_ffmpeg
        
        # Find output placeholders and generate output files
        outputs = []
        for index, item in enumerate(ffmpeg):
            if item.startswith("mltb") and (index == 0 or ffmpeg[index-1] != "-i"):
                if item != "mltb" and item.startswith("mltb"):
                    if "." in item:
                        output = f"{dir}/{item.replace('mltb', base_name)}"
                    else:
                        output = f"{dir}/{item.replace('mltb', base_name)}{ext}"
                else:
                    output = f"{dir}/{base_name}{ext}"
                
                outputs.append(output)
                ffmpeg[index] = output
        
        # Log the final command
        cmd_preview = ' '.join([ospath.basename(x) if '/' in x else x for x in ffmpeg[:10]])
        LOGGER.info(f"🎬 Executing: {cmd_preview}{'...' if len(ffmpeg) > 10 else ''}")
        
        if self._listener.is_cancelled:
            return False
        
        # Execute FFmpeg
        self._listener.subproc = await create_subprocess_exec(
            *ffmpeg, stdout=PIPE, stderr=PIPE
        )
        await self._ffmpeg_progress()
        _, stderr = await self._listener.subproc.communicate()
        code = self._listener.subproc.returncode
        
        if self._listener.is_cancelled:
            return False
        
        if code == 0:
            # Delete original files if requested
            if delete_originals:
                if f_path not in input_files:
                    input_files.append(f_path)
                
                for input_file in input_files:
                    try:
                        if await aiopath.exists(input_file):
                            await remove(input_file)
                            LOGGER.info(f"🗑️ Deleted original: {ospath.basename(input_file)}")
                    except Exception as e:
                        LOGGER.error(f"❌ Failed to delete {ospath.basename(input_file)}: {e}")
            
            LOGGER.info(f"✅ Successfully processed: {ospath.basename(f_path)}")
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

    async def ffmpeg_cmds(self, ffmpeg, f_path):
        """Main entry point for FFmpeg processing with enhanced smart matching"""
        self.clear()
        base_name, ext = ospath.splitext(f_path)
        dir, base_name = base_name.rsplit("/", 1)
        
        # Check for -del flag
        delete_originals = False
        if "-del" in ffmpeg:
            delete_originals = True
            ffmpeg = [item for item in ffmpeg if item != "-del"]
        
        # Check if we're using wildcards for multiple file processing
        video_wildcards = ['*.mkv', '*.mp4', '*.avi', '*.mov', '*.m4v', '*.webm']
        subtitle_wildcards = ['*.srt', '*.ass', '*.ssa', '*.vtt', '*.sub']
        
        has_video_wildcard = any(wildcard in ffmpeg for wildcard in video_wildcards)
        has_subtitle_wildcard = any(wildcard in ffmpeg for wildcard in subtitle_wildcards)
        
        if has_video_wildcard and has_subtitle_wildcard:
            LOGGER.info("🎬 Multiple file processing mode with smart content grouping")
            return await self._process_multiple_files_enhanced(ffmpeg, f_path, dir, delete_originals)
        else:
            LOGGER.info("🎯 Single file processing mode with smart subtitle matching")
            return await self._process_single_file_enhanced(ffmpeg, f_path, dir, base_name, ext, delete_originals)

    # Keep all the existing methods unchanged
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