import os
import sys
import warnings
import pathlib
import asyncio
import aiofiles.os
import aioshutil
import shutil
import magic
import re
import subprocess
from aiofiles.os import remove as aioremove
from aioshutil import rmtree as aiormtree
from bot.exceptions import NotSupportedExtractionArchive
from bot import aria2, DOWNLOAD_DIR, get_client, GLOBAL_EXTENSION_FILTER
from bot.helper.ext_utils.bot_utils import sync_to_async, cmd_exec

ARCH_EXT = [
    ".tar.bz2", ".tar.gz", ".bz2", ".gz", ".tar.xz", ".tar", ".tbz2", ".tgz", ".lzma2",
    ".zip", ".7z", ".z", ".rar", ".iso", ".wim", ".cab", ".apm", ".arj", ".chm",
    ".cpio", ".cramfs", ".deb", ".dmg", ".fat", ".hfs", ".lzh", ".lzma", ".mbr",
    ".msi", ".mslz", ".nsis", ".ntfs", ".rpm", ".squashfs", ".udf", ".vhd", ".xar"
]

FIRST_SPLIT_REGEX = re.compile(r'(\.|_)part0*1\.rar$|(\.|_)7z\.0*1$|(\.|_)zip\.0*1$|^(?!.*(\.|_)part\d+\.rar$).*\.rar$')
SPLIT_REGEX = re.compile(r'\.r\d+$|\.7z\.\d+$|\.z\d+$|\.zip\.\d+$')


def is_first_archive_split(file: str) -> bool:
    """Check if the file is the first split of an archived file."""
    return bool(FIRST_SPLIT_REGEX.search(file))


def is_archive(file: str) -> bool:
    """Check if the file is an archive."""
    return file.endswith(tuple(ARCH_EXT))


def is_archive_split(file: str) -> bool:
    """Check if the file is a split of an archived file."""
    return bool(SPLIT_REGEX.search(file))


async def clean_target(path: pathlib.Path) -> None:
    """Clean the target directory."""
    if path.exists():
        print(f"Cleaning Target: {path}")
        if path.is_dir():
            try:
                await aiormtree(path)
            except Exception:
                pass
        elif path.is_file():
            try:
                await aioremove(path)
            except Exception:
                pass


async def clean_download(path: pathlib.Path) -> None:
    """Clean the download directory."""
    if path.exists():
        print(f"Cleaning Download: {path}")
        try:
            await aiormtree(path)
        except Exception:
            pass


async def start_cleanup() -> None:
    """Start the cleanup process."""
    get_client().torrents_delete(torrent_hashes="all")
    try:
        await aiormtree(DOWNLOAD_DIR)
    except Exception:
        pass
    await asyncio.gather(
        aiofiles.os.makedirs(DOWNLOAD_DIR, exist_ok=True),
        aria2.remove_all(True)
    )


def clean_all() -> None:
    """Clean all downloads and the download directory."""
    aria2.remove_all(True)
    get_client().torrents_delete(torrent_hashes="all")
    try:
        shutil.rmtree(DOWNLOAD_DIR)
    except Exception:
        pass


def exit_clean_up(signal, frame) -> None:
    """Clean up and exit the program."""
    try:
        print("Please wait, while we clean up and stop the running downloads")
        clean_all()
        subprocess.run(['pkill', '-9', '-f', 'gunicorn|aria2c|qbittorrent-nox|ffmpeg'], check=True)
        sys.exit(0)
    except KeyboardInterrupt:
        print("Force Exiting before the cleanup finishes!")
        sys.exit(1)


async def clean_unwanted(path: pathlib.Path) -> None:
    """Clean unwanted files and folders."""
    print(f"Cleaning unwanted files/folders: {path}")
    for dirpath, dirs, files in path.rglob("*.!qB"):
        await aiofiles.os.remove(dirpath)
    for dirpath, dirs, files in path.rglob("*.parts"):
        if files and files[0].startswith('.'):
            await aiofiles.os.remove(dirpath / files[0])
    for dirpath in path.glob(".unwanted"):
        await aioshutil.rmtree(dirpath)
    for dirpath in path.glob("splited_files_mltb"):
        await aioshutil.rmtree(dirpath)
    for dirpath in path.glob("copied_mltb"):
        await aioshutil.rmtree(dirpath)
    for dirpath, dirs, files in path.rglob("*"):
        if not files:
            await aiofiles.os.rmdir(dirpath)


async def get_path_size(path: pathlib.Path) -> int:
    """Get the size of the path."""
    if path.is_file():
        return path.stat().st_size
    total_size = 0
    for child in path.glob("*"):
        total_size += await get_path_size(child)
    return total_size


async def count_files_and_folders(path: pathlib.Path) -> tuple[int, int]:
    """Count the number of files and folders in the path."""
    total_files = 0
    total_folders = 0
    for child in path.glob("*"):
        if child.is_file():
            total_files += 1
            if child.suffix in GLOBAL_EXTENSION_FILTER:
                total_files -= 1
        elif child.is_dir():
            total_folders += 1
    return total_folders, total_files


def get_base_name(orig_path: str) -> str:
    """Get the base name of the file."""
    extension = next(
        (ext for ext in ARCH_EXT if orig_path.lower().endswith(ext)), ''
    )
    if extension:
        return pathlib.Path(orig_path).with_suffix("").name
    else:
        raise NotSupportedExtractionArchive("File format not supported for extraction")


def get_mime_type(file_path: str) -> str:
    """Get the MIME type of the file."""
    mime = magic.Magic(mime=True)
    mime_type = mime.from_file(file_path)
    return mime_type or "text/plain"


def check_storage_threshold(size: int, threshold: int, arch: bool = False, alloc: bool = False) -> bool:
    """Check if the storage threshold is met."""
    free = shutil.disk_usage(DOWNLOAD_DIR).free
    if not alloc:
        if (not arch and free - size < threshold or arch and free - (size * 2) < threshold):
            return False
    elif not arch:
        if free < threshold:
            return False
    elif free - size < threshold:
        return False
    return True


async def join_files(path: pathlib.Path) -> None:
    """Join the split files."""
    files = await path.glob("*")
    results = []
    for file_ in files:
        if file_.suffix == ".02" and file_.stat().st_size == 0:
            final_name = file_.with_suffix("").name
            cmd = f"cat {final_name}.* > {final_name}"
            _, stderr, code = await cmd_exec(cmd, True)
            if code != 0:
                print(f"Failed to join {final_name}, stderr: {stderr}")
            else:
                results.append(final_name)
        else:
            print("No binary files to join!")
    if results:
        print("Join Completed!")
        for res in results:
            for file_ in files:
                if file_.name.startswith(f"{res}.0"):
                    await aiofiles.os.remove(file_)
