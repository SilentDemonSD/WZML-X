from random import SystemRandom
from string import ascii_letters, digits
from bot import download_dict, download_dict_lock, LOGGER, user_data, config_dict, OWNER_ID, non_queued_dl, non_queued_up, queued_dl, queue_dict_lock
from bot.helper.mirror_utils.upload_utils.gdriveTools import GoogleDriveHelper
from bot.helper.mirror_utils.status_utils.gd_download_status import GdDownloadStatus
from bot.helper.mirror_utils.status_utils.queue_status import QueueStatus
from bot.helper.telegram_helper.message_utils import sendMessage, sendStatusMessage, sendFile
from bot.helper.ext_utils.bot_utils import get_readable_file_size, is_sudo, is_paid, getdailytasks, userlistype
from bot.helper.ext_utils.fs_utils import get_base_name, check_storage_threshold


def add_gd_download(link, path, listener, newname, is_gdtot, is_udrive, is_sharer, is_sharedrive, is_filepress, from_queue=False):
    res, size, name, files = GoogleDriveHelper().helper(link)
    if res != "":
        return sendMessage(res, listener.bot, listener.message)
    if newname:
        name = newname
    user_id = listener.message.from_user.id
    user_dict = user_data.get(user_id, False)
    IS_USRTD = user_dict.get('is_usertd') if user_dict and user_dict.get('is_usertd') else False
    if config_dict['STOP_DUPLICATE'] and not listener.isLeech and IS_USRTD == False:
        LOGGER.info('Checking File/Folder if already in Drive...')
        if listener.isZip:
            gname = f"{name}.zip"
        elif listener.extract:
            try:
                gname = get_base_name(name)
            except:
                gname = None
        if gname is not None:
            gmsg, button = GoogleDriveHelper(user_id=user_id).drive_list(gname, True)
            if gmsg:
                tegr, html, tgdi = userlistype(user_id)
                if tegr:
                    return sendMessage("File/Folder is already available in Drive.\nHere are the search results:", listener.bot, listener.message, button)
                elif html:
                    return sendFile(listener.bot, listener.message, button, f"File/Folder is already available in Drive. Here are the search results:\n\n{gmsg}")
                else: return sendMessage(gmsg, listener.bot, listener.message, button)
                    
    TORRENT_DIRECT_LIMIT = config_dict['TORRENT_DIRECT_LIMIT']
    ZIP_UNZIP_LIMIT = config_dict['ZIP_UNZIP_LIMIT']
    LEECH_LIMIT = config_dict['LEECH_LIMIT']
    STORAGE_THRESHOLD = config_dict['STORAGE_THRESHOLD']
    DAILY_MIRROR_LIMIT = config_dict['DAILY_MIRROR_LIMIT'] * 1024**3 if config_dict['DAILY_MIRROR_LIMIT'] else config_dict['DAILY_MIRROR_LIMIT']
    DAILY_LEECH_LIMIT = config_dict['DAILY_LEECH_LIMIT'] * 1024**3 if config_dict['DAILY_LEECH_LIMIT'] else config_dict['DAILY_LEECH_LIMIT']
    if any([ZIP_UNZIP_LIMIT, STORAGE_THRESHOLD, TORRENT_DIRECT_LIMIT, LEECH_LIMIT]) and user_id != OWNER_ID and not is_sudo(user_id) and not is_paid(user_id):
        arch = any([listener.extract, listener.isZip])
        limit = None
        if STORAGE_THRESHOLD:
            acpt = check_storage_threshold(size, arch)
            if not acpt:
                msg = f'You must leave {STORAGE_THRESHOLD}GB free storage.'
                msg += f'\nYour File/Folder size is {get_readable_file_size(size)}'
                if config_dict['PAID_SERVICE'] is True:
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
        if config_dict['PAID_SERVICE'] is True:
            mssg += f'\n#Buy Paid Service'
        if limit is not None:
            LOGGER.info('Checking File/Folder Size...')
            if size > limit * 1024**3:
                msg = f'{mssg}.\nYour File/Folder size is {get_readable_file_size(size)}.'
                return sendMessage(msg, listener.bot, listener.message)
    if DAILY_MIRROR_LIMIT and not listener.isLeech and user_id != OWNER_ID and not is_sudo(user_id) and not is_paid(user_id) and (size >= (DAILY_MIRROR_LIMIT - getdailytasks(user_id, check_mirror=True)) or DAILY_MIRROR_LIMIT <= getdailytasks(user_id, check_mirror=True)):
        mssg = f'Daily Mirror Limit is {get_readable_file_size(DAILY_MIRROR_LIMIT)}\nYou have exhausted all your Daily Mirror Limit or File Size of your Mirror is greater than your free Limits.\nTRY AGAIN TOMORROW'
        if config_dict['PAID_SERVICE'] is True:
            mssg += f'\n#Buy Paid Service'
        return sendMessage(mssg, listener.bot, listener.message)
    elif not listener.isLeech: msize = getdailytasks(user_id, upmirror=size, check_mirror=True); LOGGER.info(f"User : {user_id} Daily Mirror Size : {get_readable_file_size(msize)}")
    if DAILY_LEECH_LIMIT and listener.isLeech and user_id != OWNER_ID and not is_sudo(user_id) and not is_paid(user_id) and (size >= (DAILY_LEECH_LIMIT - getdailytasks(user_id, check_leech=True)) or DAILY_LEECH_LIMIT <= getdailytasks(user_id, check_leech=True)):
        mssg = f'Daily Leech Limit is {get_readable_file_size(DAILY_LEECH_LIMIT)}\nYou have exhausted all your Daily Leech Limit or File Size of your Leech is greater than your free Limits.\nTRY AGAIN TOMORROW'
        if config_dict['PAID_SERVICE'] is True:
            mssg += f'\n#Buy Paid Service'
        return sendMessage(mssg, listener.bot, listener.message)
    elif listener.isLeech: lsize = getdailytasks(user_id, upleech=size, check_leech=True); LOGGER.info(f"User : {user_id} Daily Leech Size : {get_readable_file_size(lsize)}")

    gid = ''.join(SystemRandom().choices(ascii_letters + digits, k=12))
    all_limit = config_dict['QUEUE_ALL']
    dl_limit = config_dict['QUEUE_DOWNLOAD']
    if all_limit or dl_limit:
        added_to_queue = False
        with queue_dict_lock:
            dl = len(non_queued_dl)
            up = len(non_queued_up)
            if (all_limit and dl + up >= all_limit and (not dl_limit or dl >= dl_limit)) or (dl_limit and dl >= dl_limit):
                added_to_queue = True
                queued_dl[listener.uid] = ['gd', link, path, listener, newname, is_gdtot, is_udrive, is_sharer, is_sharedrive, is_filepress]
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
    drive.download(link)
    if config_dict['SAME_ACC_COOKIES']:
        if (is_gdtot or is_udrive or is_sharer or is_sharedrive):
            drive.deletefile(link)

 
