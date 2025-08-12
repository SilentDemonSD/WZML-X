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

    def _extract_episode_info(self, filename):
        """Extract season and episode numbers from various filename patterns."""
        import re
        
        # Remove file extension
        base_name = ospath.splitext(ospath.basename(filename))[0]
        
        # Multiple patterns for different episode naming conventions
        patterns = [
            # S##E## format (most common)
            r'S(\d{1,2})E(\d{1,2})',
            # Season ## Episode ## format
            r'Season\s*(\d{1,2})\s*Episode\s*(\d{1,2})',
            # ##x## format
            r'(\d{1,2})x(\d{1,2})',
            # S##.E## or S##_E##
            r'S(\d{1,2})[.\-_]E(\d{1,2})',
            # Episode only (assuming season 1)
            r'(?:Episode|Ep|E)[\s\-_]*(\d{1,3})',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, base_name, re.IGNORECASE)
            if match:
                if len(match.groups()) == 2:
                    season = int(match.group(1))
                    episode = int(match.group(2))
                    return season, episode, f"S{season:02d}E{episode:02d}"
                else:
                    # Episode only pattern - assume season 1
                    episode = int(match.group(1))
                    return 1, episode, f"S01E{episode:02d}"
        
        return None, None, None

    def _get_all_media_files(self, dir_path, file_type):
        """Get all video or subtitle files regardless of extension."""
        import glob
        
        if file_type == "video":
            extensions = ['mkv', 'mp4', 'avi', 'mov', 'wmv', 'flv', 'webm', 'm4v', '3gp', 'ogv', 'ts', 'm2ts', 'mts']
        elif file_type == "subtitle":
            extensions = ['srt', 'ass', 'ssa', 'vtt', 'sub', 'idx', 'sup', 'usf', 'ssf']
        else:
            return []
        
        files = []
        for ext in extensions:
            files.extend(glob.glob(ospath.join(dir_path, f"*.{ext}")))
        
        return sorted(files)

    def _find_matching_files(self, dir_path, video_extensions=None, subtitle_extensions=None):
        """Find and match video files with their corresponding subtitles."""
        import glob
        
        # Get all video and subtitle files
        if video_extensions is None:
            video_files = self._get_all_media_files(dir_path, "video")
        else:
            video_files = []
            for ext in video_extensions:
                video_files.extend(glob.glob(ospath.join(dir_path, f"*.{ext}")))
        
        if subtitle_extensions is None:
            subtitle_files = self._get_all_media_files(dir_path, "subtitle")
        else:
            subtitle_files = []
            for ext in subtitle_extensions:
                subtitle_files.extend(glob.glob(ospath.join(dir_path, f"*.{ext}")))
        
        # Sort files for consistent processing
        video_files.sort()
        subtitle_files.sort()
        
        LOGGER.info(f"📁 Found {len(video_files)} video files and {len(subtitle_files)} subtitle files")
        
        # Match videos with subtitles
        matched_pairs = []
        used_subtitles = set()
        
        for video_file in video_files:
            best_subtitle = self._find_best_subtitle_match(video_file, subtitle_files, used_subtitles)
            
            video_base = ospath.splitext(ospath.basename(video_file))[0]
            
            if best_subtitle:
                matched_pairs.append((video_file, best_subtitle, video_base))
                used_subtitles.add(best_subtitle)
                LOGGER.info(f"   ✅ Paired: {ospath.basename(video_file)} ↔ {ospath.basename(best_subtitle)}")
            else:
                # Video without subtitle
                matched_pairs.append((video_file, None, video_base))
                LOGGER.info(f"   📹 Video only: {ospath.basename(video_file)}")
        
        return matched_pairs

    def _find_best_subtitle_match(self, video_file, subtitle_files, used_subtitles):
        """Find the best matching subtitle for a video file using comprehensive matching."""
        video_season, video_episode, video_code = self._extract_episode_info(video_file)
        video_base = ospath.splitext(ospath.basename(video_file))[0]
        
        available_subtitles = [sub for sub in subtitle_files if sub not in used_subtitles]
        
        if not available_subtitles:
            return None
        
        LOGGER.info(f"🔍 Finding subtitle for: {ospath.basename(video_file)}")
        if video_season and video_episode:
            LOGGER.info(f"   Video info: Season {video_season}, Episode {video_episode} ({video_code})")
        
        # Priority 1: Exact season/episode match
        if video_season and video_episode:
            for sub_file in available_subtitles:
                sub_season, sub_episode, sub_code = self._extract_episode_info(sub_file)
                
                if sub_season == video_season and sub_episode == video_episode:
                    LOGGER.info(f"   ✅ Season/Episode Match: {ospath.basename(sub_file)} ({sub_code})")
                    return sub_file
        
        # Priority 2: Exact filename match (without extension)
        for sub_file in available_subtitles:
            sub_base = ospath.splitext(ospath.basename(sub_file))[0]
            if video_base == sub_base:
                LOGGER.info(f"   ✅ Exact Filename Match: {ospath.basename(sub_file)}")
                return sub_file
        
        # Priority 3: Normalized name matching (remove quality/encoding info)
        import re
        video_normalized = re.sub(
            r'\s*(1080p|720p|480p|2160p|4K|x264|x265|h264|h265|HEVC|AVC|BluRay|BDRip|WEBRip|WEB-DL|HDTV|DVDRip|10bit|8bit|2CH|5\.1|AAC|DTS|JAPANESE|ENGLISH).*', 
            '', 
            video_base, 
            flags=re.IGNORECASE
        ).strip()
        
        if video_normalized:
            for sub_file in available_subtitles:
                sub_base = ospath.splitext(ospath.basename(sub_file))[0]
                sub_normalized = re.sub(
                    r'\s*(1080p|720p|480p|2160p|4K|x264|x265|h264|h265|HEVC|AVC|BluRay|BDRip|WEBRip|WEB-DL|HDTV|DVDRip|10bit|8bit|2CH|5\.1|AAC|DTS|JAPANESE|ENGLISH).*', 
                    '', 
                    sub_base, 
                    flags=re.IGNORECASE
                ).strip()
                
                if sub_normalized and video_normalized == sub_normalized:
                    LOGGER.info(f"   ✅ Normalized Name Match: {ospath.basename(sub_file)}")
                    return sub_file
        
        # Priority 4: Partial name matching (substring)
        for sub_file in available_subtitles:
            sub_base = ospath.splitext(ospath.basename(sub_file))[0].lower()
            video_base_lower = video_base.lower()
            
            if len(video_base_lower) > 10 and len(sub_base) > 10:  # Only for longer names
                if video_base_lower[:10] in sub_base or sub_base[:10] in video_base_lower:
                    LOGGER.info(f"   ✅ Partial Name Match: {ospath.basename(sub_file)}")
                    return sub_file
        
        LOGGER.warning(f"   ❌ No matching subtitle found for: {ospath.basename(video_file)}")
        return None

    async def _process_file_pairs(self, ffmpeg, file_pairs, dir_path, delete_originals, custom_output_name=None):
        """Process multiple video-subtitle pairs or single files."""
        all_outputs = []
        files_to_delete = []
        
        total_pairs = len(file_pairs)
        
        for i, (video_file, subtitle_file, base_name) in enumerate(file_pairs, 1):
            if total_pairs > 1:
                LOGGER.info(f"🎯 Processing file {i}/{total_pairs}: {ospath.basename(video_file)}")
            else:
                LOGGER.info(f"🎯 Processing: {ospath.basename(video_file)}")
            
            # Get video duration for progress tracking
            self._total_time = (await get_media_info(video_file))[0]
            
            # Build FFmpeg command for this specific pair
            current_ffmpeg = []
            input_files = [video_file]
            
            for item in ffmpeg:
                if item in ["*.mkv", "*.mp4", "*.avi", "*.mov", "*.wmv", "*.flv", "*.webm", "*.m4v", "*.3gp"] or item == "*video*":
                    current_ffmpeg.append(video_file)
                elif item in ["*.srt", "*.ass", "*.ssa", "*.vtt", "*.sub", "*.idx", "*.sup"] or item == "*subtitle*":
                    if subtitle_file:
                        current_ffmpeg.append(subtitle_file)
                        if subtitle_file not in input_files:
                            input_files.append(subtitle_file)
                    else:
                        # Skip subtitle input if no subtitle file
                        continue
                elif item.startswith("mltb"):
                    # Generate output filename
                    if custom_output_name:
                        output_file = f"{dir_path}/{custom_output_name.replace('mltb', base_name)}"
                    elif item == "mltb.Sub.mkv":
                        output_file = f"{dir_path}/{base_name}.Sub.mkv"
                    elif item == "mltb.mkv":
                        output_file = f"{dir_path}/{base_name}.mkv"
                    elif item == "mltb.mp4":
                        output_file = f"{dir_path}/{base_name}.mp4"
                    else:
                        # Handle custom output patterns
                        output_file = f"{dir_path}/{item.replace('mltb', base_name)}"
                    
                    current_ffmpeg.append(output_file)
                    all_outputs.append(output_file)
                else:
                    current_ffmpeg.append(item)
            
            # Track files for deletion if requested
            if delete_originals:
                files_to_delete.extend(input_files)
            
            # Check for cancellation
            if self._listener.is_cancelled:
                LOGGER.info("❌ Processing cancelled by user")
                return False
            
            # Execute FFmpeg command
            if total_pairs > 1:
                LOGGER.info(f"   🔄 Executing FFmpeg command for file {i}/{total_pairs}...")
            else:
                LOGGER.info(f"🔄 Executing FFmpeg command...")
            
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
                        LOGGER.info(f"   🗑️  Cleaned up partial output: {ospath.basename(output)}")
                
                return False
            
            LOGGER.info(f"   ✅ Successfully processed: {ospath.basename(video_file)}")
            
            # Update progress tracking for multiple files
            if total_pairs > 1:
                current_duration = (await get_media_info(current_ffmpeg[-1]))[0] if await aiopath.exists(current_ffmpeg[-1]) else 0
                current_size = await aiopath.getsize(current_ffmpeg[-1]) if await aiopath.exists(current_ffmpeg[-1]) else 0
                self._last_processed_time += current_duration
                self._last_processed_bytes += current_size
        
        # Delete original files if requested
        if delete_originals and files_to_delete:
            LOGGER.info("🗑️  Deleting original files...")
            for file_to_delete in set(files_to_delete):  # Remove duplicates
                try:
                    if await aiopath.exists(file_to_delete):
                        await remove(file_to_delete)
                        LOGGER.info(f"   ✅ Deleted: {ospath.basename(file_to_delete)}")
                except Exception as e:
                    LOGGER.error(f"   ❌ Failed to delete {ospath.basename(file_to_delete)}: {e}")
        
        if total_pairs > 1:
            LOGGER.info(f"🎉 Successfully processed {total_pairs} files!")
        
        return all_outputs if len(all_outputs) > 1 else (all_outputs[0] if all_outputs else False)

    async def ffmpeg_cmds(self, ffmpeg, f_path):
        """Main entry point for FFmpeg processing with comprehensive video/subtitle support."""
        self.clear()
        base_name, ext = ospath.splitext(f_path)
        dir_path, base_name = base_name.rsplit("/", 1)
        
        # Check for -del flag
        delete_originals = False
        if "-del" in ffmpeg:
            delete_originals = True
            ffmpeg = [item for item in ffmpeg if item != "-del"]
        
        # Define supported extensions
        video_extensions = ['mkv', 'mp4', 'avi', 'mov', 'wmv', 'flv', 'webm', 'm4v', '3gp', 'ogv', 'ts', 'm2ts', 'mts']
        subtitle_extensions = ['srt', 'ass', 'ssa', 'vtt', 'sub', 'idx', 'sup', 'usf', 'ssf']
        
        # Check if we're using wildcards for batch processing
        video_wildcards = [f"*.{ext}" for ext in video_extensions] + ["*video*"]
        subtitle_wildcards = [f"*.{ext}" for ext in subtitle_extensions] + ["*subtitle*"]
        
        has_video_wildcard = any(wildcard in ffmpeg for wildcard in video_wildcards)
        has_subtitle_wildcard = any(wildcard in ffmpeg for wildcard in subtitle_wildcards)
        
        # Extract custom output name if present
        custom_output_name = None
        for item in ffmpeg:
            if item.startswith("mltb") and not item in ["mltb", "mltb.mkv", "mltb.mp4", "mltb.Sub.mkv"]:
                custom_output_name = item
                break
        
        if has_video_wildcard:
            LOGGER.info("🎬 Batch processing mode detected")
            
            # Check for universal wildcards
            if "*video*" in ffmpeg or "*subtitle*" in ffmpeg:
                file_pairs = self._find_matching_files(dir_path)
            else:
                # Find specific extensions
                used_video_exts = [ext.replace("*.", "") for ext in video_wildcards if f"*.{ext.replace('*.', '')}" in ffmpeg]
                used_subtitle_exts = [ext.replace("*.", "") for ext in subtitle_wildcards if f"*.{ext.replace('*.', '')}" in ffmpeg]
                
                file_pairs = self._find_matching_files(dir_path, used_video_exts if used_video_exts else None, used_subtitle_exts if used_subtitle_exts else None)
            
            if not file_pairs:
                LOGGER.error("❌ No video files found for batch processing!")
                return False
            
            return await self._process_file_pairs(ffmpeg, file_pairs, dir_path, delete_originals, custom_output_name)
        
        else:
            LOGGER.info("🎯 Single file processing mode")
            
            # Handle single file processing with smart wildcard expansion
            expanded_ffmpeg = []
            input_files = []
            
            for i, item in enumerate(ffmpeg):
                if '*' in item and not item.startswith('mltb'):
                    if item == "*video*":
                        # Universal video wildcard
                        video_files = self._get_all_media_files(dir_path, "video")
                        if video_files:
                            expanded_file = video_files[0]  # Use first found
                        else:
                            LOGGER.warning("⚠️  No video files found")
                            continue
                    elif item == "*subtitle*":
                        # Universal subtitle wildcard
                        subtitle_files = self._get_all_media_files(dir_path, "subtitle")
                        if subtitle_files:
                            # Smart subtitle matching for single file processing
                            video_season, video_episode, video_code = self._extract_episode_info(f_path)
                            matched_subtitle = None
                            
                            if video_season and video_episode:
                                LOGGER.info(f"🔍 Looking for subtitle matching {video_code}")
                                
                                for sub_file in subtitle_files:
                                    sub_season, sub_episode, sub_code = self._extract_episode_info(sub_file)
                                    
                                    if sub_season == video_season and sub_episode == video_episode:
                                        matched_subtitle = sub_file
                                        LOGGER.info(f"✅ Found matching subtitle: {ospath.basename(sub_file)} ({sub_code})")
                                        break
                            
                            # Use matched subtitle or fall back to best available match
                            if not matched_subtitle:
                                matched_subtitle = self._find_best_subtitle_match(f_path, subtitle_files, set())
                            
                            if matched_subtitle:
                                expanded_file = matched_subtitle
                            else:
                                LOGGER.warning(f"⚠️  No suitable subtitle found, skipping subtitle input")
                                continue
                        else:
                            LOGGER.warning("⚠️  No subtitle files found")
                            continue
                    else:
                        # Regular wildcard pattern
                        wildcard_pattern = ospath.join(dir_path, item)
                        matches = glob.glob(wildcard_pattern)
                        
                        if any(item.endswith(f"*.{ext}") for ext in subtitle_extensions) and matches:
                            # Smart subtitle matching for single file processing
                            video_season, video_episode, video_code = self._extract_episode_info(f_path)
                            matched_subtitle = None
                            
                            if video_season and video_episode:
                                LOGGER.info(f"🔍 Looking for subtitle matching {video_code}")
                                
                                for sub_file in matches:
                                    sub_season, sub_episode, sub_code = self._extract_episode_info(sub_file)
                                    
                                    if sub_season == video_season and sub_episode == video_episode:
                                        matched_subtitle = sub_file
                                        LOGGER.info(f"✅ Found matching subtitle: {ospath.basename(sub_file)} ({sub_code})")
                                        break
                            
                            # Use matched subtitle or fall back to best available match
                            if not matched_subtitle:
                                matched_subtitle = self._find_best_subtitle_match(f_path, matches, set())
                            
                            if matched_subtitle:
                                expanded_file = matched_subtitle
                                if not matched_subtitle:
                                    LOGGER.warning(f"⚠️  Using first available subtitle: {ospath.basename(matches[0])}")
                            else:
                                LOGGER.warning(f"⚠️  No suitable subtitle found, skipping subtitle input")
                                continue
                        
                        elif matches:
                            # For other wildcards, use first match
                            expanded_file = matches[0]
                        else:
                            expanded_ffmpeg.append(item)
                            continue
                    
                    expanded_ffmpeg.append(expanded_file)
                    if i > 0 and ffmpeg[i-1] == "-i":
                        input_files.append(expanded_file)
                else:
                    expanded_ffmpeg.append(item)
            
            # Process as single file pair
            video_base = ospath.splitext(ospath.basename(f_path))[0]
            file_pairs = [(f_path, None, video_base)]  # Will be updated if subtitle is found in expanded_ffmpeg
            
            # Check if we found a subtitle in the expanded command
            for file_path in input_files:
                if any(file_path.endswith(f".{ext}") for ext in subtitle_extensions):
                    file_pairs = [(f_path, file_path, video_base)]
                    break
            
            ffmpeg = expanded_ffmpeg
            
            # Find output placeholders and generate output files
            outputs = []
            for index, item in enumerate(ffmpeg):
                if item.startswith("mltb") and (index == 0 or ffmpeg[index-1] != "-i"):
                    if custom_output_name:
                        output = f"{dir_path}/{custom_output_name.replace('mltb', video_base)}"
                    elif item != "mltb" and item.startswith("mltb"):
                        if "." in item:
                            output = f"{dir_path}/{item.replace('mltb', video_base)}"
                        else:
                            output = f"{dir_path}/{item.replace('mltb', video_base)}{ext}"
                    else:
                        output = f"{dir_path}/{video_base}{ext}"
                    
                    outputs.append(output)
                    ffmpeg[index] = output
            
            # Execute single file processing
            if self._listener.is_cancelled:
                return False
            
            # Get duration for progress tracking
            self._total_time = (await get_media_info(f_path))[0]
            
            # Log the final command (truncated for readability)
            cmd_preview = ' '.join([ospath.basename(x) if '/' in x else x for x in ffmpeg[:10]])
            LOGGER.info(f"🎬 Executing: {cmd_preview}{'...' if len(ffmpeg) > 10 else ''}")
            
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
                                LOGGER.info(f"🗑️  Deleted original: {ospath.basename(input_file)}")
                        except Exception as e:
                            LOGGER.error(f"❌ Failed to delete {ospath.basename(input_file)}: {e}")
                
                LOGGER.info(f"✅ Successfully processed: {ospath.basename(f_path)}")
                return outputs if len(outputs) > 1 else (outputs[0] if outputs else True)
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
            LOGGER.

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