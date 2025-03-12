from asyncio import Event

from mega.mega import MegaApi, MegaError, MegaListener, MegaRequest, MegaTransfer

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
        super().__init__()
        self.continue_event = continue_event
        self.node = None
        self.public_node = None
        self.listener = listener
        self.is_cancelled = False
        self.error = None
        self._bytes_transferred = 0
        self._speed = 0
        self._name = ""

    @property
    def speed(self):
        return self._speed

    @property
    def downloaded_bytes(self):
        return self._bytes_transferred

    def onRequestFinish(self, api, request, error):
        if error and str(error).lower() != "no error":
            self.error = error.copy()
            if str(self.error).casefold() != "not found":
                LOGGER.error(f"Mega onRequestFinishError: {self.error}")
            self.continue_event.set()
            return

        request = request.copy()
        request_type = request.getType()

        if request_type == MegaRequest.TYPE_LOGIN:
            api.fetchNodes()
        elif request_type == MegaRequest.TYPE_GET_PUBLIC_NODE:
            self.public_node = request.getPublicMegaNode().copy() if request.getPublicMegaNode() else None
            if self.public_node:
                self._name = self.public_node.getName()
            else:
                LOGGER.error("Error: Public node is None.")
        elif request_type == MegaRequest.TYPE_FETCH_NODES:
            LOGGER.info("Fetching Root Node.")
            self.node = api.getRootNode().copy() if api.getRootNode() else None
            if self.node:
                self._name = self.node.getName()
                LOGGER.info(f"Node Name: {self.node.getName()}")

        if request_type not in self._NO_EVENT_ON or (
            self.node and "cloud drive" not in self._name.lower()
        ):
            self.continue_event.set()

    def onRequestTemporaryError(self, api, request, error: MegaError):
        error_msg = error.toString() if error else "Unknown error"
        LOGGER.error(f"Mega Request error in {error_msg}")

        if not self.is_cancelled:
            self.is_cancelled = True
            async_to_sync(self.listener.on_download_error, f"RequestTempError: {error_msg}")

        self.error = error_msg
        self.continue_event.set()

    def onTransferUpdate(self, api: MegaApi, transfer: MegaTransfer):
        transfer = transfer.copy()
        if self.is_cancelled:
            api.cancelTransfer(transfer, None)
            self.continue_event.set()
            return
        self._speed = transfer.getSpeed()
        self._bytes_transferred = transfer.getTransferredBytes()

    def onTransferFinish(self, api: MegaApi, transfer: MegaTransfer, error):
        try:
            transfer = transfer.copy()
            if self.is_cancelled:
                self.continue_event.set()
            elif transfer.isFinished() and (
                transfer.isFolderTransfer() or transfer.getFileName() == self._name
            ):
                async_to_sync(self.listener.on_download_complete, transfer.getFileName())
                self.continue_event.set()
        except Exception as e:
            LOGGER.error(e)

    def onTransferTemporaryError(self, api, transfer, error):
        error_msg = error.toString() if error else "Unknown transfer error"
        LOGGER.error(f"Mega download error in file {transfer.getFileName()}: {error_msg}")

        if transfer.getState() in [1, 4]:
            return

        self.error = f"TransferTempError: {error_msg} ({transfer.getFileName()})"

        if not self.is_cancelled:
            self.is_cancelled = True
            self.continue_event.set()

    async def cancel_task(self):
        self.is_cancelled = True
        await self.listener.on_download_error("Download Canceled by user")
    