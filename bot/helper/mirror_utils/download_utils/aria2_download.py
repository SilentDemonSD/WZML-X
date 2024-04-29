import asyncio
import re
import time
from typing import Any, Dict, List, Optional

import aioaria2api as aria2
from aiohttp import ClientSession
from bot import aria2 as bot_aria2, download_dict_lock, download_dict, LOGGER, config_dict, user_data, aria2_options, aria2c_global, OWNER_ID
from bot.helper.mirror_utils.upload_utils.gdriveTools import GoogleDriveHelper
from bot.helper.ext_utils.bot_utils import is_magnet, getDownloadByGid, new_thread, bt_selection_buttons, get_readable_file_size, is_sudo, is_paid, getdailytasks, userlistype
from bot.helper.mirror_utils.status_utils.aria_download_status import AriaDownloadStatus
from bot.helper.telegram_helper.message_utils import sendStatusMessage, sendMessage, deleteMessage, update_all_messages, sendFile
from bot.helper.ext_utils.fs_utils import get_base_name, check_storage_threshold, clean_unwanted
from bot.modules.scraper import indexScrape

async def __onDownloadStarted(api: aria2.Aria2Api, gid: str) -> None:
    download = api.get_download(gid)
    if download.is_metadata:
        LOGGER.info(f'onDownloadStarted: {gid} METADATA')
        await asyncio.sleep(1)
        if dl := getDownloadByGid(gid):
            listener = dl.listener()
            if listener.select:
                meta_msg = "Downloading Metadata, wait then you can select files. Use torrent file to avoid this wait."
                meta = await sendMessage(meta_msg, listener.bot, listener.message)
                while True:
                    if download.is_removed or download.followed_by_ids:
                        await deleteMessage(listener.bot, meta)
                        break
                    download = download.live
    else:
        LOGGER.info(f'onDownloadStarted: {download.name} - Gid: {gid}')
    try:
        STOP_DUPLICATE = config_dict['STOP_DUPLICATE']
        TORRENT_DIRECT_LIMIT = config_dict['TORRENT_DIRECT_LIMIT']
        ZIP_UNZIP_LIMIT = config_dict['ZIP_UNZIP_LIMIT']
        LEECH_LIMIT = config_dict['LEECH_LIMIT']
        STORAGE_THRESHOLD = config_dict['STORAGE_THRESHOLD']
        DAILY_MIRROR_LIMIT = config_dict['DAILY_MIRROR_LIMIT'] * 1024**3 if config_dict['DAILY_MIRROR_LIMIT'] else config_dict['DAILY_MIRROR_LIMIT']
        DAILY_LEECH_LIMIT = config_dict['DAILY_LEECH_LIMIT'] * 1024**3 if config_dict['DAILY_LEECH_LIMIT'] else config_dict['DAILY_LEECH_LIMIT']
        if any([STOP_DUPLICATE, TORRENT_DIRECT_LIMIT, ZIP_UNZIP_LIMIT, LEECH_LIMIT, STORAGE_THRESHOLD, DAILY_MIRROR_LIMIT, DAILY_LEECH_LIMIT]):
            await asyncio.sleep(1)
            if dl := getDownloadByGid(gid):
                listener = dl.listener()
                if listener.select:
                    return
                download = api.get_download(gid)
                if not download.is_torrent:
                    await asyncio.sleep(3)
                    download = download.live
            user_id = listener.message.from_user.id
            user_dict = user_data.get(user_id, False)
            IS_USRTD = user_dict and user_dict.get('is_usertd') if user_dict else False
            if STOP_DUPLICATE and not dl.listener().isLeech and IS_USRTD == False:
                LOGGER.info('Checking File/Folder if already in Drive...')
                sname = download.name
                if listener.isZip:
                    sname = f"{sname}.zip"
                elif listener.extract:
                    try:
                        sname = get_base_name(sname)
                    except:
                        sname = None
              
