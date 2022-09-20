from random import SystemRandom
from string import ascii_letters, digits
from bot import TELEGRAPH_STYLE, download_dict, download_dict_lock, ZIP_UNZIP_LIMIT, LOGGER, STOP_DUPLICATE, STORAGE_THRESHOLD, TORRENT_DIRECT_LIMIT, LEECH_LIMIT
from bot.helper.mirror_utils.upload_utils.gdriveTools import GoogleDriveHelper
from bot.helper.mirror_utils.status_utils.gd_download_status import GdDownloadStatus
from bot.helper.telegram_helper.message_utils import sendMessage, sendStatusMessage, sendMarkup, sendFile
from bot.helper.ext_utils.bot_utils import get_readable_file_size
from bot.helper.ext_utils.fs_utils import get_base_name, check_storage_threshold


def add_gd_download(link, path, listener, is_gdtot, is_unified, is_udrive, newname):
    res, size, name, files = GoogleDriveHelper().helper(link)
    if res != "":
        return sendMessage(res, listener.bot, listener.message)
    if newname:
        name = newname
    if STOP_DUPLICATE and not listener.isLeech:
        LOGGER.info('Checking File/Folder if already in Drive...')
        if listener.isZip:
            gname = f"{name}.zip"
        elif listener.extract:
            try:
                gname = get_base_name(name)
            except:
                gname = None
        if gname is not None:
            if TELEGRAPH_STYLE is True:
                gmsg, button = GoogleDriveHelper().drive_list(gname, True)
                if gmsg:
                    msg = "File/Folder is already available in Drive.\nHere are the search results:"
                    return sendMarkup(msg, listener.bot, listener.message, button)

            else:
                cap, f_name = GoogleDriveHelper().drive_list(gname, True)
                if cap:
                    cap = f"File/Folder is already available in Drive. Here are the search results:\n\n{cap}"
                    sendFile(listener.bot, listener.message, f_name, cap)
                    return
    if any([ZIP_UNZIP_LIMIT, STORAGE_THRESHOLD, TORRENT_DIRECT_LIMIT, LEECH_LIMIT]):
        arch = any([listener.extract, listener.isZip])
        limit = None
        if STORAGE_THRESHOLD is not None:
            acpt = check_storage_threshold(size, arch)
            if not acpt:
                msg = f'You must leave {STORAGE_THRESHOLD}GB free storage.'
                msg += f'\nYour File/Folder size is {get_readable_file_size(size)}'
                return sendMessage(msg, listener.bot, listener.message)
        if ZIP_UNZIP_LIMIT is not None and arch:
            mssg = f'Zip/Unzip limit is {ZIP_UNZIP_LIMIT}GB'
            limit = ZIP_UNZIP_LIMIT
        if LEECH_LIMIT is not None and listener.isLeech:
            mssg = f'Leech limit is {LEECH_LIMIT}GB'
            limit = LEECH_LIMIT
        elif TORRENT_DIRECT_LIMIT is not None:
            mssg = f'Torrent/Direct limit is {TORRENT_DIRECT_LIMIT}GB'
            limit = TORRENT_DIRECT_LIMIT
        if limit is not None:
            LOGGER.info('Checking File/Folder Size...')
            if size > limit * 1024**3:
                msg = f'{mssg}.\nYour File/Folder size is {get_readable_file_size(size)}.'
                return sendMessage(msg, listener.bot, listener.message)
    LOGGER.info(f"Download Name: {name}")
    drive = GoogleDriveHelper(name, path, size, listener)
    gid = ''.join(SystemRandom().choices(ascii_letters + digits, k=12))
    download_status = GdDownloadStatus(drive, size, listener, gid)
    with download_dict_lock:
        download_dict[listener.uid] = download_status
    listener.onDownloadStart()
    sendStatusMessage(listener.message, listener.bot)
    drive.download(link)
    if (is_gdtot or is_unified or is_udrive):
        drive.deletefile(link)