from random import SystemRandom
from string import ascii_letters, digits
from os import makedirs
from threading import Event
from mega import (MegaApi, MegaListener, MegaRequest, MegaTransfer, MegaError)

from bot import LOGGER, download_dict, download_dict_lock, config_dict, \
                user_data, OWNER_ID, non_queued_dl, non_queued_up, queued_dl, queue_dict_lock
from bot.helper.telegram_helper.message_utils import sendMessage, sendStatusMessage, sendStatusMessage, sendFile
from bot.helper.ext_utils.bot_utils import get_readable_file_size, get_mega_link_type, is_sudo, is_paid, getdailytasks, userlistype
from bot.helper.mirror_utils.upload_utils.gdriveTools import GoogleDriveHelper
from bot.helper.mirror_utils.status_utils.queue_status import QueueStatus
from bot.helper.ext_utils.fs_utils import get_base_name, check_storage_threshold
from bot.helper.mirror_utils.status_utils.mega_download_status import MegaDownloadStatus


class MegaAppListener(MegaListener):
    _NO_EVENT_ON = (MegaRequest.TYPE_LOGIN,MegaRequest.TYPE_FETCH_NODES)
    NO_ERROR = "no error"

    def __init__(self, continue_event: Event, listener):
        self.continue_event = continue_event
        self.node = None
        self.public_node = None
        self.listener = listener
        self.__bytes_transferred = 0
        self.is_cancelled = False
        self.__speed = 0
        self.__name = ''
        self.__size = 0
        self.error = None
        self.gid = ""
        super(MegaAppListener, self).__init__()

    @property
    def speed(self):
        """Returns speed of the download in bytes/second"""
        return self.__speed

    @property
    def name(self):
        """Returns name of the download"""
        return self.__name

    def setValues(self, name, size, gid):
        self.__name = name
        self.__size = size
        self.gid = gid

    @property
    def size(self):
        """Size of download in bytes"""
        return self.__size

    @property
    def downloaded_bytes(self):
        return self.__bytes_transferred

    def onRequestFinish(self, api, request, error):
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

    def onRequestTemporaryError(self, api, request, error: MegaError):
        LOGGER.error(f'Mega Request error in {error}')
        if not self.is_cancelled:
            self.is_cancelled = True
            self.listener.onDownloadError(f"RequestTempError: {error.toString()}")
        self.error = error.toString()
        self.continue_event.set()

    def onTransferUpdate(self, api: MegaApi, transfer: MegaTransfer):
        if self.is_cancelled:
            api.cancelTransfer(transfer, None)
            self.continue_event.set()
            return
        self.__speed = transfer.getSpeed()
        self.__bytes_transferred = transfer.getTransferredBytes()

    def onTransferFinish(self, api: MegaApi, transfer: MegaTransfer, error):
        try:
            if self.is_cancelled:
                self.continue_event.set()
            elif transfer.isFinished() and (transfer.isFolderTransfer() or transfer.getFileName() == self.name):
                self.listener.onDownloadComplete()
                self.continue_event.set()
        except Exception as e:
            LOGGER.error(e)

    def onTransferTemporaryError(self, api, transfer, error):
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

    def __init__(self):
        self.continue_event = Event()

    def do(self, function, args):
        self.continue_event.clear()
        function(*args)
        self.continue_event.wait()


