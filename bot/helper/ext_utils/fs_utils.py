import os
import sys
import shutil
import subprocess
import argparse
import pathlib
import magic
import time
import math
import re
from functools import lru_cache
from typing import Any, Callable, Final, List, Optional, Tuple

import aria2
import app
import LOGGER
import DOWNLOAD_DIR
import get_client
import premium_session
import config_dict
import user_data
from exceptions import NotSupportedExtractionArchive
from bot import aria2

ARCH_EXT: Final = [
    ".tar.bz2", ".tar.gz", ".bz2", ".gz", ".tar.xz", ".tar", ".tbz2", ".tgz", ".lzma2",
    ".zip", ".7z", ".z", ".rar", ".iso", ".wim", ".cab", ".apm", ".arj", ".chm",
    ".cpio", ".cramfs", ".deb", ".dmg", ".fat", ".hfs", ".lzh", ".lzma", ".mbr",
    ".msi", ".mslz", ".nsis", ".ntfs", ".rpm", ".squashfs", ".udf", ".vhd", ".xar"
]

def clean_target(path: pathlib.Path):
    if path.exists():
        LOGGER.info(f"Cleaning Target: {path}")
        shutil.rmtree(path, ignore_errors=True)

def clean_download(path: pathlib.Path):
    if path.exists():
        LOGGER.info(f"Cleaning Download: {path}")
        shutil.rmtree(path, ignore_errors=True)

def start_cleanup():
    get_client().torrents_delete(torrent_hashes="all")
    shutil.rmtree(DOWNLOAD_DIR, ignore_errors=True)
    DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)

def clean_all():
    aria2.remove_all(True)
    get_client().torrents_delete(torrent_hashes="all")
    app.stop()
    if premium_session: premium_session.stop()
    shutil.rmtree(DOWNLOAD_DIR, ignore_errors=True)

def exit_clean_up(signal, frame):
    try:
        LOGGER.info("Please wait, while we clean up the downloads and stop running downloads")
        clean_all()
        sys.exit(0)
    except KeyboardInterrupt:
        LOGGER.warning("Force Exiting before the cleanup finishes!")
        sys.exit(1)

def clean_unwanted(path: pathlib.Path):
    LOGGER.info(f"Cleaning unwanted files/folders: {path}")
    for dirpath in path.rglob(".unwanted"):
        shutil.rmtree(dirpath, ignore_errors=True)
    for dirpath in path.rglob("splited_files_wz"):
        shutil.rmtree(dirpath, ignore_errors=True)
    for dirpath in path.rglob("*.!qB"):
        dirpath.unlink(missing_ok=True)
    for dirpath in path.rglob(".parts"):
        if dirpath.name.startswith("."):
            dirpath.unlink(missing_ok=True)

def get_path_size(path: pathlib.Path) -> int:
    if path.is_file():
        return path.stat().st_size
    total_size = 0
    for child in path.glob("*"):
        total_size += get_path_size(child)
    return total_size

def check_storage_threshold(size: int, arch: bool = False, alloc: bool = False) -> bool:
    if not alloc:
        if not arch:
            free_space = shutil.disk_usage(DOWNLOAD_DIR).free
            return free_space - size > config_dict["STORAGE_THRESHOLD"] * 1024**3
        else:
            free_space = shutil.disk_usage(DOWNLOAD_DIR).free
            return free_space - (size * 2) > config_dict["STORAGE_THRESHOLD"] * 1024**3
    else:
        if not arch:
            free_space = shutil.disk_usage(DOWNLOAD_DIR).free
            return free_space > config_dict["STORAGE_THRESHOLD"] * 1024**3
        else:
            free_space = shutil.disk_usage(DOWNLOAD_DIR).free
            return free_space - size > config_dict["STORAGE_THRESHOLD"] * 1024**3

@lru_cache(maxsize=None)
def get_base_name(orig_path: str) -> str:
    ext = [ext for ext in ARCH_EXT if orig_path.lower().endswith(ext)]
    if ext:
        ext = ext[0]
        return re.split(f'{ext}$', orig_path, maxsplit=1, flags=re.IGNORECASE)[0]
    else:
        raise NotSupportedExtractionArchive("File format not supported for extraction")

def get_mime_type(file_path: pathlib.Path) -> str:
    mime = magic.Magic(mime=True)
    mime_type = mime.from_file(file_path)
    mime_type = mime_type or "text/plain"
    return mime_type

def take_ss(video_file: pathlib.Path, duration: Optional[int] = None) -> Optional[pathlib.Path]:
    des_dir = pathlib.Path("Thumbnails")
    des_dir.mkdir(parents=True, exist_ok=True)
    des_dir = des_dir / f"{time()}.jpg"
    if duration is None:
        duration = get_media_info(video_file)[0]
    if duration == 0:
        duration = 3
    duration = duration // 2

    args = [
        "ffmpeg", "-hide_banner", "-loglevel", "error", "-ss", str(duration),
        "-i", str(video_file), "-frames:v", "1", str(des_dir)
    ]
    result = subprocess.run(args, capture_output=True, text=True)
    if result.returncode != 0:
        return None

    with Image.open(des_dir) as img:
        img.convert("RGB").save(des_dir, "JPEG")

    return des_dir

