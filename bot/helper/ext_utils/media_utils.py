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
        """Process multiple video-subtitle pairs with improved TV episode matching for mixed seasons."""
        
        import re
        import os
        
        def extract_episode_id(filename):
            """Extracts season/episode code like S01E02 from filename with multiple format support."""
            patterns = [
                r'S(\d{1,2})E(\d{1,2})',  # S01E01, S1E1 - capture groups for season and episode
                r'Season\s*(\d+).*Episode\s*(\d+)',  # Season 1 Episode 1
                r'(\d{1,2})x(\d{1,2})',  # 1x01
            ]
            
            for pattern in patterns:
                match = re.search(pattern, filename, re.IGNORECASE)
                if match:
                    season = int(match.group(1))
                    episode = int(match.group(2))
                    return f"S{season:02d}E{episode:02d}"
            return None
        
        def extract_base_series_name(filename):
            """Extract the base series name without episode info and quality tags."""
            # Remove file extension
            name = os.path.splitext(filename)[0]
            
            # Remove episode patterns
            patterns_to_remove = [
                r'\s*-\s*S\d{1,2}E\d{1,2}.*$',  # Remove from " - S01E01" onwards
                r'\s*S\d{1,2}E\d{1,2}.*$',      # Remove from "S01E01" onwards  
                r'\s*Season\s*\d+.*$',           # Remove from "Season 1" onwards
                r'\s*\d{1,2}x\d{1,2}.*$',       # Remove from "1x01" onwards
            ]
            
            for pattern in patterns_to_remove:
                name = re.sub(pattern, '', name, flags=re.IGNORECASE)
            
            # Clean up extra spaces and common separators
            name = re.sub(r'\s*[-_]\s*$', '', name).strip()
            
            return name.lower()
    
        def find_best_subtitle_match(mkv_file, srt_files):
            """Find the best matching subtitle for a video file with improved logic."""
            mkv_base = os.path.basename(mkv_file)
            mkv_episode_id = extract_episode_id(mkv_base)
            mkv_series = extract_base_series_name(mkv_base)
            
            LOGGER.info(f"Finding subtitle for: {mkv_base}")
            LOGGER.info(f"  Video episode ID: {mkv_episode_id}")
            LOGGER.info(f"  Video series name: '{mkv_series}'")
            
            best_match = None
            match_type = ""
            match_score = 0
            
            for srt_file in srt_files:
                srt_base = os.path.basename(srt_file)
                srt_episode_id = extract_episode_id(srt_base)
                srt_series = extract_base_series_name(srt_base)
                
                LOGGER.debug(f"  Checking: {srt_base}")
                LOGGER.debug(f"    SRT episode ID: {srt_episode_id}")
                LOGGER.debug(f"    SRT series name: '{srt_series}'")
                
                current_score = 0
                current_match_type = ""
                
                # Priority 1: Exact episode ID match with same series (highest priority)
                if (mkv_episode_id and srt_episode_id == mkv_episode_id and 
                    mkv_series == srt_series):
                    current_score = 100
                    current_match_type = "Perfect match (Series + Episode)"
                
                # Priority 2: Exact episode ID match (even if series name slightly differs)
                elif mkv_episode_id and srt_episode_id == mkv_episode_id:
                    current_score = 90
                    current_match_type = "Episode ID match"
                
                # Priority 3: Exact filename match (without extension)
                elif os.path.splitext(mkv_base)[0].lower() == os.path.splitext(srt_base)[0].lower():
                    current_score = 80
                    current_match_type = "Exact filename match"
                
                # Priority 4: Same series with similar episode (fallback for corrupted episode IDs)
                elif mkv_series == srt_series and mkv_episode_id and srt_episode_id:
                    # Extract episode numbers for proximity check
                    mkv_ep_num = int(re.search(r'E(\d+)', mkv_episode_id).group(1))
                    srt_ep_num = int(re.search(r'E(\d+)', srt_episode_id).group(1))
                    if abs(mkv_ep_num - srt_ep_num) <= 1:  # Allow 1 episode difference
                        current_score = 70
                        current_match_type = f"Series match with close episode (±{abs(mkv_ep_num - srt_ep_num)})"
                
                # Priority 5: Partial name matching (remove quality indicators and match)
                else:
                    mkv_clean = re.sub(r'\s*(1080p|720p|480p|x264|x265|BluRay|WEB-?DL|HDTV|WEBrip).*', 
                                     '', os.path.splitext(mkv_base)[0], flags=re.IGNORECASE).strip().lower()
                    srt_clean = re.sub(r'\s*(1080p|720p|480p|x264|x265|BluRay|WEB-?DL|HDTV|WEBrip).*', 
                                     '', os.path.splitext(srt_base)[0], flags=re.IGNORECASE).strip().lower()
                    
                    if mkv_clean == srt_clean:
                        current_score = 60
                        current_match_type = "Normalized name match"
                
                # Update best match if this one is better
                if current_score > match_score:
                    best_match = srt_file
                    match_type = current_match_type
                    match_score = current_score
                    LOGGER.debug(f"    ✓ New best match! Score: {current_score}")
                elif current_score > 0:
                    LOGGER.debug(f"    + Good match but not best. Score: {current_score}")
            
            if best_match:
                LOGGER.info(f"✓ {match_type}: {mkv_base} <-> {os.path.basename(best_match)} (Score: {match_score})")
                return best_match
            else:
                LOGGER.warning(f"✗ No suitable match found for: {mkv_base}")
                return None
    
        # Get file lists (sorted for consistent order)
        mkv_files = sorted(glob.glob(os.path.join(dir, "*.mkv")))
        srt_files = sorted(glob.glob(os.path.join(dir, "*.srt")))
    
        LOGGER.info(f"Found {len(mkv_files)} MKV files and {len(srt_files)} SRT files")
        
        # Filter out files that already have subtitles embedded (*.Sub.mkv)
        original_mkv_count = len(mkv_files)
        mkv_files = [f for f in mkv_files if not f.endswith('.Sub.mkv')]
        if len(mkv_files) < original_mkv_count:
            LOGGER.info(f"Filtered out {original_mkv_count - len(mkv_files)} files that already have embedded subtitles")
    
        # Create matched pairs using improved logic
        file_pairs = []
        used_srt_files = set()
        
        for mkv_file in mkv_files:
            mkv_base = os.path.splitext(os.path.basename(mkv_file))[0]
            
            # Find best matching SRT from unused files
            available_srts = [srt for srt in srt_files if srt not in used_srt_files]
            matching_srt = find_best_subtitle_match(mkv_file, available_srts)
            
            if matching_srt:
                file_pairs.append((mkv_file, matching_srt, mkv_base))
                used_srt_files.add(matching_srt)
            else:
                LOGGER.warning(f"No matching SRT found for: {os.path.basename(mkv_file)}")
                # Still process the video without subtitles if needed
                # file_pairs.append((mkv_file, None, mkv_base))
    
        if not file_pairs:
            LOGGER.error("No matching MKV-SRT pairs found!")
            return False
    
        LOGGER.info(f"Successfully created {len(file_pairs)} MKV-SRT pairs")
        
        # Show summary of matches
        LOGGER.info("=== MATCHING SUMMARY ===")
        for i, (mkv_file, srt_file, base_name) in enumerate(file_pairs, 1):
            mkv_name = os.path.basename(mkv_file)
            srt_name = os.path.basename(srt_file) if srt_file else "NO SUBTITLE"
            LOGGER.info(f"{i:2d}. {mkv_name} -> {srt_name}")
    
        # Process each MKV+SRT pair
        all_outputs = []
        files_to_delete = []
    
        for i, (mkv_file, srt_file, base_name) in enumerate(file_pairs, 1):
            LOGGER.info(f"Processing pair {i}/{len(file_pairs)}: {os.path.basename(mkv_file)}")
            if srt_file:
                LOGGER.info(f"  + Subtitle: {os.path.basename(srt_file)}")
            
            self._total_time = (await get_media_info(mkv_file))[0]
    
            current_ffmpeg = []
            for item in ffmpeg:
                if item == "*.mkv":
                    current_ffmpeg.append(mkv_file)
                elif item == "*.srt":
                    if srt_file:
                        current_ffmpeg.append(srt_file)
                    else:
                        LOGGER.warning("No subtitle file available, skipping subtitle input")
                        continue
                elif item.startswith("mltb"):
                    if item == "mltb.Sub.mkv":
                        output_file = f"{dir}/{base_name}.Sub.mkv"
                    elif item == "mltb.mkv":
                        output_file = f"{dir}/{base_name}.mkv"
                    else:
                        output_file = f"{dir}/{item.replace('mltb', base_name)}"
                    current_ffmpeg.append(output_file)
                    all_outputs.append(output_file)
                else:
                    current_ffmpeg.append(item)
    
            if delete_originals:
                files_to_delete.append(mkv_file)
                if srt_file:
                    files_to_delete.append(srt_file)
    
            if self._listener.is_cancelled:
                return False
    
            # Log the command being executed (truncated for readability)
            cmd_preview = ' '.join([os.path.basename(x) if os.path.exists(x) else x for x in current_ffmpeg[:10]])
            if len(current_ffmpeg) > 10:
                cmd_preview += " ..."
            LOGGER.info(f"Executing: {cmd_preview}")
            
            self._listener.subproc = await create_subprocess_exec(
                *current_ffmpeg, stdout=PIPE, stderr=PIPE
            )
            await self._ffmpeg_progress()
            _, stderr = await self._listener.subproc.communicate()
            code = self._listener.subproc.returncode
    
            if self._listener.is_cancelled:
                return False
    
            if code != 0:
                try:
                    stderr = stderr.decode().strip()
                except Exception:
                    stderr = "Unable to decode the error!"
                LOGGER.error(f"Failed to process {os.path.basename(mkv_file)}: {stderr}")
                # Clean up partial outputs
                for output in all_outputs:
                    if await aiopath.exists(output):
                        await remove(output)
                return False
    
            LOGGER.info(f"✓ Successfully processed: {os.path.basename(mkv_file)}")
    
        # Delete originals if requested
        if delete_originals:
            LOGGER.info("Cleaning up original files...")
            for file_to_delete in files_to_delete:
                try:
                    if await aiopath.exists(file_to_delete):
                        await remove(file_to_delete)
                        LOGGER.info(f"Deleted: {os.path.basename(file_to_delete)}")
                except Exception as e:
                    LOGGER.error(f"Failed to delete {file_to_delete}: {e}")
    
        LOGGER.info(f"✅ Successfully processed {len(file_pairs)} video-subtitle pairs")
        return all_outputs
    
    
    async def _process_single_file(self, ffmpeg, f_path, dir, base_name, ext, delete_originals):
        """Enhanced single file processing logic with improved episode matching support"""
        import re
        import os
        
        def extract_episode_id(filename):
            """Extracts season/episode code like S01E02 from filename."""
            patterns = [
                r'S(\d{1,2})E(\d{1,2})',  # S01E01, S1E1
                r'Season\s*(\d+).*Episode\s*(\d+)',  # Season 1 Episode 1
                r'(\d{1,2})x(\d{1,2})',  # 1x01
            ]
            
            for pattern in patterns:
                match = re.search(pattern, filename, re.IGNORECASE)
                if match:
                    season = int(match.group(1))
                    episode = int(match.group(2))
                    return f"S{season:02d}E{episode:02d}"
            return None
        
        def extract_base_series_name(filename):
            """Extract the base series name without episode info and quality tags."""
            name = os.path.splitext(filename)[0]
            
            # Remove episode patterns
            patterns_to_remove = [
                r'\s*-\s*S\d{1,2}E\d{1,2}.*,
                r'\s*S\d{1,2}E\d{1,2}.*,
                r'\s*Season\s*\d+.*,
                r'\s*\d{1,2}x\d{1,2}.*,
            ]
            
            for pattern in patterns_to_remove:
                name = re.sub(pattern, '', name, flags=re.IGNORECASE)
            
            name = re.sub(r'\s*[-_]\s*, '', name).strip()
            return name.lower()
    
        def find_matching_subtitle(video_file, dir):
            """Find matching subtitle file for a video using improved episode matching logic"""
            video_base = os.path.basename(video_file)
            video_episode_id = extract_episode_id(video_base)
            video_series = extract_base_series_name(video_base)
            
            LOGGER.info(f"Looking for subtitle match for: {video_base}")
            LOGGER.info(f"  Video episode ID: {video_episode_id}")
            LOGGER.info(f"  Video series: '{video_series}'")
            
            # Get all SRT files in directory (sorted for consistency)
            srt_files = sorted(glob.glob(os.path.join(dir, "*.srt")))
            LOGGER.info(f"Found {len(srt_files)} SRT files in directory")
            
            best_match = None
            match_score = 0
            match_type = ""
            
            for srt_file in srt_files:
                srt_base = os.path.basename(srt_file)
                srt_episode_id = extract_episode_id(srt_base)
                srt_series = extract_base_series_name(srt_base)
                
                LOGGER.debug(f"Checking: {srt_base} -> Episode: {srt_episode_id}, Series: '{srt_series}'")
                
                current_score = 0
                current_match_type = ""
                
                # Perfect match: same series and episode
                if (video_episode_id and srt_episode_id == video_episode_id and 
                    video_series == srt_series):
                    current_score = 100
                    current_match_type = "Perfect match"
                
                # Good match: same episode ID
                elif video_episode_id and srt_episode_id == video_episode_id:
                    current_score = 90
                    current_match_type = "Episode ID match"
                
                # Exact filename match
                elif os.path.splitext(video_base)[0].lower() == os.path.splitext(srt_base)[0].lower():
                    current_score = 80
                    current_match_type = "Exact filename match"
                
                # Series match with close episode number
                elif video_series == srt_series and video_episode_id and srt_episode_id:
                    video_ep_num = int(re.search(r'E(\d+)', video_episode_id).group(1))
                    srt_ep_num = int(re.search(r'E(\d+)', srt_episode_id).group(1))
                    if abs(video_ep_num - srt_ep_num) <= 1:
                        current_score = 70
                        current_match_type = f"Series match, close episode (±{abs(video_ep_num - srt_ep_num)})"
                
                if current_score > match_score:
                    best_match = srt_file
                    match_score = current_score
                    match_type = current_match_type
            
            if best_match:
                LOGGER.info(f"✓ {match_type}: {video_base} <-> {os.path.basename(best_match)} (Score: {match_score})")
                return best_match
            else:
                LOGGER.warning(f"✗ No matching subtitle found for: {video_base}")
                return None
        
        self._total_time = (await get_media_info(f_path))[0]
        
        # Handle wildcards and smart subtitle matching in ffmpeg command
        expanded_ffmpeg = []
        input_files = []
        auto_matched_subtitle = None
        
        # Process each item in ffmpeg command
        for i, item in enumerate(ffmpeg):
            if '*' in item and not item.startswith('mltb'):
                wildcard_pattern = os.path.join(dir, item)
                matches = glob.glob(wildcard_pattern)
                
                if item == "*.srt" and matches:
                    # Smart SRT matching based on improved episode logic
                    matched_srt = find_matching_subtitle(f_path, dir)
                    expanded_file = matched_srt if matched_srt else matches[0]
                    
                    if not matched_srt:
                        LOGGER.warning(f"No episode match found, using first available: {os.path.basename(matches[0])}")
                    else:
                        auto_matched_subtitle = matched_srt
                
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
        
        # Log the final command for debugging
        cmd_preview = ' '.join([os.path.basename(x) if os.path.exists(x) else x for x in ffmpeg])
        LOGGER.info(f"Final command: {cmd_preview}")
        if auto_matched_subtitle:
            LOGGER.info(f"Auto-matched subtitle: {os.path.basename(auto_matched_subtitle)}")
        
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
                # Add the main file to deletion list if not already there
                if f_path not in input_files:
                    input_files.append(f_path)
                
                for input_file in input_files:
                    try:
                        if await aiopath.exists(input_file):
                            await remove(input_file)
                            LOGGER.info(f"Deleted original file: {os.path.basename(input_file)}")
                    except Exception as e:
                        LOGGER.error(f"Failed to delete file {input_file}: {e}")
            
            LOGGER.info(f"Successfully processed: {os.path.basename(f_path)}")
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