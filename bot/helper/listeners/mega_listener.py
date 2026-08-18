from asyncio import (
    Event,
    Lock as AsyncLock,
    sleep as asleep,
    wait_for,
    wrap_future,
    TimeoutError as AsyncTimeoutError,
)
from threading import Event as ThreadEvent
from concurrent.futures import Future
from re import match as rematch
from time import time

from mega import (
    MegaApi,
    MegaError,
    MegaListener,
    MegaRequest,
    MegaTransfer,
    MegaUploadOptions,
)

from ... import LOGGER, bot_loop
from ..ext_utils.bot_utils import async_to_sync, sync_to_async


async def mega_cleanup():
    from ... import task_dict, task_dict_lock

    tasks = []
    async with task_dict_lock:
        for tk in list(task_dict.values()):
            if hasattr(tk, "_obj") and hasattr(tk._obj, "cancel_task"):
                tasks.append(tk._obj)
    for obj in tasks:
        try:
            await obj.cancel_task()
        except Exception:
            pass


_MEGA_SDK_LOCK = AsyncLock()
_REQUEST_TIMEOUT_SECONDS = 300
_LOGOUT_TIMEOUT_SECONDS = 30

MEGA_ERRORS = {
    -30: "Sub-user encryption key missing",
    -29: "Paywall – upgrade required",
    -28: "Business account payment past due",
    -27: "Master account only operation",
    -26: "Two-factor authentication required",
    -25: "Transfer rolled back",
    -24: "Transfer quota exceeded, wait before retrying",
    -23: "SSL/TLS connection error",
    -22: "Invalid application key",
    -21: "Read error",
    -20: "Write error",
    -19: "Too many connections",
    -18: "Temporarily unavailable",
    -17: "Storage quota exceeded",
    -16: "Account or file(s) blocked/banned",
    -15: "Session expired or decryption key error",
    -14: "Encryption/decryption error",
    -13: "Incomplete transfer",
    -12: "File(s) already exist",
    -11: "File(s) Access Denied",
    -10: "Circular linkage detected",
    -9: "File(s) not found or deleted",
    -8: "Resource expired",
    -7: "Out of range",
    -6: "Too many requests",
    -5: "Transfer failed",
    -4: "Rate limit exceeded, slowing down",
    -3: "Temporary failure, retrying",
    -2: "Bad arguments",
    -1: "Internal error",
}


def _mega_error_format(raw_error):
    if not raw_error:
        return raw_error
    m = rematch(r"\s*(-?\d+)", str(raw_error))
    if m:
        code = int(m.group(1))
        if code in MEGA_ERRORS:
            return MEGA_ERRORS[code]
    return raw_error


