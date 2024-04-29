from typing import Dict, List, Union, Optional, Tuple, Callable
from random import SystemRandom
from string import ascii_letters, digits

import logging
import math

from bot import download_dict, download_dict_lock, LOGGER, user_data, config_dict, OWNER_ID, non_queued_dl, non_queued_up, queued_dl, queue_dict_lock
from bot.helper.mirror_utils.upload_utils.gdriveTools import GoogleDriveHelper
from bot.helper.mirror_utils.status_utils.gd_download_status import GdDownloadStatus
from bot.helper.mirror_utils.status_utils.queue_status import QueueStatus
from bot.helper.telegram_helper.message_utils import sendMessage, sendStatusMessage, sendFile
from bot.helper.ext_utils.bot_utils import get_readable_file_size, is_sudo, is_paid, getdailytasks, userlistype
from bot.helper.ext_utils.fs_utils import get_base_name, check_storage_threshold

# Constants
STOP_DUPLICATE = config_dict['STOP_DUPLICATE']
TORRENT_DIRECT_LIMIT = config_dict['TORRENT_DIRECT_LIMIT']
ZIP_UNZIP_LIMIT = config_dict['ZIP_UNZIP_LIMIT']
LEECH_LIMIT = config_dict['LEECH_LIMIT']
STORAGE_THRESHOLD = config_dict['STORAGE_THRESHOLD']
DAILY_MIRROR_LIMIT = config_dict['DAILY_MIRROR_LIMIT'] * 1024**3 if config_dict['DAILY_MIRROR_LIMIT'] else config_dict['DAILY_MIRROR_LIMIT']
DAILY_LEECH_LIMIT = config_dict['DAILY_LEECH_LIMIT'] * 1024**3 if config_dict['DAILY_LEECH_LIMIT'] else config_dict['DAILY_LEECH_LIMIT']
PAID_SERVICE = config_dict['PAID_SERVICE']
QUEUE_ALL = config_dict['QUEUE_ALL']
QUEUE_DOWNLOAD = config_dict['QUEUE_DOWNLOAD']
SAME_ACC_COOKIES = config_dict['SAME_ACC_COOKIES']

