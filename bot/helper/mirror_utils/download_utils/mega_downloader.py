import os
import asyncio
import threading
import logging
import shutil
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

import mega
from mega import MegaApi, MegaError, MegaRequest, MegaTransfer
from telegram import Message, Bot, Update
from telegram.error import TelegramError
from telegram.ext import CallbackContext
from telegram.ext.handler import CommandHandler
from telegram.ext.dispatcher import Dispatcher
from telegram.utils.helpers import mention_html

from bot import LOGGER, download_dict, download_dict_lock, config_dict, user_data, OWNER_ID, non_queued_dl, non_queued_up, queued_dl, queue_dict_lock
from bot.helper.telegram_helper.message_utils import sendMessage, sendStatusMessage, sendFile
from bot.helper.ext_utils.bot_utils import get_readable_file_size, get_mega_link_type, is_sudo, is_paid, getdailytasks, userlistype
from bot.helper.mirror_utils.upload_utils.gdriveTools import GoogleDriveHelper
from bot.helper.mirror_utils.status_utils.queue_status import QueueStatus
from bot.helper.ext_utils.fs_utils import get_base_name, check_storage_threshold
from bot.helper.mirror_utils.status_utils.mega_download_status import MegaDownloadStatus

# Logging
logging.basicConfig(
    format=u"%(filename)s:%(lineno)d #%(levelname)-8s [%(asctime)s] %(message)s",
    level=logging.INFO,
)

class MegaAppListener(MegaListener):
    """MegaListener for handling Mega API events."""

    _NO_EVENT_ON = (MegaRequest.TYPE_LOGIN, MegaRequest.TYPE_FETCH_NODES)
    NO_ERROR = "no error"

    def __init__(
        self,
        continue_event: threading.Event,
        listener: CallbackContext,
    ):
        self.continue_event = continue_event
        self.node = None
        self.public_node = None
        self.listener = listener
        self.__bytes_transferred = 0
        self.is_cancelled = False
        self.__speed = 0
        self.__name = ""
        self.__size = 0
        self.error = None
        self.gid = ""
        super().__init__()

    @property
    def speed(self) -> int:
        """Returns speed of the download in bytes/second."""
        return self.__speed

    @property
    def name(self) -> str:
        """Returns name of the download."""
        return self.__name

    def setValues(self, name: str, size: int, gid: str):
        self.__name = name
        self.__size = size
        self.gid = gid

    @property
    def size(self) -> int:
        """Size of download in bytes."""
        return self.__size

    @property
    def downloaded_bytes(self) -> int:
        return self.__bytes_transferred

    def onRequestFinish(
        self, api: MegaApi, request: MegaRequest, error: Union[MegaError, str]
    ):
        if str(error).lower() != "no error":
            self.error = error.copy()
            LOGGER.error(self.error)
            self.continue_event.set()
            return
        request_type = request.getType()
        if request_type == MegaRequest.TYPE_LOGIN:
            api.fetchNodes()
        elif request_type == MegaRequest.TYPE_GET_PUBLIC_NODE:
            self.public_node = request.getPublicMegaNode()
        elif request_type == MegaRequest.TYPE_FETCH_NODES:
            LOGGER.info("Fetching Root Node.")
            self.node = api.getRootNode()
            LOGGER.info(f"Node Name: {self.node.getName()}")
        if request_type not in self._NO_EVENT_ON or self.node and "cloud drive" not in self.node.getName().lower():
            self.continue_event.set()

    def onRequestTemporaryError(
        self, api: MegaApi, request: MegaRequest, error: MegaError
    ):
        LOGGER.error(f'Mega Request error in {error}')
        if not self.is_cancelled:
            self.is_cancelled = True
            self.listener.onDownloadError(f"RequestTempError: {error.toString()}")
        self.error = error.toString()
        self.continue_event.set()

    def onTransferUpdate(
        self, api: MegaApi, transfer: MegaTransfer
    ) -> None:
        if self.is_cancelled:
            api.cancelTransfer(transfer, None)
            self.continue_event.set()
            return
        self.__speed = transfer.getSpeed()
        self.__bytes_transferred = transfer.getTransferredBytes()

    def onTransferFinish(
        self, api: MegaApi, transfer: MegaTransfer, error: Union[MegaError, str]
    ) -> None:
        try:
            if self.is_cancelled:
                self.continue_event.set()
            elif transfer.isFinished() and (transfer.isFolderTransfer() or transfer.getFileName() == self.name):
                self.listener.onDownloadComplete()
                self.continue_event.set()
        except Exception as e:
            LOGGER.error(e)

    def onTransferTemporaryError(
        self, api, transfer, error: MegaError
    ) -> None:
        filen = transfer.getFileName()
        state = transfer.getState()
        errStr = error.toString()
        LOGGER.error(f'Mega download error in file {transfer} {filen}: {error}')
        if state in [1, 4]:
            # Sometimes MEGA (offical client) can't stream a node either and raises a temp failed error.
            # Don't break the transfer queue if transfer's in queued (1) or retrying (4) state [causes seg fault]
            return

        self.error = errStr
        if not self.is_cancelled:
            self.is_cancelled = True
            self.listener.onDownloadError(f"TransferTempError: {errStr} ({filen})")
            self.continue_event.set()

    def cancel_download(self):
        self.is_cancelled = True
        self.listener.onDownloadError("Download Canceled by user")

