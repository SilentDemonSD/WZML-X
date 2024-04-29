import asyncio
import aiofiles
import aiofiles.os
import aioshutil
import magic
import re
import subprocess
import pathlib
from bot.exceptions import NotSupportedExtractionArchive
from bot import aria2, DOWNLOAD_DIR, get_client, GLOBAL_EXTENSION_FILTER
from bot.helper.ext_utils.bot_utils import sync_to_async, cmd_exec
import os
import logging

# Initialize the logger for this module
logger = logging.getLogger(__name__)

ARCH_EXT = [
    # ... (same as before)
]

# Compile the regular expression pattern for identifying the first split archive
FIRST_SPLIT_REGEX = re.compile(r'(\.|_)part0*1\.rar$|(\.|_)7z\.0*1$|(\.|_)zip\.0*1$|^(?!.*(\.|_)part\d+\.rar$).*\.rar$')

# Compile the regular expression pattern for identifying split archives
SPLIT_REGEX = re.compile(r'\.r\d+$|\.7z\.\d+$|\.z\d+$|\.zip\.\d+$')


async def is_first_archive_split(file: pathlib.Path) -> bool:
    return bool(FIRST_SPLIT_REGEX.search(file.name))


async def is_archive(file: pathlib.Path) -> bool:
    return file.suffix in ARCH_EXT


async def is_archive_split(file: pathlib.Path) -> bool:
    return bool(SPLIT_REGEX.search(file.name))


async def clean_target(path: pathlib.Path) -> None:
    async for item in path.glob("**/*"):
        if item.is_file():
            try:
                await aiofiles.os.remove(item)
            except Exception as e:
                logger.error(f"Error removing file: {e}")
        elif item.is_dir():
            try:
                await aioshutil.rmtree(item)
            except Exception as e:
                logger.error(f"Error cleaning directory: {e}")


async def clean_download(path: pathlib.Path) -> None:
    async for item in path.glob("**/"):
        if item.is_dir():
            try:
                await aioshutil.rmtree(item)
            except Exception as e:
                logger.error(f"Error cleaning download directory: {e}")


async def start_cleanup() -> None:
    try:
        get_client().torrents_delete(torrent_hashes="all")
        await aioshutil.rmtree(DOWNLOAD_DIR)
    except Exception as e:
        logger.error(f"Error cleaning download directory: {e}")

    await asyncio.gather(
        aiofiles.os.makedirs(DOWNLOAD_DIR, exist_ok=True),
        aria2.remove_all(True)
    )


def clean_all() -> None:
    aria2.remove_all(True)
    get_client().torrents_delete(torrent_hashes="all")
    try:
        aioshutil.rmtree(DOWNLOAD_DIR)
    except Exception as e:
        logger.error(f"Error removing download directory: {e}")


async def clean_unwanted(path: pathlib.Path) -> None:
    logger.info(f"Cleaning unwanted files/folders: {path}")
    unwanted_patterns = [
        "*.!qB",
        "*.parts/*",
        ".unwanted/*",
        "splited_files_mltb/*",
        "copied_mltb/*"
    ]

    for pattern in unwanted_patterns:
        async for dirpath in path.glob(pattern):
            try:
                await aioshutil.rmtree(dirpath)
            except Exception as e:
                logger.error(f"Error cleaning unwanted files/folders: {e}")


async def get_path_size(path: pathlib.Path) -> int:
    if not path.exists():
        return 0

    if path.is_file():
        return path.stat().st_size

    total_size = 0
    async for child in path.glob("*"):
        total_size += await get_path_size(child)
    return total_size


async def count_files_and_folders(path: pathlib.Path) -> tuple[int, int]:
    if not path.exists():
        return 0, 0

    total_files = 0
    total_folders = 0
    async for child in path.glob("*"):
        if child.is_file():
            total_files += 1
            if child.suffix in GLOBAL_EXTENSION_FILTER:
                total_files -= 1
        elif child.is_dir():
            total_folders += 1
    return total_folders, total_files


def get_base_name(orig_path: str) -> str:
    extension = next(
        (ext for ext in ARCH_EXT if orig_path.lower().endswith(ext)), ''
    )
    if extension:
        return pathlib.Path(orig_path).with_suffix("").name
    else:
        return orig_path


def get_mime_type(file_path: str) -> str:
    mime = magic.Magic(mime=True)
    mime_type = mime.from_file(file_path)
    return mime_type or "text/plain"


def check_storage_threshold(size: int, threshold: int, arch: bool = False, alloc: bool = False) -> bool:
    stats = os.statvfs(DOWNLOAD_DIR)
    free = stats.f_frsize * stats.f_bavail
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
    files = path.glob("*")
    results = []
    for file_ in files:
        if file_.suffix == ".02" and (await file_.stat()).st_size == 0:
            final_name = file_.with_suffix("").name
            cmd = f"cat {final_name}.* > {final_name}"
            process = await asyncio.create_subprocess_shell(
                cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await process.communicate()
            if process.returncode != 0:
                logger.error(f"Failed to join {final_name}, stderr: {stderr.decode()}")
            else:
                results.append(final_name)
        else:
            logger.info("No binary files to join!")
    if results:
        logger.info("Join Completed!")
        for res in results:
            for file_ in files:
                if file_.name.startswith(f"{res}.0"):
                    await aiofiles.os.remove(file_)


async def main():
    # Add your main function code here
    pass

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
