from asyncio import Event

from mega import MegaApi, MegaError, MegaListener, MegaRequest, MegaTransfer

from ... import LOGGER
from ..ext_utils.bot_utils import async_to_sync, sync_to_async


class AsyncMega:
    def __init__(self):
        self.api = None
        self.folder_api = None
        self.continue_event = Event()

    async def run(self, function, *args, **kwargs):
        self.continue_event.clear()
        await sync_to_async(function, *args, **kwargs)
        await self.continue_event.wait()

    async def logout(self):
        await self.run(self.api.logout)
        if self.folder_api:
            await self.run(self.folder_api.logout)

    def __getattr__(self, name):
        attr = getattr(self.api, name)
        if callable(attr):

            async def wrapper(*args, **kwargs):
                return await self.run(attr, *args, **kwargs)

            return wrapper
        return attr


class MegaAppListener(MegaListener):
    _NO_EVENT_ON = (MegaRequest.TYPE_LOGIN, MegaRequest.TYPE_FETCH_NODES)

    def __init__(self, continue_event: Event, listener):
        self.continue_event = continue_event
        self.node = None
        self.public_node = None
        self.listener = listener
        self.is_cancelled = False
        self.error = None
        self._bytes_transferred = 0
        self._speed = 0
        self._name = ""
        super().__init__()

    @property
    def speed(self):
        return self._speed

    @property
    def downloaded_bytes(self):
        return self._bytes_transferred

    def onRequestFinish(self, api, request, error):
        if str(error).lower() != "no error":
            self.error = error.copy()
            if str(self.error).casefold() != "not found":
                LOGGER.error(f"Mega onRequestFinishError: {self.error}")
            self.continue_event.set()
            return

        request_type = request.getType()

        if request_type == MegaRequest.TYPE_LOGIN:
            api.fetchNodes()
        elif request_type == MegaRequest.TYPE_GET_PUBLIC_NODE:
            self.public_node = request.getPublicMegaNode()
            self._name = self.public_node.getName()
        elif request_type == MegaRequest.TYPE_FETCH_NODES:
            LOGGER.info("Fetching Root Node.")
            self.node = api.getRootNode()
            self._name = self.node.getName()
            LOGGER.info(f"Node Name: {self.node.getName()}")

        if request_type not in self._NO_EVENT_ON or (
            self.node and "cloud drive" not in self._name.lower()
        ):
            self.continue_event.set()

    def onRequestTemporaryError(self, api, request, error: MegaError):
        LOGGER.error(f"Mega Request error in {error}")
        if not self.is_cancelled:
            self.is_cancelled = True
            async_to_sync(
                self.listener.on_download_error, f"RequestTempError: {error.toString()}"
            )
        self.error = error.toString()
        self.continue_event.set()

    def onTransferUpdate(self, api: MegaApi, transfer: MegaTransfer):
        if self.is_cancelled:
            api.cancelTransfer(transfer, None)
            self.continue_event.set()
            return
        self._speed = transfer.getSpeed()
        self._bytes_transferred = transfer.getTransferredBytes()

    def onTransferFinish(self, api: MegaApi, transfer: MegaTransfer, error):
        try:
            if self.is_cancelled:
                self.continue_event.set()
            elif transfer.isFinished() and (
                transfer.isFolderTransfer() or transfer.getFileName() == self._name
            ):
                async_to_sync(self.listener.on_download_complete)
                self.continue_event.set()
        except Exception as e:
            LOGGER.error(e)

    def onTransferTemporaryError(self, api, transfer, error):
        LOGGER.error(f"Mega download error in file {transfer.getFileName()}: {error}")
        if transfer.getState() in [1, 4]:
            return
        self.error = f"TransferTempError: {error.toString()} ({transfer.getFileName()})"
        if not self.is_cancelled:
            self.is_cancelled = True
            self.continue_event.set()

    async def cancel_task(self):
        self.is_cancelled = True
        await self.listener.on_download_error("Download Canceled by user")
