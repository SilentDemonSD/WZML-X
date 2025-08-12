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
        
        # Multiple patterns for different naming conventions
        patterns = [
            # S##E## format (most common)
            r'S(\d{1,2})E(\d{1,3})',
            # Season ## Episode ## format
            r'Season[\s\._-]*(\d{1,2})[\s\._-]*Episode[\s\._-]*(\d{1,3})',
            # ##x## format
            r'(\d{1,2})x(\d{1,3})',
            # Episode ## format (assumes season 1)
            r'Episode[\s\._-]*(\d{1,3})',
            # E## format (assumes season 1)
            r'E(\d{1,3})',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, base_name, re.IGNORECASE)
            if match:
                if len(match.groups()) == 2:
                    season = int(match.group(1))
                    episode = int(match.group(2))
                else:
                    # Single group means episode only, assume season 1
                    season = 1
                    episode = int(match.group(1))
                return season, episode, f"S{season:02d}E{episode:02d}"
        
        return None, None, None

    def _find_best_subtitle_match(self, video_file, subtitle_files):
        """Enhanced subtitle matching with multiple language support."""
        video_season, video_episode, video_code = self._extract_episode_info(video_file)
        video_base = ospath.splitext(ospath.basename(video_file))[0]
        
        LOGGER.info(f"🔍 Finding subtitles for: {ospath.basename(video_file)}")
        LOGGER.info(f"   Video info: Season {video_season}, Episode {video_episode} ({video_code})")
        
        matches = []
        
        # Group subtitles by language if possible
        language_groups = {}
        for sub_file in subtitle_files:
            # Try to detect language from filename
            sub_base = ospath.splitext(ospath.basename(sub_file))[0]
            lang_indicators = ['eng', 'english', 'sin', 'sinhala', 'tam', 'tamil', 'hin', 'hindi']
            detected_lang = 'unknown'
            
            for lang in lang_indicators:
                if lang in sub_base.lower():
                    detected_lang = lang
                    break
            
            if detected_lang not in language_groups:
                language_groups[detected_lang] = []
            language_groups[detected_lang].append(sub_file)
        
        # Priority matching for each language group
        for lang, subs in language_groups.items():
            best_match = None
            match_type = ""
            
            # Priority 1: Exact season/episode match
            if video_season and video_episode:
                for sub_file in subs:
                    sub_season, sub_episode, sub_code = self._extract_episode_info(sub_file)
                    
                    if sub_season == video_season and sub_episode == video_episode:
                        best_match = sub_file
                        match_type = "Season/Episode Match"
                        break
            
            # Priority 2: Exact filename match (without extension)
            if not best_match:
                for sub_file in subs:
                    sub_base = ospath.splitext(ospath.basename(sub_file))[0]
                    if video_base == sub_base:
                        best_match = sub_file
                        match_type = "Exact Filename Match"
                        break
            
            # Priority 3: Normalized name matching
            if not best_match:
                import re
                video_normalized = re.sub(
                    r'\s*(1080p|720p|480p|x264|x265|HEVC|BluRay|WEBRip|WEB-DL|HDTV|10bit|2CH|PSA|JAPANESE|FLIXORA).*', 
                    '', 
                    video_base, 
                    flags=re.IGNORECASE
                ).strip()
                
                for sub_file in subs:
                    sub_base = ospath.splitext(ospath.basename(sub_file))[0]
                    sub_normalized = re.sub(
                        r'\s*(1080p|720p|480p|x264|x265|HEVC|BluRay|WEBRip|WEB-DL|HDTV|10bit|2CH|PSA|JAPANESE|FLIXORA).*', 
                        '', 
                        sub_base, 
                        flags=re.IGNORECASE
                    ).strip()
                    
                    if video_normalized and sub_normalized and video_normalized == sub_normalized:
                        best_match = sub_file
                        match_type = "Normalized Name Match"
                        break
            
            # Priority 4: Partial name matching
            if not best_match and len(subs) == 1:
                best_match = subs[0]
                match_type = "Single Subtitle Available"
            
            if best_match:
                matches.append((best_match, lang, match_type))
                LOGGER.info(f"   ✅ {match_type} ({lang}): {ospath.basename(best_match)}")
        
        if not matches:
            LOGGER.warning(f"   ❌ No matching subtitles found for: {ospath.basename(video_file)}")
        
        return matches

    def _get_all_media_files(self, directory, extensions):
        """Get all media files with specified extensions from directory."""
        files = []
        for ext in extensions:
            pattern = ospath.join(directory, f"*.{ext}")
            files.extend(glob.glob(pattern))
        return sorted(files)

    async def _build_ffmpeg_command_with_subtitles(self, video_file, subtitle_matches, output_file, base_ffmpeg):
        """Build FFmpeg command with multiple subtitle inputs and mappings."""
        cmd = [BinConfig.FFMPEG_NAME, "-hide_banner", "-loglevel", "error", "-progress", "pipe:1"]
        
        # Add video input
        cmd.extend(["-i", video_file])
        
        # Add subtitle inputs
        subtitle_files = []
        for sub_file, lang, match_type in subtitle_matches:
            cmd.extend(["-i", sub_file])
            subtitle_files.append((sub_file, lang))
        
        # Map video and audio streams
        cmd.extend(["-map", "0:v", "-map", "0:a"])
        
        # Map subtitle streams
        for i, (sub_file, lang) in enumerate(subtitle_files):
            cmd.extend(["-map", f"{i+1}"])
        
        # Copy video and audio codecs
        cmd.extend(["-c:v", "copy", "-c:a", "copy"])
        
        # Configure subtitle codecs and metadata
        for i, (sub_file, lang) in enumerate(subtitle_files):
            cmd.extend([f"-c:s:{i}", "srt"])
            
            # Set language metadata
            if lang in ['sin', 'sinhala']:
                cmd.extend([f"-metadata:s:s:{i}", "language=sin"])
                cmd.extend([f"-metadata:s:s:{i}", "title=Sinhala"])
            elif lang in ['tam', 'tamil']:
                cmd.extend([f"-metadata:s:s:{i}", "language=tam"])
                cmd.extend([f"-metadata:s:s:{i}", "title=Tamil"])
            elif lang in ['hin', 'hindi']:
                cmd.extend([f"-metadata:s:s:{i}", "language=hin"])
                cmd.extend([f"-metadata:s:s:{i}", "title=Hindi"])
            elif lang in ['eng', 'english']:
                cmd.extend([f"-metadata:s:s:{i}", "language=eng"])
                cmd.extend([f"-metadata:s:s:{i}", "title=English"])
            else:
                cmd.extend([f"-metadata:s:s:{i}", "language=und"])
                cmd.extend([f"-metadata:s:s:{i}", "title=FLIXORA"])
            
            # Set first subtitle as default
            if i == 0:
                cmd.extend([f"-disposition:s:{i}", "default"])
            else:
                cmd.extend([f"-disposition:s:{i}", "0"])
        
        # Add threading and output
        cmd.extend(["-threads", f"{max(1, cpu_no // 2)}", output_file])
        
        return cmd

    async def _process_all_videos_and_subtitles(self, ffmpeg_template, directory, delete_originals=False):
        """Process all videos and subtitles in a directory with comprehensive matching."""
        
        # Get all video and subtitle files
        video_files = self._get_all_media_files(directory, ['mkv', 'mp4', 'avi', 'mov', 'webm'])
        subtitle_files = self._get_all_media_files(directory, ['srt', 'ass', 'vtt', 'sub'])
        
        LOGGER.info(f"📁 Found {len(video_files)} video files and {len(subtitle_files)} subtitle files")
        
        if not video_files:
            LOGGER.error("❌ No video files found in directory!")
            return False
        
        if not subtitle_files:
            LOGGER.warning("⚠️  No subtitle files found in directory!")
            return await self._process_videos_only(video_files, ffmpeg_template, delete_originals)
        
        # Process each video file
        all_outputs = []
        files_to_delete = []
        processed_count = 0
        
        for i, video_file in enumerate(video_files, 1):
            LOGGER.info(f"🎯 Processing video {i}/{len(video_files)}: {ospath.basename(video_file)}")
            
            # Find matching subtitles
            subtitle_matches = self._find_best_subtitle_match(video_file, subtitle_files)
            
            if not subtitle_matches:
                LOGGER.warning(f"   ⚠️  No subtitles found for {ospath.basename(video_file)}, processing without subtitles")
                # Process without subtitles
                result = await self._process_single_video_without_subs(video_file, ffmpeg_template, delete_originals)
                if result:
                    all_outputs.extend(result if isinstance(result, list) else [result])
                    processed_count += 1
                continue
            
            # Get video duration for progress tracking
            self._total_time = (await get_media_info(video_file))[0]
            
            # Generate output filename with original extension
            base_name = ospath.splitext(ospath.basename(video_file))[0]
            original_ext = ospath.splitext(video_file)[1]  # Get original extension
            output_file = ospath.join(directory, f"{base_name}.Sub{original_ext}")
            
            # Build FFmpeg command with all matched subtitles
            cmd = await self._build_ffmpeg_command_with_subtitles(
                video_file, subtitle_matches, output_file, ffmpeg_template
            )
            
            # Track files for deletion
            if delete_originals:
                files_to_delete.append(video_file)
                files_to_delete.extend([match[0] for match in subtitle_matches])
            
            # Check for cancellation
            if self._listener.is_cancelled:
                LOGGER.info("❌ Processing cancelled by user")
                return False
            
            # Execute FFmpeg command
            LOGGER.info(f"   🔄 Executing FFmpeg with {len(subtitle_matches)} subtitle(s)...")
            self._listener.subproc = await create_subprocess_exec(
                *cmd, stdout=PIPE, stderr=PIPE
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
                
                # Clean up partial output
                if await aiopath.exists(output_file):
                    await remove(output_file)
                    LOGGER.info(f"   🗑️  Cleaned up partial output: {ospath.basename(output_file)}")
                
                continue
            
            LOGGER.info(f"   ✅ Successfully processed: {ospath.basename(video_file)}")
            all_outputs.append(output_file)
            processed_count += 1
        
        # Delete original files if requested
        if delete_originals and files_to_delete:
            LOGGER.info("🗑️  Deleting original files...")
            unique_files = list(set(files_to_delete))  # Remove duplicates
            for file_to_delete in unique_files:
                try:
                    if await aiopath.exists(file_to_delete):
                        await remove(file_to_delete)
                        LOGGER.info(f"   ✅ Deleted: {ospath.basename(file_to_delete)}")
                except Exception as e:
                    LOGGER.error(f"   ❌ Failed to delete {ospath.basename(file_to_delete)}: {e}")
        
        if processed_count > 0:
            LOGGER.info(f"🎉 Successfully processed {processed_count}/{len(video_files)} videos!")
            return all_outputs
        else:
            LOGGER.error("❌ No videos were successfully processed!")
            return False

    async def _process_videos_only(self, video_files, ffmpeg_template, delete_originals):
        """Process videos without subtitles."""
        all_outputs = []
        files_to_delete = []
        
        for video_file in video_files:
            base_name = ospath.splitext(ospath.basename(video_file))[0]
            directory = ospath.dirname(video_file)
            output_file = ospath.join(directory, f"{base_name}.processed.mkv")
            
            cmd = [
                BinConfig.FFMPEG_NAME,
                "-hide_banner",
                "-loglevel",
                "error",
                "-progress",
                "pipe:1",
                "-i",
                video_file,
                "-c",
                "copy",
                "-threads",
                f"{max(1, cpu_no // 2)}",
                output_file,
            ]
            
            if delete_originals:
                files_to_delete.append(video_file)
            
            if self._listener.is_cancelled:
                return False
            
            self._listener.subproc = await create_subprocess_exec(
                *cmd, stdout=PIPE, stderr=PIPE
            )
            
            await self._ffmpeg_progress()
            _, stderr = await self._listener.subproc.communicate()
            code = self._listener.subproc.returncode
            
            if code == 0:
                all_outputs.append(output_file)
                LOGGER.info(f"✅ Processed video: {ospath.basename(video_file)}")
            else:
                LOGGER.error(f"❌ Failed to process video: {ospath.basename(video_file)}")
                if await aiopath.exists(output_file):
                    await remove(output_file)
        
        # Delete originals if requested
        if delete_originals:
            for file_to_delete in files_to_delete:
                try:
                    if await aiopath.exists(file_to_delete):
                        await remove(file_to_delete)
                except Exception as e:
                    LOGGER.error(f"Failed to delete {file_to_delete}: {e}")
        
        return all_outputs

    async def _process_single_video_without_subs(self, video_file, ffmpeg_template, delete_originals):
        """Process a single video file without subtitles."""
        base_name = ospath.splitext(ospath.basename(video_file))[0]
        directory = ospath.dirname(video_file)
        original_ext = ospath.splitext(video_file)[1]  # Preserve original extension
        output_file = ospath.join(directory, f"{base_name}.processed{original_ext}")
        
        cmd = [
            BinConfig.FFMPEG_NAME,
            "-hide_banner",
            "-loglevel",
            "error",
            "-progress",
            "pipe:1",
            "-i",
            video_file,
            "-c",
            "copy",
            "-threads",
            f"{max(1, cpu_no // 2)}",
            output_file,
        ]
        
        self._listener.subproc = await create_subprocess_exec(
            *cmd, stdout=PIPE, stderr=PIPE
        )
        
        await self._ffmpeg_progress()
        _, stderr = await self._listener.subproc.communicate()
        code = self._listener.subproc.returncode
        
        if code == 0:
            if delete_originals:
                try:
                    await remove(video_file)
                    LOGGER.info(f"🗑️  Deleted original: {ospath.basename(video_file)}")
                except Exception as e:
                    LOGGER.error(f"Failed to delete {video_file}: {e}")
            return [output_file]
        else:
            if await aiopath.exists(output_file):
                await remove(output_file)
            return False

    async def _process_multiple_files(self, ffmpeg, f_path, dir, delete_originals):
        """Enhanced multiple file processing with comprehensive subtitle support."""
        
        # Check if this is the "all videos and subtitles" mode
        if "*.mkv" in ffmpeg and "*.srt" in ffmpeg:
            return await self._process_all_videos_and_subtitles(ffmpeg, dir, delete_originals)
        
        # Original multiple file processing logic for other cases
        mkv_files = sorted(glob.glob(ospath.join(dir, "*.mkv")))
        srt_files = sorted(glob.glob(ospath.join(dir, "*.srt")))
        
        LOGGER.info(f"📁 Found {len(mkv_files)} MKV files and {len(srt_files)} SRT files")
        
        # Create episode pairs with enhanced matching
        file_pairs = []
        used_srt_files = set()
        
        for mkv_file in mkv_files:
            # Find best matching SRT from unused files
            available_srts = [srt for srt in srt_files if srt not in used_srt_files]
            subtitle_matches = self._find_best_subtitle_match(mkv_file, available_srts)
            
            if subtitle_matches:
                # Use the first (best) match
                matching_srt = subtitle_matches[0][0]
                mkv_base = ospath.splitext(ospath.basename(mkv_file))[0]
                file_pairs.append((mkv_file, matching_srt, mkv_base))
                used_srt_files.add(matching_srt)
                LOGGER.info(f"   ✅ Paired: {ospath.basename(mkv_file)} ↔ {ospath.basename(matching_srt)}")
            else:
                LOGGER.warning(f"   ⚠️  No subtitle match for: {ospath.basename(mkv_file)}")
        
        if not file_pairs:
            LOGGER.error("❌ No matching MKV-SRT pairs found!")
            return False
        
        LOGGER.info(f"🎬 Processing {len(file_pairs)} video-subtitle pairs...")
        
        # Process each pair
        all_outputs = []
        files_to_delete = []
        
        for i, (mkv_file, srt_file, base_name) in enumerate(file_pairs, 1):
            LOGGER.info(f"🎯 Processing pair {i}/{len(file_pairs)}: {ospath.basename(mkv_file)}")
            
            # Get video duration for progress tracking
            self._total_time = (await get_media_info(mkv_file))[0]
            
            # Build FFmpeg command for this specific pair
            current_ffmpeg = []
            for item in ffmpeg:
                if item == "*.mkv":
                    current_ffmpeg.append(mkv_file)
                elif item == "*.srt":
                    current_ffmpeg.append(srt_file)
                elif item.startswith("mltb"):
                    # Generate output filename with original extension
                    if item == "mltb.Sub.mkv":
                        original_ext = ospath.splitext(mkv_file)[1]
                        output_file = f"{dir}/{base_name}.Sub{original_ext}"
                    elif item == "mltb.mkv":
                        original_ext = ospath.splitext(mkv_file)[1]
                        output_file = f"{dir}/{base_name}{original_ext}"
                    else:
                        # For custom patterns, preserve original extension
                        original_ext = ospath.splitext(mkv_file)[1]
                        if "." in item:
                            # Replace extension with original
                            item_base = item.rsplit(".", 1)[0]
                            output_file = f"{dir}/{item_base.replace('mltb', base_name)}{original_ext}"
                        else:
                            output_file = f"{dir}/{item.replace('mltb', base_name)}{original_ext}"
                    
                    current_ffmpeg.append(output_file)
                    all_outputs.append(output_file)
                else:
                    current_ffmpeg.append(item)
            
            # Track files for deletion if requested
            if delete_originals:
                files_to_delete.extend([mkv_file, srt_file])
            
            # Check for cancellation
            if self._listener.is_cancelled:
                LOGGER.info("❌ Processing cancelled by user")
                return False
            
            # Execute FFmpeg command
            LOGGER.info(f"   🔄 Executing FFmpeg command...")
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
                
                LOGGER.error(f"   ❌ Failed to process {ospath.basename(mkv_file)}: {stderr}")
                
                # Clean up any partial outputs
                for output in all_outputs:
                    if await aiopath.exists(output):
                        await remove(output)
                        LOGGER.info(f"   🗑️  Cleaned up partial output: {ospath.basename(output)}")
                
                return False
            
            LOGGER.info(f"   ✅ Successfully processed: {ospath.basename(mkv_file)}")
        
        # Delete original files if requested
        if delete_originals:
            LOGGER.info("🗑️  Deleting original files...")
            unique_files = list(set(files_to_delete))  # Remove duplicates
            for file_to_delete in unique_files:
                try:
                    if await aiopath.exists(file_to_delete):
                        await remove(file_to_delete)
                        LOGGER.info(f"   ✅ Deleted: {ospath.basename(file_to_delete)}")
                except Exception as e:
                    LOGGER.error(f"   ❌ Failed to delete {ospath.basename(file_to_delete)}: {e}")
        
        LOGGER.info(f"🎉 Successfully processed {len(file_pairs)} video-subtitle pairs!")
        return all_outputs

    async def _process_single_file(self, ffmpeg, f_path, dir, base_name, ext, delete_originals):
        """Enhanced single file processing with smart subtitle matching."""
        
        self._total_time = (await get_media_info(f_path))[0]
        
        # Handle wildcards and smart subtitle matching
        expanded_ffmpeg = []
        input_files = []
        
        for i, item in enumerate(ffmpeg):
            if '*' in item and not item.startswith('mltb'):
                wildcard_pattern = ospath.join(dir, item)
                matches = glob.glob(wildcard_pattern)
                
                if item == "*.srt" and matches:
                    # Smart SRT matching for single file processing
                    video_season, video_episode, video_code = self._extract_episode_info(f_path)
                    matched_srt = None
                    
                    if video_season and video_episode:
                        LOGGER.info(f"🔍 Looking for SRT matching {video_code}")
                        
                        for srt_file in matches:
                            srt_season, srt_episode, srt_code = self._extract_episode_info(srt_file)
                            
                            if srt_season == video_season and srt_episode == video_episode:
                                matched_srt = srt_file
                                LOGGER.info(f"✅ Found matching SRT: {ospath.basename(srt_file)} ({srt_code})")
                                break
                    
                    # Use matched SRT or fall back to first one
                    expanded_file = matched_srt if matched_srt else matches[0]
                    if not matched_srt:
                        LOGGER.warning(f"⚠️  No episode match found, using: {ospath.basename(matches[0])}")
                
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
        
        ffmpeg = expanded_ffmpeg
        
        # Find output placeholders and generate output files with original extensions
        outputs = []
        for index, item in enumerate(ffmpeg):
            if item.startswith("mltb") and (index == 0 or ffmpeg[index-1] != "-i"):
                if item != "mltb" and item.startswith("mltb"):
                    if "." in item:
                        # Replace the extension with original extension
                        item_base = item.rsplit(".", 1)[0]
                        output = f"{dir}/{item_base.replace('mltb', base_name)}{ext}"
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
                            LOGGER.info(f"🗑️  Deleted original: {ospath.basename(input_file)}")
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
        """Main entry point for FFmpeg processing with enhanced multi-subtitle support."""
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
        has_video_wildcards = any(pattern in ffmpeg for pattern in ["*.mkv", "*.mp4", "*.avi", "*.mov", "*.webm"])
        has_subtitle_wildcards = any(pattern in ffmpeg for pattern in ["*.srt", "*.ass", "*.vtt", "*.sub"])
        
        if has_video_wildcards or has_subtitle_wildcards:
            LOGGER.info("🎬 Multiple file processing mode detected")
            return await self._process_multiple_files(ffmpeg, f_path, dir, delete_originals)
        else:
            LOGGER.info("🎯 Single file processing mode")
            return await self._process_single_file(ffmpeg, f_path, dir, base_name, ext, delete_originals)

    async def convert_video(self, video_file, ext, retry=False):
        """Enhanced video conversion with better codec handling."""
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
        """Enhanced audio conversion."""
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
        """Enhanced video sampling."""
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
        """Enhanced video splitting with better error handling."""
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

    async def extract_subtitles(self, video_file, output_dir=None):
        """Extract all subtitle streams from a video file."""
        if not output_dir:
            output_dir = ospath.dirname(video_file)
        
        # Get stream information
        streams = await get_streams(video_file)
        if not streams:
            LOGGER.error(f"Could not get stream info for: {video_file}")
            return False
        
        # Find subtitle streams
        subtitle_streams = []
        for i, stream in enumerate(streams):
            if stream.get("codec_type") == "subtitle":
                subtitle_streams.append((i, stream))
        
        if not subtitle_streams:
            LOGGER.info(f"No subtitle streams found in: {ospath.basename(video_file)}")
            return False
        
        LOGGER.info(f"📝 Found {len(subtitle_streams)} subtitle stream(s) in: {ospath.basename(video_file)}")
        
        # Extract each subtitle stream
        base_name = ospath.splitext(ospath.basename(video_file))[0]
        extracted_files = []
        
        for stream_index, stream_info in subtitle_streams:
            # Get language info
            tags = stream_info.get("tags", {})
            language = tags.get("language", "unknown")
            title = tags.get("title", f"subtitle_{stream_index}")
            
            # Generate output filename
            output_file = ospath.join(output_dir, f"{base_name}_{language}_{stream_index}.srt")
            
            cmd = [
                BinConfig.FFMPEG_NAME,
                "-hide_banner",
                "-loglevel",
                "error",
                "-i",
                video_file,
                "-map",
                f"0:s:{stream_index}",
                "-c:s",
                "srt",
                output_file,
            ]
            
            try:
                process = await create_subprocess_exec(*cmd, stdout=PIPE, stderr=PIPE)
                _, stderr = await process.communicate()
                
                if process.returncode == 0:
                    extracted_files.append(output_file)
                    LOGGER.info(f"   ✅ Extracted: {ospath.basename(output_file)} ({language})")
                else:
                    stderr_text = stderr.decode().strip() if stderr else "Unknown error"
                    LOGGER.error(f"   ❌ Failed to extract subtitle {stream_index}: {stderr_text}")
            except Exception as e:
                LOGGER.error(f"   ❌ Exception extracting subtitle {stream_index}: {e}")
        
        return extracted_files if extracted_files else False

    async def merge_videos(self, video_files, output_file):
        """Merge multiple video files into one."""
        if len(video_files) < 2:
            LOGGER.error("At least 2 video files are required for merging")
            return False
        
        self.clear()
        
        # Create a temporary file list for FFmpeg concat demuxer
        file_list_path = f"{ospath.dirname(output_file)}/temp_file_list.txt"
        
        try:
            # Write file list
            with open(file_list_path, 'w') as f:
                for video_file in video_files:
                    f.write(f"file '{video_file}'\n")
            
            # Get total duration for progress tracking
            total_duration = 0
            for video_file in video_files:
                duration = (await get_media_info(video_file))[0]
                total_duration += duration
            
            self._total_time = total_duration
            
            cmd = [
                BinConfig.FFMPEG_NAME,
                "-hide_banner",
                "-loglevel",
                "error",
                "-progress",
                "pipe:1",
                "-f",
                "concat",
                "-safe",
                "0",
                "-i",
                file_list_path,
                "-c",
                "copy",
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
            
            if code == 0:
                LOGGER.info(f"✅ Successfully merged {len(video_files)} videos into: {ospath.basename(output_file)}")
                return output_file
            else:
                try:
                    stderr = stderr.decode().strip()
                except Exception:
                    stderr = "Unable to decode the error!"
                LOGGER.error(f"❌ Failed to merge videos: {stderr}")
                if await aiopath.exists(output_file):
                    await remove(output_file)
                return False
        
        finally:
            # Clean up temporary file list
            with suppress(Exception):
                await remove(file_list_path)

    async def add_watermark(self, video_file, watermark_text, position="bottom-right", opacity=0.7):
        """Add text watermark to video."""
        self.clear()
        self._total_time = (await get_media_info(video_file))[0]
        base_name = ospath.splitext(video_file)[0]
        output = f"{base_name}_watermarked.mkv"
        
        # Position mapping
        position_map = {
            "top-left": "10:10",
            "top-right": "W-tw-10:10",
            "bottom-left": "10:H-th-10",
            "bottom-right": "W-tw-10:H-th-10",
            "center": "(W-tw)/2:(H-th)/2"
        }
        
        pos = position_map.get(position, position_map["bottom-right"])
        
        cmd = [
            BinConfig.FFMPEG_NAME,
            "-hide_banner",
            "-loglevel",
            "error",
            "-progress",
            "pipe:1",
            "-i",
            video_file,
            "-vf",
            f"drawtext=text='{watermark_text}':fontsize=24:fontcolor=white@{opacity}:x={pos}",
            "-c:a",
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
        else:
            try:
                stderr = stderr.decode().strip()
            except Exception:
                stderr = "Unable to decode the error!"
            LOGGER.error(f"❌ Failed to add watermark: {stderr}")
            if await aiopath.exists(output):
                await remove(output)
            return False