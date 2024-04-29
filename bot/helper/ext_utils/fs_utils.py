import os
import asyncio
import pathlib as plib
from typing import List, Tuple, Union

import aiofiles.os
import aioshutil
import shutil
import magic
import re
import subprocess
from aiohttp import ClientSession
from bot.helper.ext_utils.bot_utils import sync_to_async

from .exceptions import NotSupportedExtractionArchive
from bot import aria2, LOGGER, DOWNLOAD_DIR, get_client, GLOBAL_EXTENSION_FILTER

ARCH_EXT = [
    ".tar.bz2", ".tar.gz", ".bz2", ".gz", ".tar.xz", ".tar", ".tbz2", ".tgz", ".lzma2",
    ".zip", ".7z", ".z", ".rar", ".iso", ".wim", ".cab", ".apm", ".arj", ".chm",
    ".cpio", ".cramfs", ".deb", ".dmg", ".fat", ".hfs", ".lzh", ".lzma", ".mbr",
    ".msi", ".mslz", ".nsis", ".ntfs", ".rpm", ".squashfs", ".udf", ".vhd", ".xar"
]

FIRST_SPLIT_REGEX = r'(\.|_)part0*1\.rar$|(\.|_)7z\.0*1$|(\.|_)zip\.0*1$|^(?!.*(\.|_)part\d+\.rar$).*\.rar$'
SPLIT_REGEX = r'\.r\d+$|\.7z\.\d+$|\.z\d+$|\.zip\.\d+$'


async def is_first_archive_split(file: str) -> bool:
    """Check if the file is the first split of an archived file."""
    return bool(re.search(FIRST_SPLIT_REGEX, file))


async def is_archive(file: str) -> bool:
    """Check if the file is an archive."""
    return file.endswith(ARCH_EXT)


async def is_archive_split(file: str) -> bool:
    """Check if the file is a split of an archived file."""
    return bool(re.search(SPLIT_REGEX, file))


async def clean_target(path: Union[str, plib.Path]) -> None:
    """Clean the target path."""
    path = plib.Path(path)
    if path.exists():
        LOGGER.info(f"Cleaning Target: {path}")
        if path.is_dir():
            try:
                await aioshutil.rmtree(path)
            except:
                pass
        elif path.is_file():
            try:
                await aiofiles.os.remove(path)
            except:
                pass


async def clean_download(path: Union[str, plib.Path]) -> None:
    """Clean the download path."""
    path = plib.Path(path)
    if path.exists():
        LOGGER.info(f"Cleaning Download: {path}")
        try:
            await aioshutil.rmtree(path)
        except:
            pass


async def start_cleanup() -> None:
    """Start the cleanup process."""
    get_client().torrents_delete(torrent_hashes="all")
    try:
        await aioshutil.rmtree(DOWNLOAD_DIR)
    except:
        pass
    await aiofiles.os.makedirs(DOWNLOAD_DIR)


def clean_all() -> None:
    """Clean all downloads and exit."""
    aria2.remove_all(True)
    get_client().torrents_delete(torrent_hashes="all")
    try:
        shutil.rmtree(DOWNLOAD_DIR)
    except:
        pass


def exit_clean_up(signal, frame) -> None:
    """Clean up and exit."""
    try:
        LOGGER.info(
            "Please wait, while we clean up and stop the running downloads")
        clean_all()
        subprocess.run(['pkill', '-9', '-f', 'gunicorn|aria2c|qbittorrent-nox|ffmpeg'],
                       check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        exit(0)
    except KeyboardInterrupt:
        LOGGER.warning("Force Exiting before the cleanup finishes!")
        exit(1)


async def clean_unwanted(path: Union[str, plib.Path]) -> None:
    """Clean unwanted files and folders."""
    path = plib.Path(path)
    LOGGER.info(f"Cleaning unwanted files/folders: {path}")
    async for dirpath, _, files in sync_to_async(path.rglob, path, topdown=False):
        for filee in files:
            if filee.endswith(".!qB") or filee.endswith('.parts') and filee.startswith('.'):
                await aiofiles.os.remove(dirpath / filee)
        if dirpath.name in (".unwanted", "splited_files_mltb", "copied_mltb"):
            await aioshutil.rmtree(dirpath)
    for dirpath, _, files in await sync_to_async(path.rglob, path, topdown=False):
        if not await asyncio.gather(*(aiofiles.os.path.exists(p) for p in dirpath.glob("*"))):
            await aioshutil.rmtree(dirpath)


async def get_path_size(path: Union[str, plib.Path]) -> int:
    """Get the size of the path."""
    path = plib.Path(path)
    if path.is_file():
        return await aiofiles.os.stat(path).size
    total_size = 0
    async for dirpath, _, files in sync_to_async(path.rglob, path, topdown=False):
        for f in files:
            abs_path = dirpath / f
            total_size += await aiofiles.os.stat(abs_path).size
    return total_size


async def count_files_and_folders(path: Union[str, plib.Path]) -> Tuple[int, int]:
    """Count the number of files and folders in the path."""
    path = plib.Path(path)
    total_files = 0
    total_folders = 0
    async for _, dirs, files in sync_to_async(path.rglob, path, topdown=False):
        total_files += len(files)
        for f in files:
            if f.endswith(tuple(GLOBAL_EXTENSION_FILTER)):
                total_files -= 1
        total_folders += len(dirs)
    return total_folders, total_files


def get_base_name(orig_path: str) -> str:
    """Get the base name of the file."""
    extension = next(
        (ext for ext in ARCH_EXT if orig_path.lower().endswith(ext)), ''
    )
    if extension != '':
        return re.split(f'{extension}$', orig_path, maxsplit=1, flags=re.IGNORECASE)[0]
    else:
        raise NotSupportedExtractionArchive(
            'File format not supported for extraction')


def get_mime_type(file_path: str) -> str:
    """Get the mime type of the file."""
    mime = magic.Magic(mime=True)
    mime_type = mime.from_file(file_path)
    mime_type = mime_type or "text/plain"
    return mime_type


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


async def join_files(path: Union[str, plib.Path]) -> None:
    """Join the split files."""
    path = plib.Path(path)
    files = await asyncio.gather(*(aiofiles.os.listdir(path)))
    results = []
    for file_ in files:
        if re.search(r"\.0+2$", file_) and await sync_to_async(get_mime_type, str(path / file_)) == 'application/octet-stream':
            final_name = file_.rsplit('.', 1)[0]
            cmd = f'cat {path}/{final_name}.* > {path}/{final_name}'
            _, stderr, code = await sync_to_async(subprocess.run, cmd, shell=True, capture_output=True)
            if code != 0:
                LOGGER.error(f'Failed to join {final_name}, stderr: {stderr.decode()}')
            else:
                results.append(final_name)
    if results:
        for res in results:
            for file_ in files:
                if re.search(fr"{res}\.0[0-9]+$", file_):
                    await aiofiles.os.remove(path / file_)
