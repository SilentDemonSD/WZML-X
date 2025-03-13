from secrets import token_hex
from aiofiles.os import makedirs

from mega import MegaApi

from .... import LOGGER, task_dict, task_dict_lock, non_queued_dl, queue_dict_lock
from ....core.config_manager import Config
from ...ext_utils.links_utils import get_mega_link_type
from ...ext_utils.bot_utils import sync_to_async

from ...ext_utils.task_manager import (
    check_running_tasks,
    stop_duplicate_check,
    limit_checker,
)
from ...mirror_leech_utils.status_utils.mega_dl_status import MegaDownloadStatus
from ...mirror_leech_utils.status_utils.queue_status import QueueStatus
from ...telegram_helper.message_utils import (
    auto_delete_message,
    delete_links,
    send_message,
    send_status_message,
)
from ...listeners.mega_listener import (
    MegaAppListener,
    AsyncMega,
)


async def add_mega_download(listener, path):
    async_api = AsyncMega()
    async_api.api = api = MegaApi(None, None, None, "WZML-X")
    folder_api = None

    mega_listener = MegaAppListener(async_api.continue_event, listener)
    api.addListener(mega_listener)

    if (MEGA_EMAIL := Config.MEGA_EMAIL) and (MEGA_PASSWORD := Config.MEGA_PASSWORD):
        await async_api.login(MEGA_EMAIL, MEGA_PASSWORD)

    if get_mega_link_type(listener.link) == "file":
        await async_api.getPublicNode(listener.link)
        node = mega_listener.public_node
    else:
        async_api.folder_api = folder_api = MegaApi(None, None, None, "WZML-X")
        folder_api.addListener(mega_listener)

        await async_api.run(folder_api.loginToFolder, listener.link)
        node = await sync_to_async(folder_api.authorizeNode, mega_listener.node)

    if mega_listener.error:
        mmsg = await send_message(listener.message, str(mega_listener.error))
        await async_api.logout()
        await delete_links(listener.message)
        await auto_delete_message(listener.message, mmsg)
        return

    listener.name = (
        listener.name or node.getName()
    )
    (msg, button) = await stop_duplicate_check(listener)
    if msg:
        mmsg = await send_message(listener.message, msg, button)
        await async_api.logout()
        await delete_links(listener.message)
        await auto_delete_message(listener.message, mmsg)
        return

    listener.size = await sync_to_async(api.getSize, node)
    if limit_exceeded := await limit_checker(listener):
        mmsg = await send_message(listener.message, limit_exceeded)
        await async_api.logout()
        await delete_links(listener.message)
        await auto_delete_message(listener.message, mmsg)
        return

    gid = token_hex(5)
    listener.size = await sync_to_async(api.getSize, node)
    (added_to_queue, event) = await check_running_tasks(listener)
    if added_to_queue:
        LOGGER.info(f"Added to Queue/Download: {listener.name}")
        async with task_dict_lock:
            task_dict[listener.mid] = QueueStatus(listener, gid, "Dl")
        await listener.on_download_start()
        await send_status_message(listener.message)
        await event.wait()
        async with task_dict_lock:
            if listener.mid not in task_dict:
                await async_api.logout()
                return
        from_queue = True
        LOGGER.info(f"Start Queued Download from Mega: {listener.name}")
    else:
        from_queue = False

    async with task_dict_lock:
        task_dict[listener.mid] = MegaDownloadStatus(listener, mega_listener, gid, "dl")
    async with queue_dict_lock:
        non_queued_dl.add(listener.mid)

    if from_queue:
        LOGGER.info(f"Start Queued Download from Mega: {listener.name}")
    else:
        await listener.on_download_start()
        await send_status_message(listener.message)
        LOGGER.info(f"Download from Mega: {listener.name}")

    await makedirs(path, exist_ok=True)
    await async_api.startDownload(node, path, listener.name, None, False, None, 3, 2, False)
    await async_api.logout()