def add_gd_download(
    link: str,
    path: str,
    listener: Callable,
    newname: Optional[str] = None,
    is_gdtot: bool = False,
    is_udrive: bool = False,
    is_sharer: bool = False,
    is_sharedrive: bool = False,
    is_filepress: bool = False,
    from_queue: bool = False
) -> Optional[str]:
    """
    Adds a download task to the queue and starts it if there are no queue limits.

    Args:
        link (str): The Google Drive link to download.
        path (str): The path to save the downloaded file.
        listener (Callable): The listener function to be called when the download starts and finishes.
        newname (Optional[str]): The new name for the downloaded file.
        is_gdtot (bool): Whether the link is a Google Drive to Google Drive link.
        is_udrive (bool): Whether the link is an upload link from User Drive.
        is_sharer (bool): Whether the link is a shared link from User Drive.
        is_sharedrive (bool): Whether the link is a shared link from Google Drive.
        is_filepress (bool): Whether the link is a FilePress link.
        from_queue (bool): Whether the download is started from the queue.

    Returns:
        Optional[str]: The error message if there is an error, None otherwise.
    """
    res, size, name, files = GoogleDriveHelper().helper(link)
    if res:
        return sendMessage(res, listener.bot, listener.message)

    user_id = listener.message.from_user.id
    user_dict = user_data.get(user_id, False)
    IS_USRTD = user_dict.get('is_usertd') if user_dict else False

    if STOP_DUPLICATE and not listener.isLeech and not IS_USRTD:
        LOGGER.info('Checking File/Folder if already in Drive...')
        gname = f"{name}.zip" if listener.isZip else get_base_name(name) if listener.extract else name
        if gname:
            gmsg, button = GoogleDriveHelper(user_id=user_id).drive_list(gname, True)
            if gmsg:
                tegr, html, tgdi = userlistype(user_id)
                if tegr:
                    return sendMessage("File/Folder is already available in Drive.\nHere are the search results:", listener.bot, listener.message, button)
                elif html:
                    return sendFile(listener.bot, listener.message, button, f"File/Folder is already available in Drive. Here are the search results:\n\n{gmsg}")
                else: return sendMessage(gmsg, listener.bot, listener.message, button)

    limits = [TORRENT_DIRECT_LIMIT, ZIP_UNZIP_LIMIT, LEECH_LIMIT, STORAGE_THRESHOLD]
    limits_names = ['TORRENT_DIRECT_LIMIT', 'ZIP_UNZIP_LIMIT', 'LEECH_LIMIT', 'STORAGE_THRESHOLD']
    user_limits = [getattr(config_dict, lim) for lim in limits_names]
    user_id_not_owner = user_id != OWNER_ID
    user_not_sudo = not is_sudo(user_id)
    user_not_paid = not is_paid(user_id)
    if any(limits) and user_id_not_owner and user_not_sudo and user_not_paid:
        arch = any([listener.extract, listener.isZip])
        limit = None
        if STORAGE_THRESHOLD:
            acpt = check_storage_threshold(size, arch)
            if not acpt:
                msg = f'You must leave {STORAGE_THRESHOLD}GB free storage.'
                msg += f'\nYour File/Folder size is {get_readable_file_size(size)}'
                if PAID_SERVICE:
                    msg += f'\n#Buy Paid Service'
                return sendMessage(msg, listener.bot, listener.message)
        if ZIP_UNZIP_LIMIT and arch:
            mssg = f'Zip/Unzip limit is {ZIP_UNZIP_LIMIT}GB'
            limit = ZIP_UNZIP_LIMIT
        if LEECH_LIMIT and listener.isLeech:
            mssg = f'Leech limit is {LEECH_LIMIT}GB'
            limit = LEECH_LIMIT
        elif TORRENT_DIRECT_LIMIT:
            mssg = f'Torrent/Direct limit is {TORRENT_DIRECT_LIMIT}GB'
            limit = TORRENT_DIRECT_LIMIT
        if PAID_SERVICE:
            mssg += f'\n#Buy Paid Service'
        if limit is not None:
            LOGGER.info('Checking File/Folder Size...')
            if size > limit * 1024**3:
                msg = f'{mssg}.\nYour File/Folder size is {get_readable_file_size(size)}.'
                return sendMessage(msg, listener.bot, listener.message)

    daily_mirror_limit = DAILY_MIRROR_LIMIT if DAILY_MIRROR_LIMIT else None
    daily_leech_limit = DAILY_LEECH_LIMIT if DAILY_LEECH_LIMIT else None
    if (daily_mirror_limit or daily_leech_limit) and user_id_not_owner and not is_sudo(user_id) and not is_paid(user_id):
        daily_tasks = getdailytasks(user_id)
        if daily_mirror_limit and not listener.isLeech:
            daily_mirror_size = daily_tasks['mirror']
            if daily_mirror_size is not None and (size >= (daily_mirror_limit - daily_mirror_size) or daily_mirror_limit <= daily_mirror_size):
                mssg = f'Daily Mirror Limit is {get_readable_file_size(daily_mirror_limit)}\nYou have exhausted all your Daily Mirror Limit or File Size of your Mirror is greater than your free Limits.\nTRY AGAIN TOMORROW'
                if PAID_SERVICE:
                    mssg += f'\n#Buy Paid Service'
                return sendMessage(mssg, listener.bot, listener.message)
        if daily_leech_limit and listener.isLeech:
            daily_leech_size = daily_tasks['leech']
            if daily_leech_size is not None and (size >= (daily_leech_limit - daily_leech_size) or daily_leech_limit <= daily_leech_size):
                mssg = f'Daily Leech Limit is {get_readable_file_size(daily_leech_limit)}\nYou have exhausted all your Daily Leech Limit or File Size of your Leech is greater than your free Limits.\nTRY AGAIN TOMORROW'
                if PAID_SERVICE:
                    mssg += f'\n#Buy Paid Service'
                return sendMessage(mssg, listener.bot, listener.message)

    gid = ''.join(SystemRandom().choices(ascii_letters + digits, k=12))
    all_limit = QUEUE_ALL
    dl_limit = QUEUE_DOWNLOAD
    if all_limit or dl_limit:
        added_to_queue = False
        with queue_dict_lock:
            dl = len(non_queued_dl)
            up = len(non_queued_up)
            if (all_limit and dl + up >= all_limit and (not dl_limit or dl >= dl_limit)) or (dl_limit and dl >= dl_limit):
                added_to_queue = True
                queued_dl[listener.uid] = [
                    'gd', link, path, listener, newname, is_gdtot, is_udrive, is_sharer, is_sharedrive, is_filepress]
        if added_to_queue:
            LOGGER.info(f"Added to Queue/Download: {name}")
            with download_dict_lock:
                download_dict[listener.uid] = QueueStatus(name, size, gid, listener, 'Dl')
            listener.onDownloadStart()
            sendStatusMessage(listener.message, listener.bot)
            return

    drive = GoogleDriveHelper(name, path, size, listener)
    with download_dict_lock:
        download_dict[listener.uid] = GdDownloadStatus(drive, size, listener, gid)
    with queue_dict_lock:
        non_queued_dl.add(listener.uid)

    if not from_queue:
        LOGGER.info(f"Download from GDrive: {name}")
        listener.onDownloadStart()
        sendStatusMessage(listener.message, listener.bot)
    else:
        LOGGER.info(f'Start Queued Download from GDrive: {name}')

    try:
        drive.download(link)
    except Exception as e:
        logging.error(f"Error downloading file from GDrive: {e}")
        return str(e)

    if SAME_ACC_COOKIES:
        if (is_gdtot or is_udrive or is_sharer or is_sharedrive):
            drive.deletefile(link)

    return None