def split_file(path: pathlib.Path, size: int, file_: str, dirpath: pathlib.Path, split_size: int, listener, start_time: int = 0, i: int = 1, inLoop: bool = False, noMap: bool = False) -> bool:
    if listener.seed and not listener.newDir:
        dirpath = dirpath / "splited_files_wz"
        dirpath.mkdir(parents=True, exist_ok=True)
    user_id = listener.message.from_user.id
    user_dict = user_data.get(user_id, False)
    leech_split_size = int((user_dict and user_dict.get('split_size')) or config_dict['TG_SPLIT_SIZE'])
    parts = math.ceil(size/leech_split_size)
    if ((user_dict and user_dict.get('equal_splits')) or config_dict['EQUAL_SPLITS']) and not inLoop:
        split_size = math.ceil(size/parts) + 1000
    if get_media_streams(path)[0]:
        duration = get_media_info(path)[0]
        base_name, extension = os.path.splitext(file_)
        split_size = split_size - 5000000
        for i, _ in enumerate(range(parts)):
            parted_name = f"{str(base_name)}.part{str(i+1).zfill(3)}{str(extension)}"
            out_path = dirpath / parted_name
            args = [
                "ffmpeg", "-hide_banner", "-loglevel", "error", "-ss", str(start_time),
                "-i", str(path), "-fs", str(split_size), "-map", "0", "-map_chapters", "-1",
                "-c", "copy", str(out_path)
            ]
            if not noMap:
                args.append("-map_metadata")
                args.append("-1")
            result = subprocess.run(args, capture_output=True, text=True)
            if result.returncode == -9:
                return False
            elif result.returncode != 0 and not noMap:
                LOGGER.warning(f"Retrying without map, -map 0 not working in all situations. Path: {path}")
                out_path.unlink(missing_ok=True)
                return split_file(path, size, file_, dirpath, split_size, listener, start_time, i, True, True)
            elif result.returncode != 0:
                LOGGER.warning(f"Unable to split this video, if it's size less than {config_dict['TG_SPLIT_SIZE']} will be uploaded as it is. Path: {path}")
                out_path.unlink(missing_ok=True)
                return "errored"
            out_size = out_path.stat().st_size
            if out_size > (config_dict['TG_SPLIT_SIZE'] + 1000):
                dif = out_size - (config_dict['TG_SPLIT_SIZE'] + 1000)
                split_size = split_size - dif + 5000000
                out_path.unlink(missing_ok=True)
                return split_file(path, size, file_, dirpath, split_size, listener, start_time, i, True, noMap)
            lpd = get_media_info(out_path)[0]
            if lpd == 0:
                LOGGER.error(f'Something went wrong while splitting mostly file is corrupted. Path: {path}')
                break
            elif duration == lpd:
                if not noMap:
                    LOGGER.warning(f"Retrying without map, -map 0 not working in all situations. Path: {path}")
                    out_path.unlink(missing_ok=True)
                    return split_file(path, size, file_, dirpath, split_size, listener, start_time, i, True, True)
                else:
                    LOGGER.warning(f"This file has been splitted with default stream and audio, so you will only see one part with less size from orginal one because it doesn't have all streams and audios. This happens mostly with MKV videos. noMap={noMap}. Path: {path}")
                    break
            elif lpd <= 4:
                out_path.unlink(missing_ok=True)
                break
            start_time += lpd - 3
    else:
        out_path = dirpath / f"{file_}."
        args = [
            "split", "--numeric-suffixes=1", "--suffix-length=3",
            f"--bytes={split_size}", str(path), str(out_path)
        ]
        result = subprocess.run(args, capture_output=True, text=True)
        if result.returncode == -9:
            return False
    return True

@lru_cache(maxsize=None)
def get_media_info(path: pathlib.Path) -> Tuple[int, Optional[str], Optional[str]]:
    try:
        result = subprocess.check_output(
            ["ffprobe", "-hide_banner", "-loglevel", "error", "-print_format", "json", "-show_format", "-show_streams", str(path)],
            stderr=subprocess.STDOUT
        ).decode('utf-8')
    except Exception as e:
        LOGGER.error(f'{e}. Mostly file not found!')
        return 0, None, None

    fields = eval(result).get('format')
    if fields is None:
        LOGGER.error(f"get_media_info: {result}")
        return 0, None, None

    duration = round(float(fields.get('duration', 0)))

    fields = fields.get('tags')
    if fields:
        artist = fields.get('artist')
        if artist is None:
            artist = fields.get('ARTIST')
        title = fields.get('title')
        if title is None:
            title = fields.get('TITLE')
    else:
        title = None
        artist = None

    return duration, artist, title

@lru_cache(maxsize=None)
def get_media_streams(path: pathlib.Path) -> Tuple[bool, bool]:
    is_video = False
    is_audio = False

    mime_type = get_mime_type(path)
    if mime_type.startswith('audio'):
        is_audio = True
        return is_video, is_audio

    if not mime_type.startswith('video'):
        return is_video, is_audio

    try:
        result = subprocess.check_output(
            ["ffprobe", "-hide_banner", "-loglevel", "error", "-print_format", "json", "-show_streams", str(path)],
            stderr=subprocess.STDOUT
        ).decode('utf-8')
    except Exception as e:
        LOGGER.error(f'{e}. Mostly file not found!')
        return is_video, is_audio

    fields = eval(result).get('streams')
    if fields is None:
        LOGGER.error(f"get_media_streams: {result}")
        return is_video, is_audio

    for stream in fields:
        if stream.get('codec_type') == 'video':
            is_video = True
        elif stream.get('codec_type') == 'audio':
            is_audio = True
    return is_video, is_audio

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Take screenshot from video file")
    parser.add_argument("video_file", help="Path to video file")
    parser.add_argument("-d", "--duration", type=int, help="Duration in seconds for screenshot")
    args = parser.parse_args()
    take_ss(pathlib.Path(args.video_file), args.duration)
