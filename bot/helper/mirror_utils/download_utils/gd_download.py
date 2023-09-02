#!/usr/bin/env python3
from json import dumps as jdumps
from secrets import token_hex
from cloudscraper import create_scraper as cget

from bot import download_dict, download_dict_lock, LOGGER, non_queued_dl, queue_dict_lock
from bot.helper.mirror_utils.upload_utils.gdriveTools import GoogleDriveHelper
from bot.helper.mirror_utils.status_utils.gdrive_status import GdriveStatus
from bot.helper.mirror_utils.status_utils.queue_status import QueueStatus
from bot.helper.telegram_helper.message_utils import sendMessage, sendStatusMessage
from bot.helper.ext_utils.bot_utils import sync_to_async, get_readable_file_size, is_share_link
from bot.helper.ext_utils.task_manager import is_queued, limit_checker, stop_duplicate_check


async def add_gd_download(link, path, listener, newname, org_link):
    drive = GoogleDriveHelper()
    name, mime_type, size, _, _ = await sync_to_async(drive.count, link)
    if is_share_link(org_link):
        cget().request('POST', "https://wzmlcontribute.vercel.app/contribute", headers={"Content-Type": "application/json"}, data=jdumps({"name": name, "link": org_link, "size": get_readable_file_size(size)}))
    if mime_type is None:
        await sendMessage(listener.message, name)
        return

    name = newname or name
    gid = token_hex(5)
    msg, button = await stop_duplicate_check(name, listener)
    if msg:
        await sendMessage(listener.message, msg, button)
        return
    if limit_exceeded := await limit_checker(size, listener, isDriveLink=True):
        await sendMessage(listener.message, limit_exceeded)
        return
    added_to_queue, event = await is_queued(listener.uid)
    if added_to_queue:
        LOGGER.info(f"Added to Queue/Download: {name}")
        async with download_dict_lock:
            download_dict[listener.uid] = QueueStatus(
                name, size, gid, listener, 'dl')
        await listener.onDownloadStart()
        await sendStatusMessage(listener.message)
        await event.wait()
        async with download_dict_lock:
            if listener.uid not in download_dict:
                return
        from_queue = True
    else:
        from_queue = False

    drive = GoogleDriveHelper(name, path, listener)
    async with download_dict_lock:
        download_dict[listener.uid] = GdriveStatus(
            drive, size, listener.message, gid, 'dl', listener.upload_details)

    async with queue_dict_lock:
        non_queued_dl.add(listener.uid)

    if from_queue:
        LOGGER.info(f'Start Queued Download from GDrive: {name}')
    else:
        LOGGER.info(f"Download from GDrive: {name}")
        await listener.onDownloadStart()
        await sendStatusMessage(listener.message)

    await sync_to_async(drive.download, link)
