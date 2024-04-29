import typing
from json import dumps as jdumps
from random import SystemRandom
from string import ascii_letters, digits
from urllib.parse import is_share_link

import aiohttp
import cloudscraper
from aiohttp import ClientSession
from bot import download_dict, download_dict_lock, LOGGER, non_queued_dl, queue_dict_lock
from bot.helper.mirror_utils.upload_utils.gdriveTools import GoogleDriveHelper
from bot.helper.mirror_utils.status_utils.gdrive_status import GdriveStatus
from bot.helper.mirror_utils.status_utils.queue_status import QueueStatus
from bot.helper.telegram_helper.message_utils import sendMessage, sendStatusMessage
from bot.helper.ext_utils.bot_utils import sync_to_async, get_readable_file_size
from bot.helper.ext_utils.task_manager import is_queued, limit_checker, stop_duplicate_check

async def add_gd_download(
    link: str,
    path: str,
    listener: typing.Any,
    newname: typing.Optional[str] = None,
    org_link: str = "",
) -> None:
    """
    Adds a download task for a Google Drive file.

    :param link: The Google Drive file link.
    :param path: The path to save the file.
    :param listener: The listener object for sending messages and handling events.
    :param newname: The optional new name for the file.
    :param org_link: The original file link (for contribution purposes).
    """
    drive = GoogleDriveHelper()
    try:
        name, mime_type, size, _, _ = await sync_to_async(drive.count, link)
    except aiohttp.ClientError as e:
        LOGGER.error(f"Error while fetching file info: {e}")
        return

    if is_share_link(org_link):
        scraper = cget()
        headers = {"Content-Type": "application/json"}
        data = jdumps({"name": name, "link": org_link, "size": get_readable_file_size(size)})
        try:
            await sync_to_async(scraper.request, "POST", "https://wzmlcontribute.vercel.app/contribute", headers=headers, data=data)
        except aiohttp.ClientError as e:
            LOGGER.error(f"Error while contributing file: {e}")

    if mime_type is None:
        await sendMessage(listener.message, name)
        return

    name = newname or name
    gid = "".join(SystemRandom().choices(ascii_letters + digits, k=12))

    msg, button = await stop_duplicate_check(name, listener)
    if msg:
        await sendMessage(listener.message, msg, button)
        return

    limit_exceeded = await limit_checker(size, listener, isDriveLink=True)
    if limit_exceeded:
        await sendMessage(listener.message, limit_exceeded)
        return

    added_to_queue, event = await is_queued(listener.uid)
    if added_to_queue:
        LOGGER.info(f"Added to Queue/Download: {name}")
        async with download_dict_lock:
            download_dict[listener.uid] = QueueStatus(
                name, size, gid, listener, "dl"
            )
        await listener.onDownloadStart()
        await sendStatusMessage(listener.message)
        await event.wait()
        async with download_dict_lock:
            if listener.uid not in download_dict:
                return
        from_queue = True
    else:
        from_queue = False

    async with ClientSession() as session:
        drive = GoogleDriveHelper(name, path, listener, session=session)
        async with download_dict_lock:
            download_dict[listener.uid] = GdriveStatus(
                drive, size, listener.message, gid, "dl", listener.upload_details
            )

        async with queue_dict_lock:
            non_queued_dl.add(listener.uid)

    if from_queue:
        LOGGER.info(f'Start Queued Download from GDrive: {name}')
    else:
        LOGGER.info(f"Download from GDrive: {name}")
        await listener.onDownloadStart()
        await sendStatusMessage(listener.message)

    try:
        await sync_to_async(drive.download, link)
    except aiohttp.ClientError as e:
        LOGGER.error(f"Error while downloading file: {e}")