class AsyncMega:
    def __init__(self):
        self.api = None
        self.continue_event = Event()
        self._transfer_future = None
        self._export_future = None
        self._export_event = None
        self._expected_request_type = None
        self._expected_request_source = None
        self._download_is_folder = False
        self.folder_api = None
        self._folder_listener = None
        self._request_future = None

    def _download_api(self):
        return self.folder_api or self.api

    def _request_type_for_name(self, name):
        request_types = {
            "login": getattr(MegaRequest, "TYPE_LOGIN", None),
            "loginToFolder": getattr(MegaRequest, "TYPE_LOGIN", None),
            "fetchNodes": getattr(MegaRequest, "TYPE_FETCH_NODES", None),
            "getPublicNode": getattr(MegaRequest, "TYPE_GET_PUBLIC_NODE", None),
            "logout": getattr(MegaRequest, "TYPE_LOGOUT", None),
            "getAccountDetails": getattr(MegaRequest, "TYPE_ACCOUNT_DETAILS", None),
            "exportNode": getattr(MegaRequest, "TYPE_EXPORT", None),
            "createFolder": getattr(MegaRequest, "TYPE_CREATE_FOLDER", None),
            "importFileLink": getattr(MegaRequest, "TYPE_IMPORT_LINK", None),
        }
        return request_types.get(name)

    def _request_type_for(self, function):
        return self._request_type_for_name(getattr(function, "__name__", ""))

    async def run(
        self,
        function,
        *args,
        expected_type=None,
        expected_source="main",
        timeout=None,
        **kwargs,
    ):
        fn_name = getattr(function, "__name__", "unknown")
        timeout = _REQUEST_TIMEOUT_SECONDS if timeout is None else timeout
        future = Future()
        self._request_future = future
        self._expected_request_type = (
            self._request_type_for(function) if expected_type is None else expected_type
        )
        self._expected_request_source = expected_source

        try:
            LOGGER.info("Mega: run(%s, src=%s)", fn_name, expected_source)
            await sync_to_async(function, *args, **kwargs)
            await asleep(0)
            try:
                await wait_for(wrap_future(future), timeout=timeout)
            except AsyncTimeoutError:
                msg = (
                    f"Mega SDK timed out after {timeout}s waiting for "
                    f"{fn_name} ({expected_source})"
                )
                LOGGER.error(msg)
                for attr in ("_mega_listener", "_folder_listener"):
                    lst = getattr(self, attr, None)
                    if lst is not None and not lst.error:
                        lst.error = msg
                if (
                    self._transfer_future is not None
                    and not self._transfer_future.done()
                ):
                    self._transfer_future.set_result(True)
        finally:
            self._request_future = None
            self._expected_request_type = None
            self._expected_request_source = None

    async def wait_for_transfer(self):
        if self._transfer_future is None:
            LOGGER.error("Mega wait_for_transfer called without active transfer")
            return
        await asleep(0)
        try:
            await wait_for(wrap_future(self._transfer_future), timeout=43200)
        except AsyncTimeoutError:
            LOGGER.error("Mega transfer timed out after 12h")
            if self._transfer_future is not None and not self._transfer_future.done():
                self._transfer_future.set_result(True)

    async def export_node(self, node, expireTime=0, writable=False, megaHosted=False):
        future = Future()
        self._request_future = future
        self._expected_request_type = MegaRequest.TYPE_EXPORT
        self._expected_request_source = "main"
        try:
            await sync_to_async(
                self.api.exportNode,
                node,
                expireTime,
                writable,
                megaHosted,
            )
            await wait_for(wrap_future(future), timeout=_REQUEST_TIMEOUT_SECONDS)
            ml = getattr(self, "_mega_listener", None)
            return getattr(ml, "_export_link", None) if ml else None
        except AsyncTimeoutError:
            LOGGER.error("export_node timed out waiting for TYPE_EXPORT callback")
            return None
        finally:
            self._request_future = None
            self._expected_request_type = None
            self._expected_request_source = None

    async def create_folder(self, name, parent):
        ml = getattr(self, "_mega_listener", None)
        future = Future()
        self._request_future = future
        self._expected_request_type = MegaRequest.TYPE_CREATE_FOLDER
        self._expected_request_source = "main"
        if ml:
            ml._created_folder_node = None
        try:
            await sync_to_async(self.api.createFolder, name, parent)
            await wait_for(wrap_future(future), timeout=_REQUEST_TIMEOUT_SECONDS)
            node = getattr(ml, "_created_folder_node", None) if ml else None
            if not node:
                LOGGER.warning(
                    f"create_folder: no node for '{name}', falling back to child scan"
                )
                node = await self._find_child_by_name(parent, name)
            return node
        except AsyncTimeoutError:
            LOGGER.error(f"create_folder timed out for '{name}'")
            return None
        except Exception as e:
            LOGGER.warning(
                f"create_folder failed for '{name}' (may already exist): {e}"
            )
            try:
                node = await self._find_child_by_name(parent, name)
                if node:
                    return node
            except Exception:
                pass
            return None
        finally:
            self._request_future = None
            self._expected_request_type = None
            self._expected_request_source = None

    async def _find_child_by_name(self, parent, name):
        try:
            children = await sync_to_async(self.api.getChildren, parent)
            if children:
                for i in range(children.size()):
                    child = children.get(i)
                    try:
                        if child.getName() == name:
                            return child
                    except Exception:
                        pass
        except Exception as e:
            LOGGER.warning(f"_find_child_by_name failed for '{name}': {e}")
        return None

    async def import_link(self, link, parent, auto_export=False):
        ml = getattr(self, "_mega_listener", None)
        future = Future()
        self._request_future = future
        self._expected_request_type = MegaRequest.TYPE_IMPORT_LINK
        self._expected_request_source = "main"
        export_future = None
        export_event = None
        if ml:
            ml._export_link = None
            ml._auto_export = auto_export
            if auto_export:
                export_future = Future()
                self._export_future = export_future
                export_event = ThreadEvent()
                self._export_event = export_event
        try:
            await sync_to_async(self.api.importFileLink, link, parent)
            await wait_for(wrap_future(future), timeout=_REQUEST_TIMEOUT_SECONDS)
            import_ok = bool(ml and ml._import_success)
            if not import_ok:
                LOGGER.warning("import_link: no node returned for link")
                return None
            if auto_export and export_event:
                exp_ok = await sync_to_async(
                    export_event.wait, timeout=_REQUEST_TIMEOUT_SECONDS
                )
                if not exp_ok:
                    LOGGER.error("Mega: export event TIMEOUT")
                elink = getattr(ml, "_export_link", None) if ml else None
                return True, elink
            return True
        except AsyncTimeoutError:
            LOGGER.error("import_link timed out")
            if auto_export:
                return None, None
            return None
        except Exception as e:
            LOGGER.error(f"import_link failed: {e}", exc_info=True)
            if auto_export:
                return None, None
            return None
        finally:
            self._request_future = None
            self._expected_request_type = None
            self._expected_request_source = None
            if ml:
                ml._auto_export = False
                self._export_future = None
                self._export_event = None

    async def logout(self):
        if self.folder_api:
            await self.run(
                self.folder_api.logout,
                False,
                None,
                expected_type=self._request_type_for_name("logout"),
                timeout=_LOGOUT_TIMEOUT_SECONDS,
            )
        if self.api:
            await self.run(
                self.api.logout,
                False,
                None,
                expected_type=self._request_type_for_name("logout"),
                timeout=_LOGOUT_TIMEOUT_SECONDS,
            )

    async def fetchNodes(self, api=None):
        api = api or self.api
        return await self.run(
            api.fetchNodes,
            expected_type=self._request_type_for_name("fetchNodes"),
        )

    async def loginToFolder(self, link):
        api = self.folder_api or self.api
        return await self.run(
            api.loginToFolder,
            link,
            expected_type=self._request_type_for_name("loginToFolder"),
        )

    async def startDownload(
        self,
        node,
        localPath,
        name,
        listener,
        startFirst,
        cancelToken,
        collisionCheck,
        collisionResolution,
        undelete,
    ):
        self._transfer_future = Future()

        ml = getattr(self, "_folder_listener", None) or getattr(
            self, "_mega_listener", None
        )
        if ml:
            self._download_is_folder = ml._is_folder
            if not ml._name:
                ml._name = name
            ml._target_handle = ml._handle
            ml._bytes_transferred = 0
            ml._total_downloaded_bytes = 0
            ml._speed = 0
            ml._smoothed_speed = 0

        await sync_to_async(
            self._download_api().startDownload,
            node,
            localPath,
            name,
            listener,
            startFirst,
            cancelToken,
            collisionCheck,
            collisionResolution,
            undelete,
        )

    async def startUpload(
        self, localPath, parentNode, customName, cancelToken, mtime=-1
    ):
        self._transfer_future = Future()
        LOGGER.info("Mega: startUpload for %s", customName)

        options = MegaUploadOptions.createInstance()
        options.fileName = customName
        options.mtime = mtime
        options.isSourceTemporary = False

        ml = getattr(self, "_mega_listener", None)
        if ml:
            ml._bytes_transferred = 0
            ml._total_downloaded_bytes = 0
            ml._speed = 0
            ml._smoothed_speed = 0
            ml._target_handle = parentNode.getHandle() if parentNode else None
            ml._target_name = customName
            ml._uploaded_node_handle = None
            ml._export_link = None

        await sync_to_async(
            self.api.startUpload,
            localPath,
            parentNode,
            cancelToken,
            options,
        )

    def __getattr__(self, name):
        attr = getattr(self.api, name)
        if callable(attr):

            async def wrapper(*args, **kwargs):
                return await self.run(
                    attr,
                    *args,
                    expected_type=self._request_type_for_name(name),
                    **kwargs,
                )

            return wrapper
        return attr


