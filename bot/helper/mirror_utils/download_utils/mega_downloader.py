from random import SystemRandom
from string import ascii_letters, digits
from os import makedirs
from threading import Event
from mega import (MegaApi, MegaListener, MegaRequest, MegaTransfer, MegaError)


from bot import LOGGER, MEGA_API_KEY, TELEGRAPH_STYLE, download_dict, download_dict_lock, MEGA_LIMIT, STOP_DUPLICATE, ZIP_UNZIP_LIMIT, STORAGE_THRESHOLD, LEECH_LIMIT, MEGA_EMAIL_ID, MEGA_PASSWORD, \
                OWNER_ID, SUDO_USERS, PAID_USERS, PAID_SERVICE
from bot.helper.telegram_helper.message_utils import sendMessage, sendMarkup, sendStatusMessage, sendStatusMessage, sendFile
from bot.helper.ext_utils.bot_utils import get_readable_file_size, setInterval, get_mega_link_type
from bot.helper.mirror_utils.upload_utils.gdriveTools import GoogleDriveHelper
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


def add_mega_download(mega_link: str, path: str, listener, name: str):
    executor = AsyncExecutor()
    api = MegaApi(MEGA_API_KEY, None, None, 'mirror-leech-telegram-bot')
    folder_api = None
    mega_listener = MegaAppListener(executor.continue_event, listener)
    api.addListener(mega_listener)
    if MEGA_EMAIL_ID is not None and MEGA_PASSWORD is not None:
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
    if STOP_DUPLICATE and not listener.isLeech:
        LOGGER.info('Checking File/Folder if already in Drive')
        if listener.isZip:
            mname = f"{mname}.zip"
        elif listener.extract:
            try:
                mname = get_base_name(mname)
            except:
                mname = None
        if mname is not None:

            if TELEGRAPH_STYLE is True:
                smsg, button = GoogleDriveHelper().drive_list(mname, True)
                if smsg:
                    msg1 = "File/Folder is already available in Drive.\nHere are the search results:"
                    return sendMarkup(msg1, listener.bot, listener.message, button)
            else:
                cap, f_name = GoogleDriveHelper().drive_list(mname, True)
                if cap:
                    cap = f"File/Folder is already available in Drive. Here are the search results:\n\n{cap}"
                    sendFile(listener.bot, listener.message, f_name, cap)
                api.removeListener(mega_listener)
                if folder_api is not None:
                    folder_api.removeListener(mega_listener)
                return
    user_id = listener.message.from_user.id
    if any([STORAGE_THRESHOLD, ZIP_UNZIP_LIMIT, MEGA_LIMIT, LEECH_LIMIT]) and user_id != OWNER_ID and user_id not in SUDO_USERS and user_id not in PAID_USERS:
        size = api.getSize(node)
        arch = any([listener.isZip, listener.isLeech, listener.extract])
        if PAID_SERVICE is True:
            if STORAGE_THRESHOLD is not None:
                acpt = check_storage_threshold(size, arch)
                if not acpt:
                    msg = f'You must leave {STORAGE_THRESHOLD}GB free storage.'
                    msg += f'\nYour File/Folder size is {get_readable_file_size(size)}'
                    msg += f'\n#Buy Paid Service'
                    return sendMessage(msg, listener.bot, listener.message)
            limit = None
            if ZIP_UNZIP_LIMIT is not None and arch:
                msg3 = f'Failed, Zip/Unzip limit is {ZIP_UNZIP_LIMIT}GB.\nYour File/Folder size is {get_readable_file_size(api.getSize(node))}.'
                msg3 += f'\n#Buy Paid Service'
                limit = ZIP_UNZIP_LIMIT
            if LEECH_LIMIT is not None and arch:
                msg3 = f'Failed, Leech limit is {LEECH_LIMIT}GB.\nYour File/Folder size is {get_readable_file_size(api.getSize(node))}.'
                msg3 += f'\n#Buy Paid Service'
                limit = LEECH_LIMIT
            if MEGA_LIMIT is not None:
                msg3 = f'Failed, Mega limit is {MEGA_LIMIT}GB.\nYour File/Folder size is {get_readable_file_size(api.getSize(node))}.'
                msg3 += f'\n#Buy Paid Service'
                limit = MEGA_LIMIT
        else:
            if STORAGE_THRESHOLD is not None:
                acpt = check_storage_threshold(size, arch)
                if not acpt:
                    msg = f'You must leave {STORAGE_THRESHOLD}GB free storage.'
                    msg += f'\nYour File/Folder size is {get_readable_file_size(size)}'
                    return sendMessage(msg, listener.bot, listener.message)
            limit = None
            if ZIP_UNZIP_LIMIT is not None and arch:
                msg3 = f'Failed, Zip/Unzip limit is {ZIP_UNZIP_LIMIT}GB.\nYour File/Folder size is {get_readable_file_size(api.getSize(node))}.'
                limit = ZIP_UNZIP_LIMIT
            if LEECH_LIMIT is not None and arch:
                msg3 = f'Failed, Leech limit is {LEECH_LIMIT}GB.\nYour File/Folder size is {get_readable_file_size(api.getSize(node))}.'
                limit = LEECH_LIMIT
            if MEGA_LIMIT is not None:
                msg3 = f'Failed, Mega limit is {MEGA_LIMIT}GB.\nYour File/Folder size is {get_readable_file_size(api.getSize(node))}.'
                limit = MEGA_LIMIT
        if limit is not None:
            LOGGER.info('Checking File/Folder Size...')
            if size > limit * 1024**3:
                return sendMessage(msg3, listener.bot, listener.message)
    
    with download_dict_lock:
        download_dict[listener.uid] = MegaDownloadStatus(mega_listener, listener)
    listener.onDownloadStart()
    makedirs(path)
    gid = ''.join(SystemRandom().choices(ascii_letters + digits, k=8))
    mname = name or node.getName()
    mega_listener.setValues(mname, api.getSize(node), gid)
    sendStatusMessage(listener.message, listener.bot)
    executor.do(api.startDownload, (node, path, name, None, False, None))
    api.removeListener(mega_listener)
    if folder_api is not None:
        folder_api.removeListener(mega_listener)





    # def add_download(self, link, path):
    #     Path(path).mkdir(parents=True, exist_ok=True)
    #     try:
    #         dl = self.__mega_client.addDl(link, path)
    #     except Exception as err:
    #         LOGGER.error(err)
    #         return sendMessage(str(err), self.__listener.bot, self.__listener.message)
    #     gid = dl['gid']
    #     info = self.__mega_client.getDownloadInfo(gid)
    #     file_name = info['name']
    #     file_size = info['total_length']
    #     if STOP_DUPLICATE and not self.__listener.isLeech:
    #         LOGGER.info('Checking File/Folder if already in Drive')
    #         mname = file_name
    #         if self.__listener.isZip:
    #             mname = f"{mname}.zip"
    #         elif self.__listener.extract:
    #             try:
    #                 mname = get_base_name(mname)
    #             except:
    #                 mname = None
    #         if mname is not None:
    #             if TELEGRAPH_STYLE is True:
    #                 smsg, button = GoogleDriveHelper().drive_list(mname, True)
    #                 if smsg:
    #                     msg1 = "File/Folder is already available in Drive.\nHere are the search results:"
    #                     return sendMarkup(msg1, self.__listener.bot, self.__listener.message, button)
    #             else:
    #                 cap, f_name = GoogleDriveHelper().drive_list(mname, True)
    #                 if cap:
    #                     cap = f"File/Folder is already available in Drive. Here are the search results:\n\n{cap}"
    #                     sendFile(self.__listener.bot, self.__listener.message, f_name, cap)
    #                     return
    #     if any([STORAGE_THRESHOLD, ZIP_UNZIP_LIMIT, MEGA_LIMIT, LEECH_LIMIT]):
    #         arch = any([self.__listener.isZip, self.__listener.extract])
    #         if STORAGE_THRESHOLD is not None:
    #             acpt = check_storage_threshold(file_size, arch)
    #             if not acpt:
    #                 msg = f'You must leave {STORAGE_THRESHOLD}GB free storage.'
    #                 msg += f'\nYour File/Folder size is {get_readable_file_size(file_size)}'
    #                 return sendMessage(msg, self.__listener.bot, self.__listener.message)
    #         limit = None
    #         if ZIP_UNZIP_LIMIT is not None and arch:
    #             msg3 = f'Failed, Zip/Unzip limit is {ZIP_UNZIP_LIMIT}GB.\nYour File/Folder size is {get_readable_file_size(file_size)}.'
    #             limit = ZIP_UNZIP_LIMIT
    #         if LEECH_LIMIT is not None and self.__listener.isLeech:
    #             msg3 = f'Failed, Leech limit is {LEECH_LIMIT}GB.\nYour File/Folder size is {get_readable_file_size(file_size)}.'
    #             limit = LEECH_LIMIT
    #         elif MEGA_LIMIT is not None:
    #             msg3 = f'Failed, Mega limit is {MEGA_LIMIT}GB.\nYour File/Folder size is {get_readable_file_size(file_size)}.'
    #             limit = MEGA_LIMIT
    #         if limit is not None:
    #             LOGGER.info('Checking File/Folder Size...')
    #             if file_size > limit * 1024**3:
    #                 return sendMessage(msg3, self.__listener.bot, self.__listener.message)
    #     self.__onDownloadStart(file_name, file_size, gid)
    #     LOGGER.info(f'Mega download started with gid: {gid}')

    # def cancel_download(self):
    #     LOGGER.info(f'Cancelling download on user request: {self.gid}')
    #     self.__mega_client.cancelDl(self.gid)
