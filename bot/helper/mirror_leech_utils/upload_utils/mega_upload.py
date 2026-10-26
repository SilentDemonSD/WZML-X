import os
from asyncio import (
    TimeoutError as AsyncTimeoutError,
    wait_for,
    wrap_future,
    sleep as asleep,
)
from contextlib import suppress
from mimetypes import guess_type
from secrets import token_hex

from aiofiles.os import makedirs, path as aiopath
from mega import MegaApi, MegaCancelToken

from .... import LOGGER, task_dict, task_dict_lock
from ...ext_utils.bot_utils import sync_to_async
from ...ext_utils.files_utils import clean_download
from ...listeners.mega_listener import (
    AsyncMega,
    MegaAppListener,
    _mega_error_format,
    _MEGA_SDK_LOCK,
)
from ...mirror_leech_utils.status_utils.mega_status import MegaDownloadStatus
from ...telegram_helper.message_utils import update_status_message


def _make_cancel_token():
    if MegaCancelToken is None:
        return None
    try:
        return MegaCancelToken.createInstance()
    except Exception as e:
        LOGGER.error(f"Mega: failed to create cancel token: {e}")
        return None


def _find_node_by_name(api, parent_node, name):
    try:
        children = api.getChildren(parent_node)
        if children:
            for i in range(children.size()):
                child = children.get(i)
                try:
                    if child.getName() == name:
                        return child
                except Exception:
                    pass
    except Exception as e:
        LOGGER.warning(f"_find_node_by_name error: {e}")
    return None


async def _get_total_size(local_dir):
    total = 0
    walk_result = await sync_to_async(lambda: list(os.walk(local_dir)))
    for root, _, files in walk_result:
        for f in files:
            try:
                total += await aiopath.getsize(os.path.join(root, f))
            except Exception:
                pass
    return total


async def _create_mega_folder(async_api, mega_listener, name, parent_node):
    return await async_api.create_folder(name, parent_node)


async def _ensure_folder_structure(
    async_api, mega_listener, local_dir, parent_node, folder_name=None
):
    root_node = parent_node
    if folder_name:
        root_node = await _create_mega_folder(
            async_api, mega_listener, folder_name, parent_node
        )
        if not root_node:
            LOGGER.error(f"Failed to create root folder '{folder_name}' on Mega")
            return None, {}

    folder_map = {}
    walk_result = await sync_to_async(lambda: list(os.walk(local_dir)))
    for root, dirs, _ in walk_result:
        if root == local_dir:
            parent = root_node
        else:
            parent = folder_map.get(root)
            if not parent:
                continue

        for d in dirs:
            sub_path = os.path.join(root, d)
            node = await _create_mega_folder(async_api, mega_listener, d, parent)
            if node:
                folder_map[sub_path] = node

    return root_node, folder_map


async def _upload_file(
    async_api, mega_listener, file_path, parent_node, custom_name, suppress_export=False
):
    for attempt in range(3):
        cancel_token = _make_cancel_token()
        mega_listener._cancel_token = cancel_token
        mega_listener.error = None
        mega_listener.retryable_error = None
        mega_listener._bytes_transferred = 0
        mega_listener._total_downloaded_bytes = 0
        mega_listener._caller_manages_completion = True
        mega_listener._size = await aiopath.getsize(file_path)

        await async_api.startUpload(
            file_path,
            parent_node,
            custom_name,
            cancel_token,
        )
        await async_api.wait_for_transfer()

        if mega_listener.is_cancelled:
            return False, None
        if mega_listener.retryable_error and attempt < 2:
            LOGGER.warning(
                "MegaUpload: attempt %d retryable: %s",
                attempt + 1,
                mega_listener.retryable_error,
            )
            continue
        if mega_listener.error:
            msg = _mega_error_format(mega_listener.error)
            LOGGER.error(f"MegaUpload error: {msg}")
            return False, None

        link = None
        if not suppress_export:
            node_handle = getattr(mega_listener, "_uploaded_node_handle", None)
            if node_handle and async_api._export_future is not None:
                try:
                    await wait_for(wrap_future(async_api._export_future), timeout=60)
                    link = getattr(mega_listener, "_export_link", None)
                except AsyncTimeoutError:
                    LOGGER.warning("MegaUpload: export timed out after 60s")

        return True, link

    return False, None