class AsyncExecutor:
    """AsyncExecutor for handling asynchronous tasks."""

    def __init__(self):
        self.continue_event = threading.Event()

    def do(self, function: Callable, args: Tuple[Any]) -> None:
        self.continue_event.clear()
        asyncio.run(function(*args))
        self.continue_event.wait()

def add_mega_download(
    mega_link: str,
    path: str,
    listener: CallbackContext,
    name: Optional[str] = None,
    from_queue: bool = False,
) -> None:
    """Adds a Mega download to the queue."""

    MEGA_API_KEY = config_dict["MEGA_API_KEY"]
    MEGA_EMAIL_ID = config_dict["MEGA_EMAIL_ID"]
    MEGA_PASSWORD = config_dict["MEGA_PASSWORD"]
    executor = AsyncExecutor()
    api = MegaApi(MEGA_API_KEY, None, None, "mirror-leech-telegram-bot")
    folder_api = None
    mega_listener = MegaAppListener(executor.continue_event, listener)
    api.addListener(mega_listener)

    try:
        user_id = listener.message.from_user.id
        user_dict = user_data[user_id]
    except KeyError:
        user_dict = {"is_usertd": False}
        user_data[user_id] = user_dict

    if MEGA_EMAIL_ID and MEGA_PASSWORD:
        executor.do(api.login, (MEGA_EMAIL_ID, MEGA_PASSWORD))

    try:
        if get_mega_link_type(mega_link) == "file":
            executor.do(api.getPublicNode, (mega_link,))
            node = mega_listener.public_node
        else:
            folder_api = MegaApi(MEGA_API_KEY, None, None, "mltb")
            folder_api.addListener(mega_listener)
            executor.do(folder_api.loginToFolder, (mega_link,))
            node = folder_api.authorizeNode(mega_listener.node)
    except Exception as e:
        LOGGER.error(e)
        return

    if mega_listener.error is not None:
        sendMessage(str(mega_listener.error), listener.bot, listener.message)
        api.removeListener(mega_listener)
        if folder_api is not None:
            folder_api.removeListener(mega_listener)
        return

    mname = name or node.getName()

    is_usertd = user_dict.get("is_usertd")
    if config_dict["STOP_DUPLICATE"] and not listener.is_leech and is_usertd is False:
        LOGGER.info("Checking File/Folder if already in Drive")
        if listener.is_zip:
            mname = f"{mname}.zip"
        elif listener.extract:
            try:
                mname = get_base_name(mname)
            except:
                mname = None
        if mname is not None:
            try:
                smsg, button = GoogleDriveHelper(user_id=user_id).drive_list(mname, True)
            except Exception as e:
                LOGGER.error(e)
                return
            if smsg:
                tegr, html, tgdi = userlistype(user_id)
                if tegr:
                    sendMessage(
                        f"File/Folder is already available in Drive.\nHere are the search results:\n{smsg}",
                        listener.bot,
                        listener.message,
                        button,
                    )
                elif html:
                    sendFile(
                        listener.bot,
                        listener.message,
                        button,
                        f"File/Folder is already available in Drive. Here are the search results:\n\n{smsg}",
                    )
                else:
                    sendMessage(smsg, listener.bot, listener.message, button)
                api.removeListener(mega_listener)
                if folder_api is not None:
                    folder_api.removeListener(mega_listener)
                return

    user_id = listener.message.from_user.id
    mega_limit = config_dict["MEGA_LIMIT"]
    storage_threshold = config_dict["STORAGE_THRESHOLD"]
    zip_unzip_limit = config_dict["ZIP_UNZIP_LIMIT"]
    leech_limit = config_dict["LEECH_LIMIT"]
    daily_mirror_limit = (
        config_dict["DAILY_MIRROR_LIMIT"] * 1024**3
        if config_dict["DAILY_MIRROR_LIMIT"]
        else config_dict["DAILY_MIRROR_LIMIT"]
    )
    daily_leech_limit = (
        config_dict["DAILY_LEECH_LIMIT"] * 1024**3
        if config_dict["DAILY_LEECH_LIMIT"]
        else config_dict["DAILY_LEECH_LIMIT"]
    )

    size = api.getSize(node)

    if any(
        [
            storage_threshold,
            zip_unzip_limit,
            mega_limit,
            leech_limit,
        ]
    ) and user_id != OWNER_ID and not is_sudo(user_id) and not is_paid(user_id):
        arch = any([listener.is_zip, listener.is_leech, listener.extract])
        if storage_threshold is not None:
            acpt = check_storage_threshold(size, arch)
            if not acpt:
                msg = f'You must leave {storage_threshold}GB free storage.'
                msg += f'\nYour File/Folder size is {get_readable_file_size(size)}'
                if config_dict["PAID_SERVICE"] is True:
                    msg += f'\n#Buy Paid Service'
                return sendMessage(msg, listener.bot, listener.message)
        limit = None
        if zip_unzip_limit and arch:
            msg3 = f'Failed, Zip/Unzip limit is {zip_unzip_limit}GB.\nYour File/Folder size is {get_readable_file_size(size)}.'
            limit = zip_unzip_limit
        if leech_limit and arch:
            msg3 = f'Failed, Leech limit is {leech_limit}GB.\nYour File/Folder size is {get_readable_file_size(size)}.'
            limit = leech_limit
        if mega_limit is not None:
            msg3 = f'Failed, Mega limit is {mega_limit}GB.\nYour File/Folder size is {get_readable_file_size(size)}.'
            limit = mega_limit
        if config_dict["PAID_SERVICE"] is True:
            msg3 += f'\n#Buy Paid Service'
        if limit is not None:
            LOGGER.info("Checking File/Folder Size...")
            if size > limit * 1024**3:
                return sendMessage(msg3, listener.bot, listener.message)

    if daily_mirror_limit and not listener.is_leech and user_id != OWNER_ID and not is_sudo(user_id) and not is_paid(user_id) and (size >= (daily_mirror_limit - getdailytasks(user_id, check_mirror=True)) or daily_mirror_limit <= getdailytasks(user_id, check_mirror=True)):
        mssg = f'Daily Mirror Limit is {get_readable_file_size(daily_mirror_limit)}\nYou have exhausted all your Daily Mirror Limit or File Size of your Mirror is greater than your free Limits.\nTRY AGAIN TOMORROW'
        if config_dict["PAID_SERVICE"] is True:
            mssg += f'\n#Buy Paid Service'
        return sendMessage(mssg, listener.bot, listener.message)
    elif not listener.is_leech:
        msize = getdailytasks(user_id, upmirror=size, check_mirror=True)
        LOGGER.info(f"User : {user_id} Daily Mirror Size : {get_readable_file_size(msize)}")

    if daily_leech_limit and listener.is_leech and user_id != OWNER_ID and not is_sudo(user_id) and not is_paid(user_id) and (size >= (daily_leech_limit - getdailytasks(user_id, check_leech=True)) or daily_leech_limit <= getdailytasks(user_id, check_leech=True)):
        mssg = f'Daily Leech Limit is {get_readable_file_size(daily_leech_limit)}\nYou have exhausted all your Daily Leech Limit or File Size of your Leech is greater than your free Limits.\nTRY AGAIN TOMORROW'
        if config_dict["PAID_SERVICE"] is True:
            mssg += f'\n#Buy Paid Service'
        return sendMessage(mssg, listener.bot, listener.message)
    elif listener.is_leech:
        lsize = getdailytasks(user_id, upleech=size, check_leech=True)
        LOGGER.info(f"User : {user_id} Daily Leech Size : {get_readable_file_size(lsize)}")

    gid = ''.join(SystemRandom().choices(ascii_letters + digits, k=8))
    mname = name or node.getName()
    size = api.getSize(node)
    all_limit = config_dict["QUEUE_ALL"]
    dl_limit = config_dict["QUEUE_DOWNLOAD"]
    if all_limit or dl_limit:
        added_to_queue = False
        with queue_dict_lock:
            dl = len(non_queued_dl)
            up = len(non_queued_up)
            if (all_limit and dl + up >= all_limit and (not dl_limit or dl >= dl_limit)) or (dl_limit and dl >= dl_limit):
                added_to_queue = True
                queued_dl[listener.uid] = ['mega', mega_link, path, listener, name]
        if added_to_queue:
            LOGGER.info(f"Added to Queue/Download: {mname}")
            with download_dict_lock:
                download_dict[listener.uid] = QueueStatus(mname, size, gid, listener, 'Dl')
            listener.onDownloadStart()
            sendStatusMessage(listener.message, listener.bot)
            api.removeListener(mega_listener)
            if folder_api is not None:
                folder_api.removeListener(mega_listener)
            return

    with download_dict_lock:
        download_dict[listener.uid] = MegaDownloadStatus(mega_listener, listener)
    with queue_dict_lock:
        non_queued_dl.add(listener.uid)
    makedirs(path, exist_ok=True)
    mega_listener.setValues(mname, size, gid)
    if not from_queue:
        listener.onDownloadStart()
        sendStatusMessage(listener.message, listener.bot)
        LOGGER.info(f"Download from Mega: {mname}")
    else:
        LOGGER.info(f'Start Queued Download from Mega: {mname}')
    executor.do(api.startDownload, (node, path, name, None, False, None))
    api.removeListener(mega_listener)
    if folder_api is not None:
        folder_api.removeListener(mega_listener)

def register_mega_download_handler(dispatcher: Dispatcher) -> None:
    """Registers the mega download handler."""

    dispatcher.add_handler(
        CommandHandler(
            "megadl",
            add_mega_download,
            pass_args=True,
            pass_user_data=True,
            run_async=True,
        )
    )