def add_mega_download(mega_link, path, listener, name, from_queue=False):
    MEGA_API_KEY = config_dict['MEGA_API_KEY']
    MEGA_EMAIL_ID = config_dict['MEGA_EMAIL_ID']
    MEGA_PASSWORD = config_dict['MEGA_PASSWORD']
    executor = AsyncExecutor()
    api = MegaApi(MEGA_API_KEY, None, None, 'mirror-leech-telegram-bot')
    folder_api = None
    mega_listener = MegaAppListener(executor.continue_event, listener)
    api.addListener(mega_listener)
    user_id = listener.message.from_user.id
    user_dict = user_data.get(user_id, False)
    if MEGA_EMAIL_ID and MEGA_PASSWORD:
        executor.do(api.login, (MEGA_EMAIL_ID, MEGA_PASSWORD))
    if get_mega_link_type(mega_link) == "file":
        executor.do(api.getPublicNode, (mega_link,))
        node = mega_listener.public_node
    else:
        folder_api = MegaApi(MEGA_API_KEY, None, None, 'mltb')
        folder_api.addListener(mega_listener)
        executor.do(folder_api.loginToFolder, (mega_link,))
        node = folder_api.authorizeNode(mega_listener.node)
    if mega_listener.error is not None:
        sendMessage(str(mega_listener.error), listener.bot, listener.message)
        api.removeListener(mega_listener)
        if folder_api is not None:
            folder_api.removeListener(mega_listener)
        return
    mname = name or node.getName()

    IS_USRTD = user_dict.get('is_usertd') if user_dict and user_dict.get('is_usertd') else False
    if config_dict['STOP_DUPLICATE'] and not listener.isLeech and IS_USRTD == False:
        LOGGER.info('Checking File/Folder if already in Drive')
        if listener.isZip:
            mname = f"{mname}.zip"
        elif listener.extract:
            try:
                mname = get_base_name(mname)
            except:
                mname = None
        if mname is not None:
            smsg, button = GoogleDriveHelper(user_id=user_id).drive_list(mname, True)
            if smsg:
                tegr, html, tgdi = userlistype(user_id)
                if tegr:
                    sendMessage("File/Folder is already available in Drive.\nHere are the search results:", listener.bot, listener.message, button)
                elif html:
                    sendFile(listener.bot, listener.message, button, f"File/Folder is already available in Drive. Here are the search results:\n\n{smsg}")
                else: sendMessage(smsg, listener.bot, listener.message, button)
                api.removeListener(mega_listener)
                if folder_api is not None:
                    folder_api.removeListener(mega_listener)
                return

    user_id = listener.message.from_user.id
    MEGA_LIMIT = config_dict['MEGA_LIMIT']
    STORAGE_THRESHOLD = config_dict['STORAGE_THRESHOLD']
    ZIP_UNZIP_LIMIT = config_dict['ZIP_UNZIP_LIMIT']
    LEECH_LIMIT = config_dict['LEECH_LIMIT']
    DAILY_MIRROR_LIMIT = config_dict['DAILY_MIRROR_LIMIT'] * 1024**3 if config_dict['DAILY_MIRROR_LIMIT'] else config_dict['DAILY_MIRROR_LIMIT']
    DAILY_LEECH_LIMIT = config_dict['DAILY_LEECH_LIMIT'] * 1024**3 if config_dict['DAILY_LEECH_LIMIT'] else config_dict['DAILY_LEECH_LIMIT']

    size = api.getSize(node)
    if any([STORAGE_THRESHOLD, ZIP_UNZIP_LIMIT, MEGA_LIMIT, LEECH_LIMIT]) and user_id != OWNER_ID and not is_sudo(user_id) and not is_paid(user_id):
        arch = any([listener.isZip, listener.isLeech, listener.extract])
        if STORAGE_THRESHOLD is not None:
            acpt = check_storage_threshold(size, arch)
            if not acpt:
                msg = f'You must leave {STORAGE_THRESHOLD}GB free storage.'
                msg += f'\nYour File/Folder size is {get_readable_file_size(size)}'
                if config_dict['PAID_SERVICE'] is True:
                    msg += f'\n#Buy Paid Service'
                return sendMessage(msg, listener.bot, listener.message)
        limit = None
        if ZIP_UNZIP_LIMIT and arch:
            msg3 = f'Failed, Zip/Unzip limit is {ZIP_UNZIP_LIMIT}GB.\nYour File/Folder size is {get_readable_file_size(api.getSize(node))}.'
            limit = ZIP_UNZIP_LIMIT
        if LEECH_LIMIT and arch:
            msg3 = f'Failed, Leech limit is {LEECH_LIMIT}GB.\nYour File/Folder size is {get_readable_file_size(api.getSize(node))}.'
            limit = LEECH_LIMIT
        if MEGA_LIMIT is not None:
            msg3 = f'Failed, Mega limit is {MEGA_LIMIT}GB.\nYour File/Folder size is {get_readable_file_size(api.getSize(node))}.'
            limit = MEGA_LIMIT
        if config_dict['PAID_SERVICE'] is True:
            msg3 += f'\n#Buy Paid Service'
        if limit is not None:
            LOGGER.info('Checking File/Folder Size...')
            if size > limit * 1024**3:
                return sendMessage(msg3, listener.bot, listener.message)
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


    gid = ''.join(SystemRandom().choices(ascii_letters + digits, k=8))
    mname = name or node.getName()
    size = api.getSize(node)
    all_limit = config_dict['QUEUE_ALL']
    dl_limit = config_dict['QUEUE_DOWNLOAD']
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
    makedirs(path)
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