async def add_mega_upload(listener, path, mega_email, mega_password, gid):
    if not mega_email or not mega_password:
        await listener.on_upload_error("Mega credentials not configured for this user.")
        return

    mega_base = ""
    sdk_gid = token_hex(5)
    mega_base = os.path.join(os.path.dirname(path.rstrip("/")), ".mega_sdk", sdk_gid)
    mega_dir = os.path.join(mega_base, "main")
    await makedirs(mega_dir, exist_ok=True)

    async_api = AsyncMega()
    async_api.api = api = MegaApi("", mega_dir, "Borderless", 4)
    await asleep(0.1)
    mega_listener = MegaAppListener(async_api, listener)
    mega_listener._upload_mode = True
    async_api._mega_listener = mega_listener
    api.addListener(mega_listener)
    api._listener_ref = mega_listener

    try:
        if await aiopath.isdir(path):
            listener.size = await _get_total_size(path)
        else:
            listener.size = await aiopath.getsize(path)

        async with task_dict_lock:
            task_dict[listener.mid] = MegaDownloadStatus(
                listener, mega_listener, gid, "up"
            )
        await update_status_message(listener.message.chat.id)

        await async_api.login(mega_email, mega_password)
        if mega_listener.error:
            await listener.on_upload_error(
                f"Mega login failed: {_mega_error_format(mega_listener.error)}"
            )
            return

        await async_api.fetchNodes()
        await asleep(0)
        if mega_listener.error:
            await listener.on_upload_error(
                f"Mega fetch nodes failed: {_mega_error_format(mega_listener.error)}"
            )
            return

        root_node = mega_listener.node
        if not root_node:
            await listener.on_upload_error("Failed to get Mega root node.")
            return

        total_files = 0
        uploaded_files = 0
        mime_type = "application/octet-stream"

        upload_link = None
        if await aiopath.isdir(path):
            total_files = await sync_to_async(
                lambda: sum(len(files) for _, _, files in os.walk(path))
            )
            if total_files == 0:
                await listener.on_upload_error("No files to upload in folder")
                return
            dir_name = os.path.basename(path.rstrip("/\\"))
            mega_root, folder_map = await _ensure_folder_structure(
                async_api, mega_listener, path, root_node, dir_name
            )
            if not mega_root:
                if not listener.is_cancelled and not mega_listener.is_cancelled:
                    await listener.on_upload_error(
                        "Failed to create root folder on Mega"
                    )
                return

            mega_listener._suppress_export = True

            walk_result = await sync_to_async(lambda: list(os.walk(path)))
            for root, _, files in walk_result:
                if listener.is_cancelled or mega_listener.is_cancelled:
                    return
                if root == path:
                    parent = mega_root
                else:
                    parent = folder_map.get(root)

                if parent is None:
                    continue

                for f in files:
                    if listener.is_cancelled or mega_listener.is_cancelled:
                        return
                    file_path = os.path.join(root, f)
                    ok, _ = await _upload_file(
                        async_api,
                        mega_listener,
                        file_path,
                        parent,
                        f,
                        suppress_export=True,
                    )
                    if ok:
                        uploaded_files += 1
                    else:
                        if not listener.is_cancelled and not mega_listener.is_cancelled:
                            await listener.on_upload_error(f"MegaUpload failed for {f}")
                        return

            mime_type = "Folder"
            if (
                uploaded_files > 0
                and not listener.is_cancelled
                and not mega_listener.is_cancelled
            ):
                try:
                    mega_listener._suppress_export = False
                    upload_link = await async_api.export_node(mega_root)
                except Exception:
                    LOGGER.exception("MegaUpload: folder export failed")

        else:
            total_files = 1
            file_name = os.path.basename(path)
            ok, link = await _upload_file(
                async_api, mega_listener, path, root_node, file_name
            )
            if ok:
                uploaded_files = 1
                upload_link = link
                mime_type = guess_type(file_name)[0] or "application/octet-stream"
            else:
                if not listener.is_cancelled and not mega_listener.is_cancelled:
                    await listener.on_upload_error(f"MegaUpload failed for {file_name}")
                return

        if (
            uploaded_files > 0
            and not listener.is_cancelled
            and not mega_listener.is_cancelled
        ):
            LOGGER.info(f"MegaUpload: completed, {uploaded_files}/{total_files} files")
            await listener.on_upload_complete(upload_link, uploaded_files, 0, mime_type)

    except Exception as e:
        LOGGER.error(f"Unexpected error in add_mega_upload: {e}", exc_info=True)
        if not listener.is_cancelled:
            await listener.on_upload_error(f"Internal error: {e}")
    finally:
        if async_api is not None:
            async with _MEGA_SDK_LOCK:
                with suppress(Exception):
                    await async_api.logout()
                if async_api.api is not None and async_api._mega_listener is not None:
                    with suppress(Exception):
                        async_api.api.removeListener(async_api._mega_listener)
        await clean_download(mega_base)
