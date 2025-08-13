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

    def _get_all_video_files(self, dir_path):
        """Get all video files from directory (all supported formats)."""
        video_extensions = ['mkv', 'mp4', 'avi', 'mov', 'wmv', 'flv', 'webm', 'm4v', '3gp', 'ogv']
        video_files = []
        
        for ext in video_extensions:
            pattern = f"*.{ext}"
            found_files = glob.glob(ospath.join(dir_path, pattern))
            video_files.extend(found_files)
        
        return sorted(video_files)

    def _get_all_subtitle_files(self, dir_path):
        """Get all subtitle files from directory (all supported formats)."""
        subtitle_extensions = ['srt', 'ass', 'ssa', 'idx', 'sub', 'vtt', 'sbv', 'ttml', 'dfxp']
        subtitle_files = []
        
        for ext in subtitle_extensions:
            pattern = f"*.{ext}"
            found_files = glob.glob(ospath.join(dir_path, pattern))
            subtitle_files.extend(found_files)
        
        return sorted(subtitle_files)

    def _find_matching_subtitles(self, video_file, all_subtitle_files):
        """Find all matching subtitles for a video file with enhanced matching."""
        video_season, video_episode, video_code = self._extract_episode_info(video_file)
        video_base = ospath.splitext(ospath.basename(video_file))[0]
        
        LOGGER.info(f"🔍 Finding subtitles for: {ospath.basename(video_file)}")
        if video_code:
            LOGGER.info(f"   Video info: {video_code}")
        
        matched_subtitles = []
        used_subtitles = set()
        
        # Group subtitle files by type for better organization
        subtitle_groups = {}
        for sub_file in all_subtitle_files:
            if sub_file in used_subtitles:
                continue
            sub_ext = ospath.splitext(sub_file)[1][1:].lower()
            if sub_ext not in subtitle_groups:
                subtitle_groups[sub_ext] = []
            subtitle_groups[sub_ext].append(sub_file)
        
        # Process each subtitle type
        for sub_type, sub_files in subtitle_groups.items():
            best_match = None
            match_type = ""
            
            # Priority 1: Exact season/episode match
            if video_season and video_episode:
                for sub_file in sub_files:
                    if sub_file in used_subtitles:
                        continue
                    sub_season, sub_episode, sub_code = self._extract_episode_info(sub_file)
                    if sub_season == video_season and sub_episode == video_episode:
                        best_match = sub_file
                        match_type = "Season/Episode Match"
                        break
            
            # Priority 2: Exact filename match (without extension)
            if not best_match:
                for sub_file in sub_files:
                    if sub_file in used_subtitles:
                        continue
                    sub_base = ospath.splitext(ospath.basename(sub_file))[0]
                    if video_base == sub_base:
                        best_match = sub_file
                        match_type = "Exact Filename Match"
                        break
            
            # Priority 3: Normalized name matching (remove quality tags)
            if not best_match:
                import re
                video_normalized = re.sub(
                    r'\s*(1080p|720p|480p|x264|x265|HEVC|BluRay|WEBRip|WEB-DL|HDTV|10bit|2CH|PSA|JAPANESE|DUAL|AUDIO).*', 
                    '', 
                    video_base, 
                    flags=re.IGNORECASE
                ).strip()
                
                for sub_file in sub_files:
                    if sub_file in used_subtitles:
                        continue
                    sub_base = ospath.splitext(ospath.basename(sub_file))[0]
                    sub_normalized = re.sub(
                        r'\s*(1080p|720p|480p|x264|x265|HEVC|BluRay|WEBRip|WEB-DL|HDTV|10bit|2CH|PSA|JAPANESE|DUAL|AUDIO).*', 
                        '', 
                        sub_base, 
                        flags=re.IGNORECASE
                    ).strip()
                    
                    if video_normalized and sub_normalized and video_normalized == sub_normalized:
                        best_match = sub_file
                        match_type = "Normalized Name Match"
                        break
            
            # Priority 4: Partial name matching (for series)
            if not best_match:
                import re
                # Extract series name (everything before season/episode info)
                video_series = re.sub(r'[.\s]*(S\d+E\d+|Season\s*\d+|Episode\s*\d+).*', '', video_base, flags=re.IGNORECASE).strip()
                
                for sub_file in sub_files:
                    if sub_file in used_subtitles:
                        continue
                    sub_base = ospath.splitext(ospath.basename(sub_file))[0]
                    sub_series = re.sub(r'[.\s]*(S\d+E\d+|Season\s*\d+|Episode\s*\d+).*', '', sub_base, flags=re.IGNORECASE).strip()
                    
                    if video_series and sub_series and video_series.lower() == sub_series.lower():
                        # Additional check for episode numbers if present
                        if video_episode and video_season:
                            sub_season, sub_episode, _ = self._extract_episode_info(sub_file)
                            if sub_season == video_season and sub_episode == video_episode:
                                best_match = sub_file
                                match_type = "Series + Episode Match"
                                break
                        else:
                            best_match = sub_file
                            match_type = "Series Name Match"
                            break
            
            if best_match:
                matched_subtitles.append({
                    'file': best_match,
                    'type': sub_type,
                    'match_type': match_type
                })
                used_subtitles.add(best_match)
                LOGGER.info(f"   ✅ {match_type} ({sub_type.upper()}): {ospath.basename(best_match)}")
        
        return matched_subtitles

    def _get_subtitle_codec(self, container_format, subtitle_type):
        """Get appropriate subtitle codec based on container and subtitle type."""
        container_format = container_format.lower()
        subtitle_type = subtitle_type.lower()
        
        if container_format == 'mp4':
            # MP4 container - convert most subtitles to mov_text
            if subtitle_type in ['srt', 'vtt', 'ass', 'ssa', 'sbv', 'ttml', 'dfxp']:
                return 'mov_text'
            elif subtitle_type in ['idx', 'sub']:
                return 'copy'  # VobSub can be copied to MP4
            else:
                return 'mov_text'  # Default for MP4
        else:
            # MKV, AVI and other containers - can handle most subtitle formats natively
            if subtitle_type == 'srt':
                return 'srt'
            elif subtitle_type in ['ass', 'ssa']:
                return 'ass'
            elif subtitle_type == 'vtt':
                return 'webvtt'
            elif subtitle_type in ['idx', 'sub']:
                return 'copy'  # VobSub format
            elif subtitle_type in ['sbv', 'ttml', 'dfxp']:
                return 'srt'  # Convert to SRT for better compatibility
            else:
                return 'copy'  # Default copy

    async def _process_universal_command(self, f_path, delete_originals):
        """Process using the universal command template - automatically detects all formats."""
        
        dir_path = ospath.dirname(f_path)
        
        # Get ALL video files (any supported format)
        video_files = self._get_all_video_files(dir_path)
        
        if not video_files:
            LOGGER.error("❌ No video files found in directory!")
            return False
        
        # Get ALL subtitle files (any supported format)
        all_subtitle_files = self._get_all_subtitle_files(dir_path)
        
        if not all_subtitle_files:
            LOGGER.error("❌ No subtitle files found in directory!")
            return False
        
        LOGGER.info(f"🎬 Found {len(video_files)} video file(s) and {len(all_subtitle_files)} subtitle file(s)")
        
        all_outputs = []
        
        for i, video_file in enumerate(video_files, 1):
            LOGGER.info(f"🎯 Processing video {i}/{len(video_files)}: {ospath.basename(video_file)}")
            
            # Get video info
            self._total_time = (await get_media_info(video_file))[0]
            video_base_with_ext = ospath.basename(video_file)
            video_base, video_ext = ospath.splitext(video_base_with_ext)
            video_ext = video_ext[1:]  # Remove the dot
            
            # Find matching subtitles for this video
            matched_subtitles = self._find_matching_subtitles(video_file, all_subtitle_files)
            
            if not matched_subtitles:
                LOGGER.warning(f"⚠️ No matching subtitles found for: {ospath.basename(video_file)}")
                continue
            
            # Build FFmpeg command
            cmd = [BinConfig.FFMPEG_NAME, "-hide_banner", "-loglevel", "error", "-progress", "pipe:1"]
            
            # Add video input
            cmd.extend(["-i", video_file])
            input_files = [video_file]
            
            # Add subtitle inputs
            for sub_info in matched_subtitles:
                cmd.extend(["-i", sub_info['file']])
                input_files.append(sub_info['file'])
            
            # Add mapping
            cmd.extend(["-map", "0:v", "-map", "0:a"])
            
            # Map subtitle streams
            for i_sub, _ in enumerate(matched_subtitles, 1):
                cmd.extend(["-map", f"{i_sub}"])
            
            # Copy video and audio codecs
            cmd.extend(["-c", "copy"])
            
            # Set subtitle codecs and metadata
            for i_sub, sub_info in enumerate(matched_subtitles):
                sub_codec = self._get_subtitle_codec(video_ext, sub_info['type'])
                cmd.extend([f"-c:s:{i_sub}", sub_codec])
                
                # Set metadata (language and title)
                cmd.extend([f"-metadata:s:s:{i_sub}", "language=sin"])
                cmd.extend([f"-metadata:s:s:{i_sub}", "title=FLIXORA"])
                
                # Set first subtitle as default and forced
                if i_sub == 0:
                    cmd.extend([f"-disposition:s:{i_sub}", "default"])
                    cmd.extend([f"-disposition:s:{i_sub}", "forced"])
                else:
                    cmd.extend([f"-disposition:s:{i_sub}", "0"])
            
            # Add threads
            cmd.extend(["-threads", f"{max(1, cpu_no // 2)}"])
            
            # Set output file - maintain original extension with .Sub
            output_file = f"{dir_path}/{video_base}.Sub.{video_ext}"
            cmd.append(output_file)
            
            # Log processing info
            LOGGER.info(f"   📹 Input: {video_base_with_ext}")
            LOGGER.info(f"   📁 Output: {video_base}.Sub.{video_ext}")
            LOGGER.info(f"   📝 Subtitles: {len(matched_subtitles)} file(s)")
            
            if self._listener.is_cancelled:
                return False
            
            # Execute FFmpeg
            self._listener.subproc = await create_subprocess_exec(*cmd, stdout=PIPE, stderr=PIPE)
            await self._ffmpeg_progress()
            _, stderr = await self._listener.subproc.communicate()
            code = self._listener.subproc.returncode
            
            if self._listener.is_cancelled:
                return False
            
            if code == 0:
                # Delete original files if requested
                if delete_originals:
                    for input_file in input_files:
                        try:
                            if await aiopath.exists(input_file):
                                await remove(input_file)
                                LOGGER.info(f"🗑️ Deleted original: {ospath.basename(input_file)}")
                        except Exception as e:
                            LOGGER.error(f"❌ Failed to delete {ospath.basename(input_file)}: {e}")
                
                LOGGER.info(f"✅ Successfully processed: {ospath.basename(video_file)}")
                all_outputs.append(output_file)
            elif code == -9:
                self._listener.is_cancelled = True
                return False
            else:
                try:
                    stderr = stderr.decode().strip()
                except Exception:
                    stderr = "Unable to decode the error!"
                
                LOGGER.error(f"❌ Failed to process {ospath.basename(video_file)}: {stderr}")
                
                # Clean up output file
                if await aiopath.exists(output_file):
                    await remove(output_file)
                    LOGGER.info(f"🗑️ Cleaned up partial output: {ospath.basename(output_file)}")
            
            # Check for cancellation between files
            if self._listener.is_cancelled:
                LOGGER.info("❌ Processing cancelled by user")
                return False
        
        if all_outputs:
            LOGGER.info(f"🎉 Successfully processed {len(all_outputs)} video(s) with subtitles!")
            return all_outputs
        else:
            LOGGER.error("❌ No videos were successfully processed!")
            return False

    async def ffmpeg_cmds(self, ffmpeg, f_path):
        """Main entry point - only accepts the universal command format."""
        self.clear()
        
        # Validate command format
        if not isinstance(ffmpeg, list) or len(ffmpeg) != 1:
            LOGGER.error("❌ Invalid command format! Only accepts single command string format.")
            return False
        
        cmd_string = ffmpeg[0]
        
        # Check for required components in the command
        required_components = ["-i *.mkv", "-i *.srt", "-map 0:v", "-map 0:a", "-map 1", "-c copy"]
        for component in required_components:
            if component not in cmd_string:
                LOGGER.error(f"❌ Missing required component: {component}")
                return False
        
        # Check for -del flag
        delete_originals = '-del' in cmd_string
        
        LOGGER.info("🎬 Universal Auto-Detection Mode Active")
        LOGGER.info("   🔍 Auto-detecting all video formats: MKV, MP4, AVI, MOV, WMV, FLV, WEBM, M4V, 3GP, OGV")
        LOGGER.info("   🔍 Auto-detecting all subtitle formats: SRT, ASS, SSA, IDX+SUB, VTT, SBV, TTML, DFXP")
        LOGGER.info(f"   🗑️ Delete originals: {'Yes' if delete_originals else 'No'}")
        
        # Process with universal auto-detection
        return await self._process_universal_command(f_path, delete_originals)

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
            self._last_processed_time += lpd - 3
            self._last_processed_bytes += out_size
            start_time += lpd - 3
            i += 1
        return True