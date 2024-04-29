import asyncio
import uuid
from typing import Dict, Any, List, Union, AsyncContextManager

import aiohttp
from bot.helper.ext_utils.bot_utils import sync_to_async
from bot.helper.ext_utils.task_manager import is_queued, stop_duplicate_check
from async_timeout import asyncio_timeout

async def async_lock(lock):
    async with lock:
        yield

aria2_options = None
aria2c_global = None
download_dict = {}
download_dict_lock = asyncio.Lock()
non_queued_dl = set()
queue_dict_lock = asyncio.Lock()

class QueueStatus:
    def __init__(self, folder_name, size, gid, listener, status):
        self.folder_name = folder_name
        self.size = size
        self.gid = gid
        self.listener = listener
        self.status = status

class DirectStatus:
    def __init__(self, direct_listener, gid, listener, upload_details):
        self.direct_listener = direct_listener
        self.gid = gid
        self.listener = listener
        self.upload_details = upload_details

class DirectListener:
    @staticmethod
    async def download(contents):
        # implementation here
        pass

async def add_direct_download(
    details: Dict[str, Union[str, int, bool, List[str]]],
    path: str,
    listener,
    folder_name: str = None,
) -> None:
    """
    Adds a direct download to the download queue.

    :param details: A dictionary containing download details.
    :param path: The path to save the download.
    :param listener: The listener object.
    :param folder_name: The name of the folder to save the download.
    :return: None
    """
    if not (contents := details.get("contents")):
        await sendMessage(listener.message, "There is nothing to download!")
        return
    size = details["total_size"]

    if not folder_name:
        folder_name = details["title"]
    download_path = f"{path}/{folder_name}"

    stop_duplicate_msg, stop_duplicate_button = await stop_duplicate_check(folder_name, listener)
    if stop_duplicate_msg:
        await sendMessage(listener.message, stop_duplicate_msg, stop_duplicate_button)
        return

    gid = str(uuid.uuid4())
    is_queued_added, event = await is_queued(listener.uid)
    if is_queued_added:
        LOGGER.info(f"Added to Queue/Download: {folder_name}")
        async with async_lock(download_dict_lock):
            download_dict[listener.uid] = QueueStatus(
                folder_name, size, gid, listener, "dl"
            )
        await listener.onDownloadStart()
        await sendStatusMessage(listener.message)
        await event.wait()
        async with async_lock(download_dict_lock):
            if listener.uid not in download_dict:
                return
    else:
        async with async_lock(download_dict_lock):
            download_dict[listener.uid] = DirectStatus(
                DirectListener(folder_name, size, download_path, listener, aria2_options),
                gid,
                listener,
                listener.upload_details,
            )

        async with async_lock(queue_dict_lock):
            non_queued_dl.add(listener.uid)

        LOGGER.info(f"Download from Direct Download: {folder_name}")
        await listener.onDownloadStart()
        await sendStatusMessage(listener.message)

        try:
            async with async_timeout(120):
                await sync_to_async(DirectListener.download, contents)
        except asyncio.TimeoutError:
            LOGGER.error("Download timed out")
        except Exception as e:
            LOGGER.error(f"Error while downloading: {e}")
        finally:
            async with async_lock(queue_dict_lock):
                non_queued_dl.discard(listener.uid)
