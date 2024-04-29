from hashlib import sha1
from base64 import b64encode
from bencoding import bencode, bdecode
from time import sleep, time
from re import search as re_search
from os import remove
from time import sleep, time
from re import search as re_search
from threading import Lock, Thread

import logging
from typing import Any, Dict, List, Optional, Set, Union

from bot import download_dict, download_dict_lock, get_client, config_dict, QbInterval, user_data, LOGGER, OWNER_ID
from bot.helper.mirror_utils.status_utils.qbit_download_status import QbDownloadStatus
from bot.helper.mirror_utils.upload_utils.gdriveTools import GoogleDriveHelper
from bot.helper.telegram_helper.message_utils import sendMessage, deleteMessage, sendStatusMessage, update_all_messages, sendFile
from bot.helper.ext_utils.bot_utils import get_readable_file_size, get_readable_time, setInterval, bt_selection_buttons, getDownloadByGid, new_thread, is_sudo, is_paid, getdailytasks, userlistype
from bot.helper.ext_utils.fs_utils import clean_unwanted, get_base_name, check_storage_threshold

qb_download_lock = Lock()
STALLED_TIME: Dict[str, float] = {}
STOP_DUP_CHECK: Set[str] = set()
LIMITS_CHECK: Set[str] = set()
RECHECKED: Set[str] = set()
UPLOADED: Set[str] = set()
SEEDING: Set[str] = set()

def __get_hash_magnet(mgt: str) -> Optional[str]:
    match = re_search(r'(?<=xt=urn:btih:)[a-zA-Z0-9]+', mgt)
    if match is not None:
        hash_ = match.group(0)
        if len(hash_) == 32:
            hash_ = b64encode(b32decode(hash_.upper())).decode()
        return str(hash_)
    return None

def __get_hash_file(path: str) -> Optional[str]:
    try:
        with open(path, "rb") as f:
            decodedDict = bdecode(f.read())
            hash_ = sha1(bencode(decodedDict[b'info'])).hexdigest()
    except Exception as e:
        logging.error(f"Error getting hash from file: {e}")
        return None
    return str(hash_)

def add_qb_torrent(link: str, path: str, listener: Any, ratio: float, seed_time: int) -> None:
    client = get_client()
    ADD_TIME = time()
    try:
        if link.startswith('magnet:'):
            ext_hash = __get_hash_magnet(link)
        else:
            ext_hash = __get_hash_file(link)
        if ext_hash is None or len(ext_hash) < 30:
            sendMessage("Not a torrent! Qbittorrent only for torrents!", listener.bot, listener.message)
            return
        tor_info = client.torrents_info(torrent_hashes=ext_hash)
        if len(tor_info) > 0:
            sendMessage("This Torrent already added!", listener.bot, listener.message)
            return
        if link.startswith('magnet:'):
            op = client.torrents_add(link, save_path=path, ratio_limit=ratio, seeding_time_limit=seed_time)
        else:
            op = client.torrents_add(torrent_files=[link], save_path=path, ratio_limit=ratio, seeding_time_limit=seed_time)
        sleep(0.3)
        if op.lower() == "ok.":
            tor_info = client.torrents_info(torrent_hashes=ext_hash)
            if len(tor_info) == 0:
                while True:
                    tor_info = client.torrents_info(torrent_hashes=ext_hash)
                    if len(tor_info) > 0:
                        break
                    elif time() - ADD_TIME >= 60:
                        msg = "Not added, maybe it will took time and u should remove it manually using eval!"
                        sendMessage(msg, listener.bot, listener.message)
                        __remove_torrent(client, ext_hash)
                        return
        else:
            sendMessage("This is an unsupported/invalid link.", listener.bot, listener.message)
            __remove_torrent(client, ext_hash)
            return
        tor_info = tor_info[0]
        ext_hash = tor_info.hash
        with download_dict_lock:
            download_dict[listener.uid] = QbDownloadStatus(listener, ext_hash)
            logging.info(download_dict)
        with qb_download_lock:
            STALLED_TIME[ext_hash] = time()
            if not QbInterval:
                periodic = setInterval(5, __qb_listener)
                QbInterval.append(periodic)
        listener.onDownloadStart()
        logging.info(f"QbitDownload started: {tor_info.name} - Hash: {ext_hash}")
        if config_dict['BASE_URL'] and listener.select:
            if link.startswith('magnet:'):
                metamsg = "Downloading Metadata, wait then you can select files. Use torrent file to avoid this wait."
                meta = sendMessage(metamsg, listener.bot, listener.message)
                while True:
                    tor_info = client.torrents_info(torrent_hashes=ext_hash)
                    if len(tor_info) == 0:
                        deleteMessage(listener.bot, meta)
                        return
                    try:
                        tor_info = tor_info[0]
                        if tor_info.state not in ["metaDL", "checkingResumeData", "pausedDL"]:
                            deleteMessage(listener.bot, meta)
                            break
                    except:
                        return deleteMessage(listener.bot, meta)
            client.torrents_pause(torrent_hashes=ext_hash)
            SBUTTONS = bt_selection_buttons(ext_hash)
            msg = "Your download paused. Choose files then press Done Selecting button to start downloading."
            sendMessage(msg, listener.bot, listener.message, SBUTTONS)
        else:
            sendStatusMessage(listener.message, listener.bot)
    except Exception as e:
        sendMessage(str(e), listener.bot, listener.message)
    finally:
        if not link.startswith('magnet:'):
            remove(link)
        client.auth_log_out()

