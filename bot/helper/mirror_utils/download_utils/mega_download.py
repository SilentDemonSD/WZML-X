import asyncio
import contextlib
from asyncio import Event
from typing import Any, Callable, Coroutine, Dict, List, Optional, Union

import aiofiles.os
from aiohttp import ClientSession
from mega import MegaApi, MegaError, MegaListener, MegaRequest, MegaTransfer
from telegram import Message, Update

from bot import LOGGER, config_dict, download_dict_lock, download_dict, non_queued_dl, queue_dict_lock
from bot.helper.telegram_helper.message_utils import sendMessage, sendStatusMessage
from bot.helper.ext_utils.bot_utils import get_mega_link_type, run_until_complete, as_completed
from bot.helper.mirror_utils.status_utils.mega_download_status import MegaDownloadStatus
from bot.helper.mirror_utils.status_utils.queue_status import QueueStatus
from bot.helper.ext_utils.task_manager import is_queued, limit_checker, stop_duplicate_check


@contextlib.asynccontextmanager
async def download_dict_context():
    async with download_dict_lock:
        yield download_dict


@contextlib.asynccontextmanager
async def queue_dict_context():
    async with queue_dict_lock:
        yield non_queued_dl


class MegaAppListener(MegaListener):
    _NO_EVENT_ON = (MegaRequest.TYPE_LOGIN, MegaRequest.TYPE_FETCH_NODES)
    NO_ERROR = "no error"

    def __init__(self, continue_event: Event, listener):
        self.continue_event = continue_event
        self.node = None
        self.public_node = None
        self.listener = listener
        self.is_cancelled = False
        self.error = None
        self.__bytes_transferred = 0
        self.__speed = 0
        self.__name = ''
        super().__init__()

    @property
    def speed(self):
        return self.__speed

    @property
    def downloaded_bytes(self):
        return self.__bytes_transferred

    def onRequestFinish(self, api, request, error):
        if str(error).lower() != "no error":
            self.error = error.copy()
            LOGGER.error(f'Mega onRequestFinishError: {self.error}')
            self.continue_event.set()
            return
        request_type = request.getType()
        if request_type == MegaRequest.TYPE_LOGIN:
            api.fetchNodes()
        elif request_type == MegaRequest.TYPE_GET_PUBLIC_NODE:
            self.public_node = request.getPublicMegaNode()
            self.__name = self.public_node.getName()
        elif request_type == MegaRequest.TYPE_FETCH_NODES:
            LOGGER.info("Fetching Root Node.")
            self.node = api.getRootNode()
            self.__name = self.node.getName()
            LOGGER.info(f"Node Name: {self.node.getName()}")
        if request_type not in self._NO_EVENT_ON or self.node and "cloud drive" not in self.__name.lower():
            self.continue_event.set()

    def onRequestTemporaryError(self, api, request, error: MegaError):
        LOGGER.error(f'Mega Request error in {error}')
        if not self.is_cancelled:
            self.is_cancelled = True
            run_until_complete(self.listener.onDownloadError,
                               f"RequestTempError: {error.toString()}")
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
            elif transfer.isFinished() and (transfer.isFolderTransfer() or transfer.getFileName() == self.__name):
                run_until_complete(self.listener.onDownloadComplete)
                self.continue_event.set()
        except Exception as e:
            LOGGER.error(e)

    def onTransferTemporaryError(self, api, transfer, error):
        filen = transfer.getFileName()
        state = transfer.getState()
        errStr = error.toString()
        LOGGER.error(
            f'Mega download error in file {transfer} {filen}: {error}')
        if state in [1, 4]:
            # Sometimes MEGA (offical client) can't stream a node either and raises a temp failed error.
            # Don't break the transfer queue if transfer's in queued (1) or retrying (4) state [causes seg fault]
            return

        self.error = errStr
        if not self.is_cancelled:
            self.is_cancelled = True
            run_until_complete(self.listener.onDownloadError,
                               f"TransferTempError: {errStr} ({filen})")
            self.continue_event.set()

    async def cancel_download(self):
        self.is_cancelled = True
        await self.listener.onDownloadError("Download Canceled by user")


class AsyncExecutor:

    def __init__(self):
        self.continue_event = Event()

    async def do(self, function: Callable, *args):
        self.continue_event.clear()
        await run_until_complete(function, *args)
        await self.continue_event.wait()


async def add_mega_download(mega_link: str, path: str, listener: 'Listener', name: Optional[str] = None) -> Coroutine[Any, Any, None]:
    MEGA_EMAIL = config_dict['MEGA_EMAIL']
    MEGA_PASSWORD = config_dict['MEGA_PASSWORD']

    executor = AsyncExecutor()
    api = MegaApi(None, None, None, 'WZML-X')
    folder_api = None

    mega_listener = MegaAppListener(executor.continue_event, listener)
    api.addListener(mega_listener)

    if MEGA_EMAIL and MEGA_PASSWORD:
        await executor.do(api.login, (MEGA_EMAIL, MEGA_PASSWORD))

    if get_mega_link_type(mega_link) == "file":
        await executor.do(api.getPublicNode, (mega_link,))
        node = mega_listener.public_node
    else:
        folder_api = MegaApi(None, None, None, 'WZML-X')
        folder_api.addListener(mega_listener)
        await executor.do(folder_api.loginToFolder, (mega_link,))
        node = await run_until_complete(folder_api.authorizeNode, mega_listener.node)
    if mega_listener.error:
        await sendMessage(listener.message, str(mega_listener.error))
        await executor.do(api.logout, ())
        if folder_api is not None:
            await executor.do(folder_api.logout, ())
        return

    name = name or node.getName()
    msg, button = await stop_duplicate_check(name, listener)
    if msg:
        await sendMessage(listener.message, msg, button)
        await executor.do(api.logout, ())
        if folder_api is not None:
            await executor.do(folder_api.logout, ())
        return

    gid = token_hex(5)
    size = api.getSize(node)
    limit_exceeded = await limit_checker(size, listener, isMega=True)
    if limit_exceeded:
        await sendMessage(listener.message, limit_exceeded)
        return
    added_to_queue, event = await is_queued(listener.uid)
    if added_to_queue:
        LOGGER.info(f"Added to Queue/Download: {name}")
        async with download_dict_context() as download_dict:
            download_dict[listener.uid] = QueueStatus(
                name, size, gid, listener, 'Dl')
        await listener.onDownloadStart()
        await sendStatusMessage(listener.message)
        await event.wait()
        async with download_dict_context() as download_dict:
            if listener.uid not in download_dict:
                await executor.do(api.logout, ())
                if folder_api is not None:
                    await executor.do(folder_api.logout, ())
                return
        from_queue = True
        LOGGER.info(f'Start Queued Download from Mega: {name}')
    else:
        from_queue = False

    async with download_dict_context() as download_dict:
        download_dict[listener.uid] = MegaDownloadStatus(name, size, gid, mega_listener, listener.message, listener.upload_details)
    async with queue_dict_context() as non_queued_dl:
        non_queued_dl.add(listener.uid)

    if from_queue:
        LOGGER.info(f'Start Queued Download from Mega: {name}')
    else:
        await listener.onDownloadStart()
        await sendStatusMessage(listener.message)
        LOGGER.info(f"Download from Mega: {name}")

    await aiofiles.os.makedirs(path, exist_ok=True)
    await executor.do(api.startDownload, (node, path, name, None, False, None))
    await executor.do(api.logout, ())
    if folder_api is not None:
        await executor.do(folder_api.logout, ())
