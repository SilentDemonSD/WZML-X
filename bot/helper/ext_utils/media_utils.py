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
        
        # Supported formats
        self.video_formats = {
            'mp4', 'mkv', 'avi', 'mov', 'wmv', 'flv', 'webm', 'm4v', 
            '3gp', 'mpg', 'mpeg', 'ts', 'vob', 'asf', 'rm', 'rmvb', 
            'ogv', 'divx', 'xvid', 'f4v', 'mts', 'm2ts', 'mod', 'tod'
        }
        
        self.subtitle_formats = {
            'srt', 'ass', 'ssa', 'vtt', 'sub', 'idx', 'smi', 'rt', 
            'txt', 'usf', 'jss', 'psb', 'pjs', 'mpl2', 'ttml', 'dfxp',
            'sbv', 'lrc', 'cap', 'scc', 'stl', 'xml', 'itt'
        }
        
        self.audio_formats = {
            'mp3', 'flac', 'aac', 'ogg', 'wma', 'wav', 'ape', 'm4a',
            'opus', 'ac3', 'dts', 'amr', 'ra', 'au', 'aiff', '3ga'
        }

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

    def _detect_file_type(self, file_path):
        """Detect if file is video, audio, or subtitle based on extension"""
        ext = ospath.splitext(file_path)[1][1:].lower()
        if ext in self.video_formats:
            return 'video'
        elif ext in self.audio_formats:
            return 'audio'
        elif ext in self.subtitle_formats:
            return 'subtitle'
        return 'unknown'

    def _extract_episode_info(self, filename):
        """Extract season and episode numbers from various filename patterns."""
        import re
        
        # Remove file extension
        base_name = ospath.splitext(ospath.basename(filename))[0]
        
        # Multiple patterns for different naming conventions
        patterns = [
            r'S(\d{1,2})E(\d{1,2})',  # S01E01
            r'Season\s*(\d+).*Episode\s*(\d+)',  # Season 1 Episode 1
            r'(\d{1,2})x(\d{1,2})',  # 1x01
            r'\.(\d{1,2})(\d{2})\.',  # .101. (season 1, episode 1)
            r'[^\d](\d{1,2})(\d{2})[^\d]',  # non-digit + 101 + non-digit
        ]
        
        for pattern in patterns:
            match = re.search(pattern, base_name, re.IGNORECASE)
            if match:
                season = int(match.group(1))
                episode = int(match.group(2))
                return season, episode, f"S{season:02d}E{episode:02d}"
        
        return None, None, None

    def _get_all_media_files(self, directory, file_types):
        """Get all media files of specified types from directory"""
        all_files = []
        for file_type in file_types:
            if file_type == 'video':
                for ext in self.video_formats:
                    all_files.extend(glob.glob(ospath.join(directory, f"*.{ext}")))
            elif file_type == 'subtitle':
                for ext in self.subtitle_formats:
                    all_files.extend(glob.glob(ospath.join(directory, f"*.{ext}")))
            elif file_type == 'audio':
                for ext in self.audio_formats:
                    all_files.extend(glob.glob(ospath.join(directory, f"*.{ext}")))
        
        return sorted(all_files)

    def _smart_file_matching(self, primary_files, secondary_files, match_type="subtitle"):
        """Enhanced file matching with multiple strategies"""
        matched_pairs = []
        used_secondary = set()
        
        LOGGER.info(f"🔍 Starting {match_type} matching for {len(primary_files)} primary files")
        
        for primary_file in primary_files:
            primary_base = ospath.splitext(ospath.basename(primary_file))[0]
            primary_season, primary_episode, primary_code = self._extract_episode_info(primary_file)
            
            best_match = None
            match_score = 0
            match_reason = ""
            
            for secondary_file in secondary_files:
                if secondary_file in used_secondary:
                    continue
                
                secondary_base = ospath.splitext(ospath.basename(secondary_file))[0]
                secondary_season, secondary_episode, secondary_code = self._extract_episode_info(secondary_file)
                
                current_score = 0
                current_reason = ""
                
                # Score 1: Exact episode match (highest priority)
                if (primary_season and primary_episode and 
                    secondary_season == primary_season and secondary_episode == primary_episode):
                    current_score = 100
                    current_reason = f"Episode Match ({primary_code})"
                
                # Score 2: Exact filename match
                elif primary_base == secondary_base:
                    current_score = 90
                    current_reason = "Exact Filename Match"
                
                # Score 3: Normalized filename match
                else:
                    import re
                    # Remove quality indicators and normalize
                    primary_norm = re.sub(
                        r'\s*(1080p|720p|480p|x264|x265|HEVC|BluRay|WEBRip|WEB-DL|HDTV|10bit|2CH|PSA|JAPANESE|HINDI|ENGLISH).*', 
                        '', primary_base, flags=re.IGNORECASE
                    ).strip()
                    secondary_norm = re.sub(
                        r'\s*(1080p|720p|480p|x264|x265|HEVC|BluRay|WEBRip|WEB-DL|HDTV|10bit|2CH|PSA|JAPANESE|HINDI|ENGLISH).*', 
                        '', secondary_base, flags=re.IGNORECASE
                    ).strip()
                    
                    if primary_norm and secondary_norm and primary_norm == secondary_norm:
                        current_score = 80
                        current_reason = "Normalized Name Match"
                    
                    # Score 4: Partial name match
                    elif primary_norm and secondary_norm:
                        if primary_norm in secondary_norm or secondary_norm in primary_norm:
                            current_score = 60
                            current_reason = "Partial Name Match"
                
                if current_score > match_score:
                    match_score = current_score
                    best_match = secondary_file
                    match_reason = current_reason
            
            if best_match and match_score >= 60:  # Minimum acceptable score
                matched_pairs.append((primary_file, best_match, match_reason))
                used_secondary.add(best_match)
                LOGGER.info(f"   ✅ {match_reason}: {ospath.basename(primary_file)} ↔ {ospath.basename(best_match)}")
            else:
                LOGGER.warning(f"   ❌ No {match_type} match for: {ospath.basename(primary_file)}")
        
        return matched_pairs

    def _expand_wildcards_smart(self, ffmpeg_cmd, directory, primary_file=None):
        """Smart wildcard expansion with comprehensive format support"""
        expanded_cmd = []
        
        for item in ffmpeg_cmd:
            if '*' in item and not item.startswith('mltb'):
                # Handle different wildcard patterns
                if item in ['*.vid', '*.video']:
                    # Get all video files
                    matches = self._get_all_media_files(directory, ['video'])
                elif item in ['*.sub', '*.subtitle', '*.srt']:
                    # Get all subtitle files
                    matches = self._get_all_media_files(directory, ['subtitle'])
                elif item in ['*.aud', '*.audio']:
                    # Get all audio files
                    matches = self._get_all_media_files(directory, ['audio'])
                elif item.startswith('*.'):
                    # Specific extension wildcard
                    ext = item[2:]
                    matches = glob.glob(ospath.join(directory, f"*.{ext}"))
                else:
                    # Generic wildcard
                    matches = glob.glob(ospath.join(directory, item))
                
                if matches:
                    # If we have a primary file and this is a subtitle wildcard, do smart matching
                    if primary_file and item in ['*.sub', '*.subtitle', '*.srt']:
                        matched_pairs = self._smart_file_matching([primary_file], matches, "subtitle")
                        if matched_pairs:
                            expanded_cmd.append(matched_pairs[0][1])  # Use the matched subtitle
                        else:
                            expanded_cmd.append(matches[0])  # Fallback to first match
                    else:
                        expanded_cmd.append(matches[0])  # Use first match for other cases
                else:
                    expanded_cmd.append(item)  # Keep original if no matches
            else:
                expanded_cmd.append(item)
        
        return expanded_cmd

    async def _process_batch_files(self, ffmpeg_cmd, directory, delete_originals=False):
        """Process multiple video-subtitle pairs in batch mode"""
        
        # Get all video and subtitle files
        video_files = self._get_all_media_files(directory, ['video'])
        subtitle_files = self._get_all_media_files(directory, ['subtitle'])
        
        if not video_files:
            LOGGER.error("❌ No video files found for batch processing!")
            return False
        
        LOGGER.info(f"📁 Batch processing: {len(video_files)} videos, {len(subtitle_files)} subtitles")
        
        # Create video-subtitle pairs
        if subtitle_files:
            file_pairs = self._smart_file_matching(video_files, subtitle_files, "subtitle")
        else:
            # Process videos without subtitles
            file_pairs = [(video, None, "No Subtitle") for video in video_files]
        
        if not file_pairs:
            LOGGER.error("❌ No valid file pairs created!")
            return False
        
        LOGGER.info(f"🎬 Processing {len(file_pairs)} file pairs...")
        
        all_outputs = []
        files_to_delete = []
        
        for i, (video_file, subtitle_file, match_reason) in enumerate(file_pairs, 1):
            LOGGER.info(f"🎯 Processing {i}/{len(file_pairs)}: {ospath.basename(video_file)} ({match_reason})")
            
            # Get video duration for progress tracking
            self._total_time = (await get_media_info(video_file))[0]
            
            # Build command for this specific pair
            current_cmd = []
            base_name = ospath.splitext(ospath.basename(video_file))[0]
            
            for item in ffmpeg_cmd:
                if item in ['*.vid', '*.video', '*.mkv', '*.mp4']:
                    current_cmd.append(video_file)
                elif item in ['*.sub', '*.subtitle', '*.srt'] and subtitle_file:
                    current_cmd.append(subtitle_file)
                elif item in ['*.sub', '*.subtitle', '*.srt'] and not subtitle_file:
                    # Skip subtitle-related parameters if no subtitle
                    continue
                elif item.startswith('mltb'):
                    # Generate output filename
                    if '.' in item:
                        output_ext = item.split('.')[-1]
                        output_file = f"{directory}/{base_name}.{output_ext}"
                    else:
                        # Preserve original extension
                        output_file = f"{directory}/{base_name}{ospath.splitext(video_file)[1]}"
                    
                    current_cmd.append(output_file)
                    all_outputs.append(output_file)
                else:
                    current_cmd.append(item)
            
            # Track files for deletion
            if delete_originals:
                files_to_delete.append(video_file)
                if subtitle_file:
                    files_to_delete.append(subtitle_file)
            
            # Check for cancellation
            if self._listener.is_cancelled:
                LOGGER.info("❌ Batch processing cancelled")
                return False
            
            # Execute FFmpeg command
            LOGGER.info(f"   🔄 Executing FFmpeg...")
            self._listener.subproc = await create_subprocess_exec(
                *current_cmd, stdout=PIPE, stderr=PIPE
            )
            
            await self._ffmpeg_progress()
            _, stderr = await self._listener.subproc.communicate()
            code = self._listener.subproc.returncode
            
            if self._listener.is_cancelled:
                return False
            
            if code != 0:
                try:
                    stderr = stderr.decode().strip()
                except:
                    stderr = "Unable to decode error"
                
                LOGGER.error(f"   ❌ Failed to process {ospath.basename(video_file)}: {stderr}")
                
                # Clean up partial outputs
                for output in all_outputs:
                    if await aiopath.exists(output):
                        await remove(output)
                        LOGGER.info(f"   🗑️  Cleaned up: {ospath.basename(output)}")
                
                return False
            
            LOGGER.info(f"   ✅ Success: {ospath.basename(video_file)}")
        
        # Delete original files if requested
        if delete_originals and files_to_delete:
            LOGGER.info("🗑️  Deleting original files...")
            for file_path in files_to_delete:
                try:
                    if await aiopath.exists(file_path):
                        await remove(file_path)
                        LOGGER.info(f"   ✅ Deleted: {ospath.basename(file_path)}")
                except Exception as e:
                    LOGGER.error(f"   ❌ Failed to delete {ospath.basename(file_path)}: {e}")
        
        LOGGER.info(f"🎉 Batch processing complete! Processed {len(file_pairs)} files")
        return all_outputs

    async def _process_single_enhanced(self, ffmpeg_cmd, f_path, directory, base_name, ext, delete_originals=False):
        """Enhanced single file processing with comprehensive format support"""
        
        self._total_time = (await get_media_info(f_path))[0]
        
        # Smart wildcard expansion
        expanded_cmd = self._expand_wildcards_smart(ffmpeg_cmd, directory, f_path)
        
        # Find inputs and outputs
        input_files = []
        outputs = []
        
        for i, item in enumerate(expanded_cmd):
            # Track input files (after -i flag)
            if i > 0 and expanded_cmd[i-1] == "-i":
                input_files.append(item)
            
            # Handle output placeholders
            elif item.startswith("mltb") and (i == 0 or expanded_cmd[i-1] != "-i"):
                if item != "mltb" and "." in item:
                    # Extract extension from placeholder
                    if item.startswith("mltb."):
                        output_ext = item[5:]  # Remove "mltb."
                        output = f"{directory}/{base_name}.{output_ext}"
                    else:
                        output = f"{directory}/{item.replace('mltb', base_name)}"
                else:
                    output = f"{directory}/{base_name}{ext}"
                
                outputs.append(output)
                expanded_cmd[i] = output
        
        # Log command preview
        cmd_preview = ' '.join([ospath.basename(x) if '/' in x else x for x in expanded_cmd[:15]])
        LOGGER.info(f"🎬 Executing: {cmd_preview}{'...' if len(expanded_cmd) > 15 else ''}")
        
        if self._listener.is_cancelled:
            return False
        
        # Execute FFmpeg
        self._listener.subproc = await create_subprocess_exec(
            *expanded_cmd, stdout=PIPE, stderr=PIPE
        )
        await self._ffmpeg_progress()
        _, stderr = await self._listener.subproc.communicate()
        code = self._listener.subproc.returncode
        
        if self._listener.is_cancelled:
            return False
        
        if code == 0:
            # Delete original files if requested
            if delete_originals:
                # Add primary file to deletion list if not already in inputs
                if f_path not in input_files:
                    input_files.append(f_path)
                
                for input_file in input_files:
                    try:
                        if await aiopath.exists(input_file):
                            await remove(input_file)
                            LOGGER.info(f"🗑️  Deleted: {ospath.basename(input_file)}")
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
            except:
                stderr = "Unable to decode error"
            
            LOGGER.error(f"❌ FFmpeg error: {stderr}")
            LOGGER.error(f"   File: {f_path}")
            
            # Clean up failed outputs
            for output in outputs:
                if await aiopath.exists(output):
                    await remove(output)
            
            return False

    def _detect_batch_mode(self, ffmpeg_cmd):
        """Detect if we should use batch processing mode"""
        video_wildcards = ['*.vid', '*.video', '*.mkv', '*.mp4']
        subtitle_wildcards = ['*.sub', '*.subtitle', '*.srt']
        
        has_video_wildcard = any(item in ffmpeg_cmd for item in video_wildcards)
        has_subtitle_wildcard = any(item in ffmpeg_cmd for item in subtitle_wildcards)
        
        return has_video_wildcard and has_subtitle_wildcard

    async def ffmpeg_cmds(self, ffmpeg_cmd, f_path):
        """Enhanced FFmpeg command processor with comprehensive format support"""
        self.clear()
        base_name, ext = ospath.splitext(f_path)
        directory, base_name = base_name.rsplit("/", 1)
        
        # Check for deletion flag
        delete_originals = False
        if "-del" in ffmpeg_cmd:
            delete_originals = True
            ffmpeg_cmd = [item for item in ffmpeg_cmd if item != "-del"]
        
        LOGGER.info(f"🎯 Processing: {ospath.basename(f_path)}")
        LOGGER.info(f"   Directory: {directory}")
        LOGGER.info(f"   Delete originals: {delete_originals}")
        
        # Detect processing mode
        if self._detect_batch_mode(ffmpeg_cmd):
            LOGGER.info("🎬 Batch processing mode detected")
            return await self._process_batch_files(ffmpeg_cmd, directory, delete_originals)
        else:
            LOGGER.info("🎯 Single file processing mode")
            return await self._process_single_enhanced(ffmpeg_cmd, f_path, directory, base_name, ext, delete_originals)

    async def convert_video(self, video_file, ext, retry=False):
        """Enhanced video conversion with better format support"""
        self.clear()
        self._total_time = (await get_media_info(video_file))[0]
        base_name = ospath.splitext(video_file)[0]
        output = f"{base_name}.{ext}"
        
        # Determine best codec based on output format
        video_codec = "libx264"
        audio_codec = "aac"
        subtitle_codec = "copy"
        
        if ext.lower() == "mp4":
            subtitle_codec = "mov_text"
        elif ext.lower() == "mkv":
            subtitle_codec = "ass"
        elif ext.lower() == "webm":
            video_codec = "libvpx-vp9"
            audio_codec = "libopus"
        
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
                video_codec,
                "-c:a",
                audio_codec,
                "-c:s",
                subtitle_codec,
                "-threads",
                f"{max(1, cpu_no // 2)}",
                output,
            ]
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
                LOGGER.warning(f"Copy failed, retrying with re-encoding for: {video_file}")
                return await self.convert_video(video_file, ext, True)
            
            try:
                stderr = stderr.decode().strip()
            except:
                stderr = "Unable to decode error"
            LOGGER.error(f"Video conversion failed: {stderr}")
            LOGGER.error(f"File: {video_file}")
            return False

    async def convert_audio(self, audio_file, ext):
        """Enhanced audio conversion with better format support"""
        self.clear()
        self._total_time = (await get_media_info(audio_file))[0]
        base_name = ospath.splitext(audio_file)[0]
        output = f"{base_name}.{ext}"
        
        # Determine best codec and quality based on output format
        codec_params = []
        if ext.lower() == "mp3":
            codec_params = ["-c:a", "libmp3lame", "-b:a", "192k"]
        elif ext.lower() == "aac":
            codec_params = ["-c:a", "aac", "-b:a", "128k"]
        elif ext.lower() == "ogg":
            codec_params = ["-c:a", "libvorbis", "-q:a", "5"]
        elif ext.lower() == "opus":
            codec_params = ["-c:a", "libopus", "-b:a", "96k"]
        elif ext.lower() == "flac":
            codec_params = ["-c:a", "flac"]
        elif ext.lower() == "wav":
            codec_params = ["-c:a", "pcm_s16le"]
        
        cmd = [
            BinConfig.FFMPEG_NAME,
            "-hide_banner",
            "-loglevel",
            "error",
            "-progress",
            "pipe:1",
            "-i",
            audio_file,
        ] + codec_params + [
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
            except:
                stderr = "Unable to decode error"
            LOGGER.error(f"Audio conversion failed: {stderr}")
            LOGGER.error(f"File: {audio_file}")
            if await aiopath.exists(output):
                await remove(output)
            return False

    async def extract_subtitles(self, video_file, output_dir=None):
        """Extract all subtitle streams from video file"""
        if output_dir is None:
            output_dir = ospath.dirname(video_file)
        
        base_name = ospath.splitext(ospath.basename(video_file))[0]
        
        # Get stream information
        streams = await get_streams(video_file)
        if not streams:
            LOGGER.error(f"Could not get stream info for: {video_file}")
            return False
        
        subtitle_streams = [s for s in streams if s.get("codec_type") == "subtitle"]
        if not subtitle_streams:
            LOGGER.info(f"No subtitle streams found in: {video_file}")
            return False
        
        LOGGER.info(f"Found {len(subtitle_streams)} subtitle streams in: {ospath.basename(video_file)}")
        
        extracted_files = []
        
        for i, stream in enumerate(subtitle_streams):
            # Get language and title info
            tags = stream.get("tags", {})
            language = tags.get("language", f"track{i}")
            title = tags.get("title", "")
            
            # Determine output format based on codec
            codec_name = stream.get("codec_name", "").lower()
            if codec_name in ["ass", "ssa"]:
                ext = "ass"
            elif codec_name == "subrip":
                ext = "srt"
            elif codec_name == "webvtt":
                ext = "vtt"
            else:
                ext = "srt"  # Default fallback
            
            # Create output filename
            if title:
                output_file = f"{output_dir}/{base_name}.{language}.{title}.{ext}"
            else:
                output_file = f"{output_dir}/{base_name}.{language}.{ext}"
            
            # Extract subtitle
            cmd = [
                BinConfig.FFMPEG_NAME,
                "-hide_banner",
                "-loglevel",
                "error",
                "-i",
                video_file,
                "-map",
                f"0:s:{i}",
                "-c",
                "copy",
                output_file,
            ]
            
            try:
                result = await cmd_exec(cmd)
                if result[2] == 0:
                    extracted_files.append(output_file)
                    LOGGER.info(f"   ✅ Extracted: {ospath.basename(output_file)}")
                else:
                    LOGGER.error(f"   ❌ Failed to extract subtitle {i}: {result[1]}")
            except Exception as e:
                LOGGER.error(f"   ❌ Error extracting subtitle {i}: {e}")
        
        return extracted_files if extracted_files else False

    async def merge_subtitles(self, video_file, subtitle_files, output_file=None, languages=None):
        """Merge multiple subtitle files into video"""
        if output_file is None:
            base_name = ospath.splitext(video_file)[0]
            output_file = f"{base_name}.merged.mkv"
        
        # Build command
        cmd = [
            BinConfig.FFMPEG_NAME,
            "-hide_banner",
            "-loglevel",
            "error",
            "-progress",
            "pipe:1",
            "-i",
            video_file,
        ]
        
        # Add subtitle inputs
        for sub_file in subtitle_files:
            cmd.extend(["-i", sub_file])
        
        # Map video and audio from first input
        cmd.extend(["-map", "0:v", "-map", "0:a"])
        
        # Map subtitle streams and set metadata
        for i, sub_file in enumerate(subtitle_files, 1):
            cmd.extend(["-map", f"{i}:0"])
            
            # Set language if provided
            if languages and i-1 < len(languages):
                cmd.extend([f"-metadata:s:s:{i-1}", f"language={languages[i-1]}"])
        
        # Copy video/audio, convert subtitles
        cmd.extend(["-c:v", "copy", "-c:a", "copy", "-c:s", "ass"])
        cmd.extend(["-threads", f"{max(1, cpu_no // 2)}", output_file])
        
        self.clear()
        self._total_time = (await get_media_info(video_file))[0]
        
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
            LOGGER.info(f"✅ Successfully merged subtitles: {ospath.basename(output_file)}")
            return output_file
        else:
            try:
                stderr = stderr.decode().strip()
            except:
                stderr = "Unable to decode error"
            LOGGER.error(f"❌ Subtitle merge failed: {stderr}")
            if await aiopath.exists(output_file):
                await remove(output_file)
            return False

    async def sample_video(self, video_file, sample_duration, part_duration):
        """Enhanced video sampling with better quality"""
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
            "-crf",
            "23",
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
            except:
                stderr = "Unable to decode error"
            LOGGER.error(f"Sample creation failed: {stderr}")
            LOGGER.error(f"File: {video_file}")
            if await aiopath.exists(output_file):
                await remove(output_file)
            return False

    async def split(self, f_path, file_, parts, split_size):
        """Enhanced video splitting with better stream handling"""
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
                "-avoid_negative_ts",
                "make_zero",
                "-threads",
                f"{max(1, cpu_no // 2)}",
                out_path,
            ]
            
            if not multi_streams:
                # Remove -map 0 if it's causing issues
                cmd.remove("-map")
                cmd.remove("0")
            
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
                except:
                    stderr = "Unable to decode error"
                
                with suppress(Exception):
                    await remove(out_path)
                
                if multi_streams:
                    LOGGER.warning(f"Multi-stream mapping failed, retrying with single stream. Error: {stderr}")
                    multi_streams = False
                    continue
                else:
                    LOGGER.warning(f"Split failed: {stderr}")
                    LOGGER.warning(f"File will be uploaded as-is if under size limit: {f_path}")
                    return False
            
            out_size = await aiopath.getsize(out_path)
            if out_size > self._listener.max_split_size:
                split_size -= (out_size - self._listener.max_split_size) + 5000000
                LOGGER.warning(f"Part size {out_size} too large, retrying with smaller split size")
                await remove(out_path)
                continue
            
            lpd = (await get_media_info(out_path))[0]
            if lpd == 0:
                LOGGER.error(f"Split resulted in corrupted file: {f_path}")
                break
            elif duration == lpd:
                LOGGER.warning(f"Split produced full duration (stream issue): {f_path}")
                break
            elif lpd <= 3:
                await remove(out_path)
                break
            
            self._last_processed_time += lpd
            self._last_processed_bytes += out_size
            start_time += lpd - 3
            i += 1
        
        return True