class MegaAppListener(MegaListener):
    def __init__(self, async_api: AsyncMega, listener):
        self._async_api = async_api
        self.continue_event = async_api.continue_event
        self.listener = listener
        self.is_cancelled = False
        self.error = None
        self.retryable_error = None
        self._suppress_export = False
        self._bytes_transferred = 0
        self._total_downloaded_bytes = 0
        self._total_folder_size = 0
        self._current_transfer = None
        self._speed = 0
        self._smoothed_speed = 0
        self._last_speed_time = 0
        self._caller_manages_completion = False
        self._completion_sent = False
        self._cancel_token = None
        self._upload_mode = False
        self.node = None
        self.public_node = None
        self._name = ""
        self._size = 0
        self._handle = None
        self._is_folder = False
        self._target_handle = None
        self._uploaded_node_handle = None
        self._created_folder_node = None
        self._import_success = False
        self._imported_node_name = None
        self._imported_node_size = 0
        self._imported_node_is_folder = False
        self._auto_export = False
        self._export_link = None
        super().__init__()

    @property
    def speed(self):
        if self._last_speed_time and (time() - self._last_speed_time) > 2:
            return 0
        return int(self._smoothed_speed)

    @property
    def downloaded_bytes(self):
        return self._total_downloaded_bytes + self._bytes_transferred

    def _set_request_event(self):
        try:
            bot_loop.call_soon_threadsafe(self.continue_event.set)
        except Exception as e:
            LOGGER.error(f"Mega request event signal failed: {e}")
        try:
            fut = self._async_api._request_future
            if fut is not None and not fut.done():
                fut.set_result(True)
        except Exception as e:
            LOGGER.error(f"Mega request future resolve failed: {e}")

    def _set_transfer_event(self):
        try:
            fut = self._async_api._transfer_future
            if fut is not None and not fut.done():
                fut.set_result(True)
        except Exception as e:
            LOGGER.error(f"Mega transfer future resolve failed: {e}")

    def _set_export_done(self):
        try:
            fut = self._async_api._export_future
            if fut is not None and not fut.done():
                fut.set_result(True)
        except Exception as e:
            LOGGER.error(f"Mega export future resolve failed: {e}")
        try:
            evt = self._async_api._export_event
            if evt is not None:
                evt.set()
        except Exception as e:
            LOGGER.error(f"Mega export event set failed: {e}")

    def _clear_export_done(self):
        try:
            self._async_api._export_future = Future()
        except Exception as e:
            LOGGER.error(f"Mega export future create failed: {e}")

    def _cache_node_data(self, node):
        try:
            self._name = node.getName()
        except Exception:
            pass
        try:
            self._handle = node.getHandle()
        except Exception:
            pass
        try:
            self._is_folder = node.isFolder()
        except Exception:
            pass

    def _is_expected_request(self, request_type):
        expected = self._async_api._expected_request_type
        return expected is None or request_type == expected

    def _is_expected_source(self, source):
        expected = self._async_api._expected_request_source
        return expected is None or source == expected

    def _is_target_transfer(self, transfer):
        if self._upload_mode:
            try:
                expected = getattr(self, "_target_name", None)
                return expected is not None and transfer.getFileName() == expected
            except Exception:
                return False
        if self._async_api._download_is_folder:
            try:
                return transfer.isFolderTransfer()
            except Exception:
                return False
        target_match = False
        if self._target_handle is not None:
            try:
                if transfer.getNodeHandle() == self._target_handle:
                    target_match = True
            except Exception:
                pass
        if not target_match:
            try:
                if transfer.getFileName() == self._name:
                    target_match = True
            except Exception:
                pass
        return target_match

    def onRequestFinish(self, api, request, error, source="main"):
        try:
            request_type = request.getType()
            err_code = error.getErrorCode() if error else MegaError.API_OK
            if err_code != MegaError.API_OK:
                if self.is_cancelled:
                    self._set_request_event()
                    self._set_transfer_event()
                    return
                if err_code in (MegaError.API_EAGAIN, MegaError.API_ERATELIMIT):
                    return
                if not (
                    self._is_expected_request(request_type)
                    and self._is_expected_source(source)
                ):
                    return
                self.error = f"{err_code} {error.toString()}"
                LOGGER.error(f"Mega onRequestFinishError: {self.error}")
                self._set_request_event()
                self._set_transfer_event()
                return

            if self.is_cancelled:
                self._set_request_event()
                self._set_transfer_event()
                return

            LOGGER.info(
                "Mega: onRequestFinish type=%s source=%s err=%s",
                request_type,
                source,
                err_code,
            )
            if request_type == MegaRequest.TYPE_GET_PUBLIC_NODE:
                try:
                    self.public_node = request.getPublicMegaNode()
                except Exception:
                    self.public_node = None
                if self.public_node:
                    self._cache_node_data(self.public_node)
                    try:
                        self._size = self.public_node.getSize()
                    except Exception:
                        pass
            elif request_type == MegaRequest.TYPE_LOGIN:
                try:
                    fut = self._async_api._request_future
                    if fut is not None and not fut.done():
                        fut.set_result(True)
                except Exception:
                    pass
            elif request_type == MegaRequest.TYPE_FETCH_NODES:
                root_node = api.getRootNode()
                if not root_node:
                    try:
                        root_node = api.getNodeByPath("/", None)
                    except Exception:
                        pass
                LOGGER.info("MEGA DEBUG FETCH: root=%s", root_node)
                self.node = root_node
                if self.node:
                    LOGGER.info("MEGA DEBUG FETCH: name=%s handle=%s folder=%s", self.node.getName(), self.node.getHandle(), self.node.isFolder())
                    self._cache_node_data(self.node)
                    try:
                        self._size = self.node.getSize()
                    except Exception:
                        pass
            elif request_type == MegaRequest.TYPE_EXPORT:
                try:
                    self._export_link = request.getLink()
                except Exception:
                    pass
                self._set_export_done()
            elif request_type == MegaRequest.TYPE_CREATE_FOLDER:
                try:
                    handle = request.getNodeHandle()
                    node = api.getNodeByHandle(handle) if handle else None
                    if node:
                        self._created_folder_node = node
                except Exception:
                    pass
                try:
                    fut = self._async_api._request_future
                    if fut is not None and not fut.done():
                        fut.set_result(True)
                except Exception:
                    pass
            elif request_type == MegaRequest.TYPE_IMPORT_LINK:
                try:
                    handle = request.getNodeHandle()
                    node = api.getNodeByHandle(handle) if handle else None
                    if node:
                        name = node.getName()
                        size = node.getSize()
                        is_folder = node.isFolder()
                        self._imported_node_name = name
                        self._imported_node_size = size
                        self._imported_node_is_folder = is_folder
                        self._import_success = True
                        if self._auto_export:
                            self._auto_export = False
                            api.exportNode(node, 0, False, False, None)
                except Exception as e:
                    LOGGER.error(f"Mega import link callback error: {e}")

            if self._is_expected_request(request_type) and self._is_expected_source(
                source
            ):
                self._set_request_event()
        except Exception as e:
            self.error = f"Mega request callback exception: {e}"
            LOGGER.error(self.error, exc_info=True)
            self._set_request_event()
            self._set_transfer_event()

    def onRequestTemporaryError(self, api, request, error: MegaError, source="main"):
        try:
            LOGGER.warning(
                "Mega: onRequestTemporaryError source=%s err=%s",
                source,
                error.toString() if error else "?",
            )
        except Exception:
            pass
        if self.is_cancelled:
            self._set_request_event()

    def onTransferStart(self, api, transfer):
        try:
            if not self._is_target_transfer(transfer):
                return
            LOGGER.info("Mega: onTransferStart TARGET name=%s", transfer.getFileName())
            self._current_transfer = transfer
            self._bytes_transferred = 0
            self._set_request_event()
        except Exception as e:
            LOGGER.error(f"Mega transfer start callback exception: {e}", exc_info=True)

    def onTransferUpdate(self, api: MegaApi, transfer: MegaTransfer):
        try:
            if not self._is_target_transfer(transfer):
                return
            if self.is_cancelled:
                token = self._cancel_token
                if token is not None and not token.isCancelled():
                    try:
                        token.cancel()
                    except Exception:
                        pass
                try:
                    api.cancelTransfer(transfer, None)
                except Exception:
                    pass
                return
            self._speed = transfer.getSpeed()
            alpha = 0.3
            self._smoothed_speed = (
                alpha * self._speed + (1 - alpha) * self._smoothed_speed
            )
            self._last_speed_time = time()
            self._bytes_transferred = transfer.getTransferredBytes()
            total = transfer.getTotalBytes()
            if total > self._total_folder_size:
                self._total_folder_size = total
        except Exception as e:
            LOGGER.error(f"Mega transfer update callback exception: {e}", exc_info=True)

    def onTransferFinish(self, api: MegaApi, transfer: MegaTransfer, error):
        try:
            err_code = error.getErrorCode() if error else MegaError.API_OK
            if self.is_cancelled:
                self._set_transfer_event()
                return

            if not self._is_target_transfer(transfer):
                return
            LOGGER.info("Mega: onTransferFinish TARGET err=%s", err_code)
            if err_code != MegaError.API_OK:
                self.error = f"{err_code} {error.toString()}"
                if err_code == MegaError.API_EINCOMPLETE:
                    self.retryable_error = self.error
                    self._set_transfer_event()
                    return
                LOGGER.error(f"Mega onTransferFinishError: {self.error}")
                self.is_cancelled = True
                if not self._upload_mode:
                    async_to_sync(
                        self.listener.on_download_error, _mega_error_format(self.error)
                    )
                self._set_transfer_event()
                return
            self.retryable_error = None
            if not self._caller_manages_completion:
                async_to_sync(self.listener.on_download_complete)
            else:
                try:
                    self._uploaded_node_handle = transfer.getNodeHandle()
                except Exception as e:
                    LOGGER.warning(f"onTransferFinish: getNodeHandle failed: {e}")
                if self._upload_mode and self._bytes_transferred == 0 and self._size:
                    self._bytes_transferred = self._size
                    self._last_speed_time = time()
                if (
                    self._upload_mode
                    and transfer.getType() == MegaTransfer.TYPE_UPLOAD
                    and not self._suppress_export
                ):
                    self._clear_export_done()
                    try:
                        node = None
                        handle = self._uploaded_node_handle
                        if handle:
                            node = api.getNodeByHandle(handle)
                        if not node:
                            parent = api.getNodeByHandle(transfer.getParentHandle())
                            if parent:
                                name = transfer.getFileName()
                                children = api.getChildren(parent)
                                if children:
                                    for i in range(children.size()):
                                        child = children.get(i)
                                        try:
                                            if child.getName() == name:
                                                node = child
                                                break
                                        except Exception:
                                            pass
                        if node:
                            api.exportNode(node, 0, False, False, None)
                        else:
                            LOGGER.warning(
                                "onTransferFinish: node not found for export"
                            )
                            self._set_export_done()
                    except Exception as e:
                        LOGGER.error(f"onTransferFinish: export failed: {e}")
                        self._set_export_done()
            self._set_transfer_event()
        except Exception as e:
            LOGGER.error(f"onTransferFinish exception: {e}")
            self._set_transfer_event()

    def onTransferTemporaryError(self, api, transfer, error):
        try:
            if self.is_cancelled:
                return
            if not self._is_target_transfer(transfer):
                return
            err_code = error.getErrorCode() if error else 0
            err_str = error.toString() if error else "unknown"
            LOGGER.warning("Mega: onTransferTemporaryError err=%s", err_code)
            if err_code == MegaError.API_EOVERQUOTA:
                msg = f"TransferTempError: Over quota: {err_str}"
                self.error = msg
                self.is_cancelled = True
                if not self._upload_mode:
                    async_to_sync(
                        self.listener.on_download_error, _mega_error_format(msg)
                    )
                self._set_transfer_event()
                return
            if err_code == MegaError.API_EINCOMPLETE:
                self.retryable_error = f"{err_code} {err_str}"
        except Exception as e:
            LOGGER.error(
                f"Mega transfer temporary-error callback exception: {e}",
                exc_info=True,
            )

    async def cancel_task(self):
        if self.is_cancelled:
            return
        self.is_cancelled = True
        token = self._cancel_token
        if token is not None and not token.isCancelled():
            try:
                token.cancel()
            except Exception as e:
                LOGGER.error(f"Mega cancel-token cancel failed: {e}")
        current = getattr(self, "_current_transfer", None)
        if current is not None:
            try:
                self._async_api.api.cancelTransfer(current, None)
            except Exception as e:
                LOGGER.error(f"Mega cancel-transfer failed: {e}")
        self._set_request_event()
        self._set_transfer_event()

    def onUsersUpdate(self, api, users):
        pass

    def onUserAlertsUpdate(self, api, alerts):
        pass

    def onNodesUpdate(self, api, nodes):
        pass

    def onAccountUpdate(self, api):
        pass

    def onSetsUpdate(self, api, sets):
        pass

    def onSetElementsUpdate(self, api, elements):
        pass

    def onContactRequestsUpdate(self, api, requests):
        pass

    def onReloadNeeded(self, api):
        pass

    def onSyncFileStateChanged(self, *args):
        pass

    def onSyncAdded(self, *args):
        pass

    def onSyncDeleted(self, *args):
        pass

    def onSyncStateChanged(self, *args):
        pass

    def onSyncStatsUpdated(self, *args):
        pass

    def onGlobalSyncStateChanged(self, api):
        pass

    def onSyncRemoteRootChanged(self, *args):
        pass

    def onBackupStateChanged(self, *args):
        pass

    def onBackupStart(self, *args):
        pass

    def onBackupFinish(self, *args):
        pass

    def onBackupUpdate(self, *args):
        pass

    def onBackupTemporaryError(self, *args):
        pass

    def onChatsUpdate(self, api, chats):
        pass

    def onEvent(self, api, event):
        pass

    def onMountAdded(self, *args):
        pass

    def onMountChanged(self, *args):
        pass


