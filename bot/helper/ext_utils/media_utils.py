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
        
        # Pattern for S##E## format (most reliable)
        pattern = r'S(\d{1,2})E(\d{1,2})'
        match = re.search(pattern, base_name, re.IGNORECASE)
        
        if match:
            season = int(match.group(1))
            episode = int(match.group(2))
            return season, episode, f"S{season:02d}E{episode:02d}"
        
        return None, None, None

    def _find_matching_subtitles(self, video_file, dir_path):
        """Find all matching subtitle files for a video."""
        video_base = ospath.splitext(ospath.basename(video_file))[0]
        video_season, video_episode, video_code = self._extract_episode_info(video_file)
        
        # Find all subtitle files in directory
        subtitle_extensions = ['*.srt', '*.ass', '*.ssa', '*.vtt', '*.sub']
        all_subtitles = []
        
        for ext in subtitle_extensions:
            pattern = ospath.join(dir_path, ext)
            all_subtitles.extend(glob.glob(pattern))
        
        if not all_subtitles:
            LOGGER.info(f"No subtitle files found in directory: {dir_path}")
            return []
        
        matched_subtitles = []
        
        # Priority 1: Season/Episode matching
        if video_season and video_episode:
            for sub_file in all_subtitles:
                sub_season, sub_episode, sub_code = self._extract_episode_info(sub_file)
                if sub_season == video_season and sub_episode == video_episode:
                    matched_subtitles.append(sub_file)
                    LOGGER.info(f"Episode match: {ospath.basename(sub_file)} for {ospath.basename(video_file)}")
        
        # Priority 2: Exact filename match
        if not matched_subtitles:
            for sub_file in all_subtitles:
                sub_base = ospath.splitext(ospath.basename(sub_file))[0]
                if video_base == sub_base:
                    matched_subtitles.append(sub_file)
                    LOGGER.info(f"Filename match: {ospath.basename(sub_file)} for {ospath.basename(video_file)}")
        
        # Priority 3: Partial name matching (remove quality indicators)
        if not matched_subtitles:
            import re
            video_normalized = re.sub(
                r'\s*(1080p|720p|480p|x264|x265|HEVC|BluRay|WEBRip|WEB-DL|HDTV|10bit|2CH|PSA).*', 
                '', 
                video_base, 
                flags=re.IGNORECASE
            ).strip()
            
            for sub_file in all_subtitles:
                sub_base = ospath.splitext(ospath.basename(sub_file))[0]
                sub_normalized = re.sub(
                    r'\s*(1080p|720p|480p|x264|x265|HEVC|BluRay|WEBRip|WEB-DL|HDTV|10bit|2CH|PSA).*', 
                    '', 
                    sub_base, 
                    flags=re.IGNORECASE
                ).strip()
                
                if video_normalized and sub_normalized and video_normalized == sub_normalized:
                    matched_subtitles.append(sub_file)
                    LOGGER.info(f"Normalized match: {ospath.basename(sub_file)} for {ospath.basename(video_file)}")
        
        # If still no matches, return all subtitles (let user decide)
        if not matched_subtitles:
            matched_subtitles = all_subtitles
            LOGGER.info(f"No specific matches found, using all {len(all_subtitles)} subtitle files")
        
        return sorted(matched_subtitles)

    async def _expand_wildcards(self, ffmpeg_cmd, video_file, dir_path):
        """Expand wildcards in FFmpeg command and find matching files."""
        expanded_cmd = []
        input_files = [video_file]  # Always include the main video file
        
        for item in ffmpeg_cmd:
            if '*' in item and not item.startswith('mltb'):
                if item in ['*.mkv', '*.mp4', '*.avi', '*.mov']:
                    # Video wildcards - use the current video file
                    expanded_cmd.append(video_file)
                elif item in ['*.srt', '*.ass', '*.ssa', '*.vtt', '*.sub']:
                    # Subtitle wildcards - find matching subtitles
                    matching_subs = self._find_matching_subtitles(video_file, dir_path)
                    if matching_subs:
                        # Use the best match (first in sorted list)
                        best_sub = matching_subs[0]
                        expanded_cmd.append(best_sub)
                        input_files.append(best_sub)
                        LOGGER.info(f"Using subtitle: {ospath.basename(best_sub)}")
                    else:
                        LOGGER.warning(f"No matching subtitles found for wildcard: {item}")
                        expanded_cmd.append(item)  # Keep original if no match
                else:
                    # Other wildcards - use glob
                    pattern = ospath.join(dir_path, item)
                    matches = glob.glob(pattern)
                    if matches:
                        expanded_cmd.append(matches[0])
                        if not matches[0] in input_files:
                            input_files.append(matches[0])
                    else:
                        expanded_cmd.append(item)
            else:
                expanded_cmd.append(item)
        
        return expanded_cmd, input_files

    async def _generate_output_path(self, template, video_file, dir_path):
        """Generate output file path from template."""
        base_name = ospath.splitext(ospath.basename(video_file))[0]
        
        if template.startswith("mltb"):
            if template == "mltb":
                # Simple replacement
                output_ext = ospath.splitext(video_file)[1]
                return f"{dir_path}/{base_name}{output_ext}"
            elif "." in template:
                # Template with extension (e.g., "mltb.Sub.mkv")
                new_template = template.replace("mltb", base_name)
                return f"{dir_path}/{new_template}"
            else:
                # Template without extension
                output_ext = ospath.splitext(video_file)[1]
                new_template = template.replace("mltb", base_name)
                return f"{dir_path}/{new_template}{output_ext}"
        
        return template

    async def ffmpeg_cmds(self, ffmpeg_cmd, video_file):
        """
        Execute FFmpeg commands with improved subtitle handling and format support.
        
        Supports both MKV and MP4 output formats with automatic subtitle codec selection.
        """
        self.clear()
        
        # Parse command for deletion flag
        delete_originals = False
        if "-del" in ffmpeg_cmd:
            delete_originals = True
            ffmpeg_cmd = [item for item in ffmpeg_cmd if item != "-del"]
        
        # Get file info
        base_name = ospath.splitext(ospath.basename(video_file))[0]
        dir_path = ospath.dirname(video_file)
        
        # Get video duration for progress tracking
        self._total_time = (await get_media_info(video_file))[0]
        
        LOGGER.info(f"🎬 Processing: {ospath.basename(video_file)}")
        
        # Expand wildcards and find matching files
        expanded_cmd, input_files = await self._expand_wildcards(ffmpeg_cmd, video_file, dir_path)
        
        # Generate output files
        output_files = []
        final_cmd = []
        
        for item in expanded_cmd:
            if item.startswith("mltb"):
                output_path = await self._generate_output_path(item, video_file, dir_path)
                output_files.append(output_path)
                final_cmd.append(output_path)
            else:
                final_cmd.append(item)
        
        # Auto-detect output format and adjust subtitle codec if needed
        if output_files:
            main_output = output_files[0]
            output_ext = ospath.splitext(main_output)[1].lower()
            
            # Automatically adjust subtitle codec based on output format
            if output_ext == '.mp4':
                # For MP4, ensure subtitle codec is mov_text
                final_cmd = self._adjust_subtitle_codec_for_mp4(final_cmd)
            elif output_ext == '.mkv':
                # For MKV, ensure subtitle codec is srt or ass
                final_cmd = self._adjust_subtitle_codec_for_mkv(final_cmd)
        
        # Log the final command (truncated for readability)
        cmd_preview = ' '.join([ospath.basename(x) if '/' in x else x for x in final_cmd[:15]])
        if len(final_cmd) > 15:
            cmd_preview += '...'
        LOGGER.info(f"🔧 Command: {cmd_preview}")
        
        # Check for cancellation
        if self._listener.is_cancelled:
            return False
        
        # Execute FFmpeg command
        try:
            self._listener.subproc = await create_subprocess_exec(
                *final_cmd, stdout=PIPE, stderr=PIPE
            )
            
            # Monitor progress
            await self._ffmpeg_progress()
            _, stderr = await self._listener.subproc.communicate()
            code = self._listener.subproc.returncode
            
            if self._listener.is_cancelled:
                LOGGER.info("❌ Processing cancelled by user")
                return False
            
            if code == 0:
                # Success - handle file deletion if requested
                if delete_originals:
                    LOGGER.info("🗑️ Deleting original files...")
                    for input_file in input_files:
                        try:
                            if await aiopath.exists(input_file):
                                await remove(input_file)
                                LOGGER.info(f"   ✅ Deleted: {ospath.basename(input_file)}")
                        except Exception as e:
                            LOGGER.error(f"   ❌ Failed to delete {ospath.basename(input_file)}: {e}")
                
                LOGGER.info(f"✅ Successfully processed: {ospath.basename(video_file)}")
                return output_files if len(output_files) > 1 else output_files[0] if output_files else True
            
            elif code == -9:
                self._listener.is_cancelled = True
                return False
            
            else:
                # Error occurred
                try:
                    stderr_msg = stderr.decode().strip()
                except Exception:
                    stderr_msg = "Unable to decode the error!"
                
                LOGGER.error(f"❌ FFmpeg failed: {stderr_msg}")
                LOGGER.error(f"   File: {video_file}")
                
                # Clean up any partial outputs
                for output_file in output_files:
                    if await aiopath.exists(output_file):
                        await remove(output_file)
                        LOGGER.info(f"   🗑️ Cleaned up: {ospath.basename(output_file)}")
                
                return False
                
        except Exception as e:
            LOGGER.error(f"❌ Unexpected error during FFmpeg execution: {e}")
            return False

    def _adjust_subtitle_codec_for_mp4(self, cmd):
        """Adjust subtitle codec for MP4 output format."""
        adjusted_cmd = cmd.copy()
        
        # Look for subtitle codec settings
        for i, item in enumerate(adjusted_cmd):
            if item.startswith('-c:s'):
                # Replace with mov_text for MP4 compatibility
                if i + 1 < len(adjusted_cmd):
                    adjusted_cmd[i + 1] = 'mov_text'
                    LOGGER.info("📝 Adjusted subtitle codec to mov_text for MP4 output")
                break
        else:
            # If no subtitle codec specified, add mov_text
            # Find the last -c or -codec parameter and add after it
            insert_pos = len(adjusted_cmd) - 1  # Default to end
            for i, item in enumerate(adjusted_cmd):
                if item.startswith('-c:') or item == '-c' or item == '-codec':
                    insert_pos = i + 2  # After the codec specification
            
            adjusted_cmd.insert(insert_pos, '-c:s')
            adjusted_cmd.insert(insert_pos + 1, 'mov_text')
            LOGGER.info("📝 Added mov_text subtitle codec for MP4 output")
        
        return adjusted_cmd

    def _adjust_subtitle_codec_for_mkv(self, cmd):
        """Adjust subtitle codec for MKV output format."""
        adjusted_cmd = cmd.copy()
        
        # Look for subtitle codec settings
        for i, item in enumerate(adjusted_cmd):
            if item.startswith('-c:s'):
                # For MKV, srt or ass are good choices
                if i + 1 < len(adjusted_cmd):
                    current_codec = adjusted_cmd[i + 1]
                    if current_codec not in ['srt', 'ass', 'copy']:
                        adjusted_cmd[i + 1] = 'srt'
                        LOGGER.info("📝 Adjusted subtitle codec to srt for MKV output")
                break
        
        return adjusted_cmd

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