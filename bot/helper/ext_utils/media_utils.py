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


def find_best_subtitle_match(video_file, subtitle_files):
    """
    Find the best matching subtitle file for a video file.
    Uses multiple strategies to find the best match.
    """
    video_base = ospath.splitext(ospath.basename(video_file))[0]
    
    # Strategy 1: Exact base name match
    for srt_file in subtitle_files:
        srt_base = ospath.splitext(ospath.basename(srt_file))[0]
        if video_base == srt_base:
            return srt_file
    
    # Strategy 2: Remove common release group patterns and try again
    import re
    
    # Remove common patterns like [GroupName], (GroupName), etc.
    def clean_filename(filename):
        cleaned = re.sub(r'[\[\(].*?[\]\)]', '', filename)  # Remove bracketed content
        cleaned = re.sub(r'\s+', ' ', cleaned).strip()  # Normalize whitespace
        return cleaned
    
    video_clean = clean_filename(video_base)
    
    for srt_file in subtitle_files:
        srt_base = ospath.splitext(ospath.basename(srt_file))[0]
        srt_clean = clean_filename(srt_base)
        if video_clean == srt_clean:
            return srt_file
    
    # Strategy 3: Episode number matching (for series)
    episode_pattern = r'[SE]\d{2}[EX]\d{2}|S\d{2}E\d{2}|\bE\d{2,3}\b|\b\d{2,3}\b'
    video_episodes = re.findall(episode_pattern, video_base, re.IGNORECASE)
    
    if video_episodes:
        for srt_file in subtitle_files:
            srt_base = ospath.splitext(ospath.basename(srt_file))[0]
            srt_episodes = re.findall(episode_pattern, srt_base, re.IGNORECASE)
            
            # Check if any episode numbers match
            if any(ve.upper() == se.upper() for ve in video_episodes for se in srt_episodes):
                return srt_file
    
    # Strategy 4: Fuzzy matching based on common words
    def get_common_words(filename):
        # Remove common video/subtitle extensions and group tags
        cleaned = re.sub(r'[\[\(].*?[\]\)]', '', filename)
        cleaned = re.sub(r'\b(1080p|720p|480p|x264|x265|aac|eac3|mkv|avi|mp4|srt)\b', '', cleaned, flags=re.IGNORECASE)
        words = re.findall(r'\b\w{3,}\b', cleaned.lower())  # Words with 3+ characters
        return set(words)
    
    video_words = get_common_words(video_base)
    best_match = None
    best_score = 0
    
    for srt_file in subtitle_files:
        srt_base = ospath.splitext(ospath.basename(srt_file))[0]
        srt_words = get_common_words(srt_base)
        
        # Calculate similarity score (Jaccard similarity)
        if video_words and srt_words:
            intersection = len(video_words.intersection(srt_words))
            union = len(video_words.union(srt_words))
            score = intersection / union if union > 0 else 0
            
            if score > best_score and score > 0.3:  # Minimum similarity threshold
                best_score = score
                best_match = srt_file
    
    if best_match:
        LOGGER.info(f"Fuzzy matched '{ospath.basename(video_file)}' with '{ospath.basename(best_match)}' (score: {best_score:.2f})")
        return best_match
    
    return None


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
        
        # More thorough wildcard detection
        has_mkv_wildcard = any("*.mkv" in item for item in ffmpeg)
        has_srt_wildcard = any("*.srt" in item for item in ffmpeg)
        has_video_wildcard = any(item.endswith(("*.mkv", "*.mp4", "*.avi")) for item in ffmpeg)
        has_subtitle_wildcard = any(item.endswith(("*.srt", "*.ass", "*.sub")) for item in ffmpeg)
        
        LOGGER.info(f"Wildcard detection - MKV: {has_mkv_wildcard}, SRT: {has_srt_wildcard}")
        LOGGER.info(f"FFmpeg command: {' '.join(ffmpeg)}")
        
        if (has_mkv_wildcard and has_srt_wildcard) or (has_video_wildcard and has_subtitle_wildcard):
            # Multiple file processing mode with improved pairing
            LOGGER.info("Using multiple file processing mode")
            return await self._process_multiple_files_improved(ffmpeg, f_path, dir, delete_originals)
        else:
            # Single file processing mode (original logic)
            LOGGER.info("Using single file processing mode")
            return await self._process_single_file(ffmpeg, f_path, dir, base_name, ext, delete_originals)
    
        async def _process_multiple_files_improved(self, ffmpeg, f_path, dir, delete_originals):
          """Process multiple video-subtitle pairs with improved matching logic and auto-format detection"""
          
          LOGGER.info(f"Processing multiple files in directory: {dir}")
          LOGGER.info(f"Original FFmpeg command: {' '.join(ffmpeg)}")
          
          # Enhanced wildcard detection for any video/subtitle format
          video_extensions = ["*.mkv", "*.mp4", "*.avi", "*.mov", "*.m4v", "*.webm"]
          subtitle_extensions = ["*.srt", "*.ass", "*.sub", "*.vtt"]
          
          # Find video and subtitle wildcards in command
          video_wildcards = [item for item in ffmpeg if any(item == ext for ext in video_extensions)]
          subtitle_wildcards = [item for item in ffmpeg if any(item == ext for ext in subtitle_extensions)]
          
          LOGGER.info(f"Found video wildcards: {video_wildcards}")
          LOGGER.info(f"Found subtitle wildcards: {subtitle_wildcards}")
          
          # If specific format wildcards found, use them, otherwise auto-detect
          if video_wildcards and subtitle_wildcards:
              # Use the formats specified in the command
              video_files = []
              subtitle_files = []
              
              for video_wildcard in video_wildcards:
                  pattern = os.path.join(dir, video_wildcard.replace("*.", "*."))
                  video_files.extend(sorted(glob.glob(pattern)))
              
              for subtitle_wildcard in subtitle_wildcards:
                  pattern = os.path.join(dir, subtitle_wildcard.replace("*.", "*."))
                  subtitle_files.extend(sorted(glob.glob(pattern)))
                  
              else:
              # Auto-detect all video and subtitle files
                video_files = []
                subtitle_files = []
                
                for ext in video_extensions:
                    pattern = os.path.join(dir, ext)
                    video_files.extend(sorted(glob.glob(pattern)))
                
                for ext in subtitle_extensions:
                    pattern = os.path.join(dir, ext)
                    subtitle_files.extend(sorted(glob.glob(pattern)))
            
            LOGGER.info(f"Found {len(video_files)} video files and {len(subtitle_files)} subtitle files")
            for video in video_files:
                LOGGER.info(f"  Video: {os.path.basename(video)}")
            for subtitle in subtitle_files:
                LOGGER.info(f"  Subtitle: {os.path.basename(subtitle)}")
            
            if not video_files or not subtitle_files:
                LOGGER.error("No matching video or subtitle files found in directory!")
                return False
          
          # Create pairs using improved matching logic
          file_pairs = []
          used_subtitle_files = set()
          
          for video_file in video_files:
              matching_subtitle = find_best_subtitle_match(video_file, [sub for sub in subtitle_files if sub not in used_subtitle_files])
              
              if matching_subtitle:
                  video_base = os.path.splitext(os.path.basename(video_file))[0]
                  file_pairs.append((video_file, matching_subtitle, video_base))
                  used_subtitle_files.add(matching_subtitle)
                  LOGGER.info(f"✅ Paired: {os.path.basename(video_file)} + {os.path.basename(matching_subtitle)}")
              else:
                  LOGGER.warning(f"❌ No matching subtitle found for: {os.path.basename(video_file)}")
          
          if not file_pairs:
              LOGGER.error("No matching video-subtitle pairs found!")
              return False
          
          LOGGER.info(f"Created {len(file_pairs)} file pairs for processing")
          
          # Process each pair
          all_outputs = []
          files_to_delete = []
          successful_pairs = 0
          
          for pair_index, (video_file, subtitle_file, base_name) in enumerate(file_pairs):
              LOGGER.info(f"🎬 Processing pair {pair_index + 1}/{len(file_pairs)}: {os.path.basename(video_file)}")
              
              # Get duration for this specific video
              self._total_time = (await get_media_info(video_file))[0]
              LOGGER.info(f"Video duration: {self._total_time} seconds")
              
              # Create FFmpeg command for this specific pair with format auto-detection
              current_ffmpeg = []
              output_file = None
              
              i = 0
              while i < len(ffmpeg):
                  item = ffmpeg[i]
                  
                  # Replace video wildcards with actual file
                  if any(item == ext for ext in video_extensions):
                      current_ffmpeg.append(video_file)
                      LOGGER.info(f"Replaced {item} with: {video_file}")
                  
                  # Replace subtitle wildcards with actual file  
                  elif any(item == ext for ext in subtitle_extensions):
                      current_ffmpeg.append(subtitle_file)
                      LOGGER.info(f"Replaced {item} with: {subtitle_file}")
                  
                  # Handle output file with format preservation
                  elif item.startswith("mltb"):
                      video_ext = os.path.splitext(video_file)[1]  # Get original video extension
                      
                      if item == "mltb.Sub.mkv":
                          output_file = f"{dir}/{base_name}.Sub{video_ext}"
                      elif item == "mltb.mkv":
                          output_file = f"{dir}/{base_name}{video_ext}"
                      elif item == "mltb":
                          output_file = f"{dir}/{base_name}{video_ext}"
                      else:
                          # Handle other mltb variations, preserve original extension
                          output_file = f"{dir}/{item.replace('mltb', base_name).replace('.mkv', video_ext).replace('.mp4', video_ext).replace('.avi', video_ext)}"
                      
                      current_ffmpeg.append(output_file)
                      all_outputs.append(output_file)
                      LOGGER.info(f"Output file: {output_file}")
                  
                  else:
                      current_ffmpeg.append(item)
                  i += 1
              
              LOGGER.info(f"Final FFmpeg command: {' '.join(current_ffmpeg)}")
              
              # Track files for deletion
              if delete_originals:
                  files_to_delete.extend([video_file, subtitle_file])
              
              # Execute FFmpeg for this pair
              if self._listener.is_cancelled:
                  LOGGER.info("Process cancelled by user")
                  return False
              
              try:    
                  LOGGER.info("Starting FFmpeg process...")
                  self._listener.subproc = await create_subprocess_exec(
                      *current_ffmpeg, stdout=PIPE, stderr=PIPE
                  )
                  await self._ffmpeg_progress()
                  _, stderr = await self._listener.subproc.communicate()
                  code = self._listener.subproc.returncode
                  
                  if self._listener.is_cancelled:
                      LOGGER.info("Process cancelled during execution")
                      return False
                      
                  if code != 0:
                      try:
                          stderr = stderr.decode().strip()
                      except Exception:
                          stderr = "Unable to decode the error!"
                      LOGGER.error(f"❌ Failed to process {os.path.basename(video_file)}: {stderr}")
                      
                      # Remove this pair's output file if it exists
                      if output_file and await aiopath.exists(output_file):
                          await remove(output_file)
                          if output_file in all_outputs:
                              all_outputs.remove(output_file)
                      
                      # Don't fail the entire operation for one file
                      continue
                  
                  successful_pairs += 1
                  LOGGER.info(f"✅ Successfully processed: {os.path.basename(video_file)} -> {os.path.basename(output_file)}")
                  
              except Exception as e:
                  LOGGER.error(f"❌ Exception while processing {os.path.basename(video_file)}: {e}")
                  if output_file and await aiopath.exists(output_file):
                      await remove(output_file)
                      if output_file in all_outputs:
                          all_outputs.remove(output_file)
                  continue
          
          # Only delete original files if at least some processing succeeded
          if delete_originals and successful_pairs > 0:
              LOGGER.info("Deleting original files...")
              # Only delete files that were successfully processed
              successfully_processed_files = []
              for i in range(min(successful_pairs, len(file_pairs))):
                  video_file, subtitle_file, _ = file_pairs[i]
                  successfully_processed_files.extend([video_file, subtitle_file])
              
              for file_to_delete in successfully_processed_files:
                  try:
                      if await aiopath.exists(file_to_delete):
                          await remove(file_to_delete)
                          LOGGER.info(f"🗑️ Deleted original file: {os.path.basename(file_to_delete)}")
                  except Exception as e:
                      LOGGER.error(f"Failed to delete file {file_to_delete}: {e}")
          
          if successful_pairs > 0:
              LOGGER.info(f"🎉 Successfully processed {successful_pairs} out of {len(file_pairs)} video-subtitle pairs")
              return all_outputs if all_outputs else True
          else:
              LOGGER.error("❌ Failed to process any video-subtitle pairs")
              return False
    
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