class MegaFolderListener(MegaListener):
    def __init__(self, async_api: AsyncMega, listener):
        self._async_api = async_api
        self.listener = listener
        self.is_cancelled = False
        self.error = None
        self.retryable_error = None
        self._bytes_transferred = 0
        self._total_downloaded_bytes = 0
        self._total_folder_size = 0
        self._current_transfer = None
        self._speed = 0
        self._smoothed_speed = 0
        self._last_speed_time = 0
        self._cancel_token = None
        self.node = None
        self.public_node = None
        self._name = ""
        self._size = 0
        self._handle = None
        self._is_folder = True
        self._target_handle = None
        self._children = None
        self._caller_manages_completion = False
        super().__init__()

    @property
    def speed(self):
        if self._last_speed_time and (time() - self._last_speed_time) > 2:
            return 0
        return int(self._smoothed_speed)

    @property
    def downloaded_bytes(self):
        return self._total_downloaded_bytes + self._bytes_transferred

    def _set_request_event(self):
        try:
            fut = self._async_api._request_future
            if fut is not None and not fut.done():
                fut.set_result(True)
        except Exception as e:
            LOGGER.error(f"MegaFolder request future resolve failed: {e}")

    def _set_transfer_event(self):
        try:
            fut = self._async_api._transfer_future
            if fut is not None and not fut.done():
                fut.set_result(True)
        except Exception as e:
            LOGGER.error(f"MegaFolder transfer future resolve failed: {e}")

    def _cache_node_data(self, node):
        try:
            self._name = node.getName()
        except Exception:
            pass
        try:
            self._handle = node.getHandle()
        except Exception:
            pass

    def _is_expected_request(self, request_type):
        expected = self._async_api._expected_request_type
        return expected is None or request_type == expected

    def _is_expected_source(self, source):
        expected = self._async_api._expected_request_source
        return expected is None or source == expected

    def _is_target_transfer(self, transfer):
        if self._async_api._download_is_folder:
            try:
                return transfer.isFolderTransfer()
            except Exception:
                return False
        target_match = False
        if self._target_handle is not None:
            try:
                if transfer.getNodeHandle() == self._target_handle:
                    target_match = True
            except Exception:
                pass
        if not target_match:
            try:
                if transfer.getFileName() == self._name:
                    target_match = True
            except Exception:
                pass
        return target_match

    def onRequestFinish(self, api, request, error, source="main"):
        try:
            request_type = request.getType()
            err_code = error.getErrorCode() if error else MegaError.API_OK
            if err_code != MegaError.API_OK:
                if self.is_cancelled:
                    self._set_request_event()
                    self._set_transfer_event()
                    return
                if err_code in (MegaError.API_EAGAIN, MegaError.API_ERATELIMIT):
                    return
                if not (
                    self._is_expected_request(request_type)
                    and self._is_expected_source(source)
                ):
                    return
                self.error = f"{err_code} {error.toString()}"
                LOGGER.error(f"MegaFolder onRequestFinishError: {self.error}")
                self._set_request_event()
                self._set_transfer_event()
                return

            if self.is_cancelled:
                self._set_request_event()
                try:
                    fut = self._async_api._request_future
                    if fut is not None and not fut.done():
                        fut.set_result(True)
                except Exception:
                    pass
                return

            LOGGER.info(
                "MegaFolder: onRequestFinish type=%s source=%s err=%s",
                request_type,
                source,
                err_code,
            )
            if request_type == MegaRequest.TYPE_LOGIN:
                try:
                    fut = self._async_api._request_future
                    if fut is not None and not fut.done():
                        fut.set_result(True)
                except Exception:
                    pass
            elif request_type == MegaRequest.TYPE_FETCH_NODES:
                root_node = api.getRootNode()
                if not root_node:
                    try:
                        root_node = api.getNodeByPath("/", None)
                    except Exception:
                        pass
                self.node = root_node
                if self.node:
                    self._cache_node_data(self.node)
                    self._size = api.getSize(self.node)
                    try:
                        self._children = api.getChildren(self.node)
                    except Exception:
                        pass

            if self._is_expected_request(request_type) and self._is_expected_source(
                source
            ):
                self._set_request_event()
        except Exception as e:
            self.error = f"MegaFolder request callback exception: {e}"
            LOGGER.error(self.error, exc_info=True)
            self._set_request_event()
            self._set_transfer_event()

    def onRequestTemporaryError(self, api, request, error: MegaError, source="main"):
        try:
            LOGGER.warning(
                "MegaFolder: onRequestTemporaryError source=%s err=%s",
                source,
                error.toString() if error else "?",
            )
        except Exception:
            pass
        if self.is_cancelled:
            self._set_request_event()

    def onTransferStart(self, api, transfer):
        try:
            if not self._is_target_transfer(transfer):
                return
            LOGGER.info(
                "MegaFolder: onTransferStart TARGET name=%s", transfer.getFileName()
            )
            self._current_transfer = transfer
            self._bytes_transferred = 0
            self._set_request_event()
        except Exception as e:
            LOGGER.error(
                f"MegaFolder transfer start callback exception: {e}", exc_info=True
            )

    def onTransferUpdate(self, api: MegaApi, transfer: MegaTransfer):
        try:
            if not self._is_target_transfer(transfer):
                return
            if self.is_cancelled:
                token = self._cancel_token
                if token is not None and not token.isCancelled():
                    try:
                        token.cancel()
                    except Exception:
                        pass
                try:
                    api.cancelTransfer(transfer, None)
                except Exception:
                    pass
                return
            self._speed = transfer.getSpeed()
            alpha = 0.3
            self._smoothed_speed = (
                alpha * self._speed + (1 - alpha) * self._smoothed_speed
            )
            self._last_speed_time = time()
            self._bytes_transferred = transfer.getTransferredBytes()
            total = transfer.getTotalBytes()
            if total > self._total_folder_size:
                self._total_folder_size = total
                if total > 0 and hasattr(self, "listener"):
                    self.listener.size = total
        except Exception as e:
            LOGGER.error(
                f"MegaFolder transfer update callback exception: {e}", exc_info=True
            )

    def onTransferFinish(self, api: MegaApi, transfer: MegaTransfer, error):
        try:
            err_code = error.getErrorCode() if error else MegaError.API_OK
            if self.is_cancelled:
                self._set_transfer_event()
                return

            if not self._is_target_transfer(transfer):
                return
            transferred = transfer.getTransferredBytes()
            total = transfer.getTotalBytes()
            speed = transfer.getSpeed()
            state = transfer.getState()
            LOGGER.info("MegaFolder: onTransferFinish TARGET err=%s transferred=%s total=%s speed=%s state=%s", err_code, transferred, total, speed, state)
            if err_code != MegaError.API_OK:
                self.error = f"{err_code} {error.toString()}"
                if err_code == MegaError.API_EINCOMPLETE:
                    self.retryable_error = self.error
                    self._set_transfer_event()
                    return
                LOGGER.error(f"MegaFolder onTransferFinishError: {self.error}")
                self.is_cancelled = True
                async_to_sync(
                    self.listener.on_download_error, _mega_error_format(self.error)
                )
                self._set_transfer_event()
                return
            self.retryable_error = None
            async_to_sync(self.listener.on_download_complete)
            self._set_transfer_event()
        except Exception as e:
            LOGGER.error(f"MegaFolder onTransferFinish exception: {e}")
            self._set_transfer_event()

    def onTransferTemporaryError(self, api, transfer, error):
        try:
            if self.is_cancelled:
                return
            if not self._is_target_transfer(transfer):
                return
            err_code = error.getErrorCode() if error else 0
            err_str = error.toString() if error else "unknown"
            LOGGER.warning("MegaFolder: onTransferTemporaryError err=%s", err_code)
            if err_code == MegaError.API_EOVERQUOTA:
                msg = f"TransferTempError: Over quota: {err_str}"
                self.error = msg
                self.is_cancelled = True
                async_to_sync(self.listener.on_download_error, _mega_error_format(msg))
                self._set_transfer_event()
                return
            if err_code == MegaError.API_EINCOMPLETE:
                self.retryable_error = f"{err_code} {err_str}"
        except Exception as e:
            LOGGER.error(
                f"MegaFolder transfer temporary-error callback exception: {e}",
                exc_info=True,
            )

    async def cancel_task(self):
        if self.is_cancelled:
            return
        self.is_cancelled = True
        token = self._cancel_token
        if token is not None and not token.isCancelled():
            try:
                token.cancel()
            except Exception as e:
                LOGGER.error(f"MegaFolder cancel-token cancel failed: {e}")
        current = getattr(self, "_current_transfer", None)
        if current is not None:
            try:
                self._async_api._download_api().cancelTransfer(current, None)
            except Exception as e:
                LOGGER.error(f"MegaFolder cancel-transfer failed: {e}")
        self._set_request_event()
        self._set_transfer_event()

    def onUsersUpdate(self, api, users):
        pass

    def onUserAlertsUpdate(self, api, alerts):
        pass

    def onNodesUpdate(self, api, nodes):
        pass

    def onAccountUpdate(self, api):
        pass

    def onSetsUpdate(self, api, sets):
        pass

    def onSetElementsUpdate(self, api, elements):
        pass

    def onContactRequestsUpdate(self, api, requests):
        pass

    def onReloadNeeded(self, api):
        pass

    def onSyncFileStateChanged(self, *args):
        pass

    def onSyncAdded(self, *args):
        pass

    def onSyncDeleted(self, *args):
        pass

    def onSyncStateChanged(self, *args):
        pass

    def onSyncStatsUpdated(self, *args):
        pass

    def onGlobalSyncStateChanged(self, api):
        pass

    def onSyncRemoteRootChanged(self, *args):
        pass

    def onBackupStateChanged(self, *args):
        pass

    def onBackupStart(self, *args):
        pass

    def onBackupFinish(self, *args):
        pass

    def onBackupUpdate(self, *args):
        pass

    def onBackupTemporaryError(self, *args):
        pass

    def onChatsUpdate(self, api, chats):
        pass

    def onEvent(self, api, event):
        pass

    def onMountAdded(self, *args):
        pass

    def onMountChanged(self, *args):
        pass
