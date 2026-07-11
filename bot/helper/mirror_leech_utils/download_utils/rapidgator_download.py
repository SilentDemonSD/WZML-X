from secrets import token_hex

from bot import (
    LOGGER,
    task_dict,
    task_dict_lock,
    user_data,
)
from bot.core.config_manager import Config
from ...ext_utils.task_manager import (
    check_running_tasks,
    stop_duplicate_check,
    limit_checker,
)
from ...listeners.direct_listener import DirectListener
from ...mirror_leech_utils.status_utils.rapidgator_status import RapidgatorStatus
from ...mirror_leech_utils.status_utils.queue_status import QueueStatus
from ...telegram_helper.message_utils import send_status_message
from ...ext_utils.rapidgator_utils import get_rapidgator_link


async def add_rapidgator_download(listener, path):
    if Config.DISABLE_RAPIDGATOR:
        await listener.on_download_error(
            "Rapidgator Link downloads are currently disabled by the Bot Owner."
        )
        return

    user_dict = user_data.get(listener.user_id, {})
    rg_email = user_dict.get("RAPIDGATOR_EMAIL") or Config.RAPIDGATOR_EMAIL
    rg_password = user_dict.get("RAPIDGATOR_PASSWORD") or Config.RAPIDGATOR_PASSWORD

    if not rg_email or not rg_password:
        await listener.on_download_error(
            "Rapidgator premium credentials are not configured! Please set them in your user settings or config."
        )
        return

    # Resolve link
    try:
        url, filename, size = await get_rapidgator_link(listener.link, rg_email, rg_password)
    except Exception as e:
        await listener.on_download_error(f"Rapidgator error: {str(e)}")
        return

    listener.size = size
    if not listener.name:
        listener.name = filename
    path = f"{path}/{listener.name}"

    msg, button = await stop_duplicate_check(listener)
    if msg:
        await listener.on_download_error(msg, button)
        return

    if limit_exceeded := await limit_checker(listener):
        await listener.on_download_error(limit_exceeded, is_limit=True)
        return

    gid = token_hex(5)
    add_to_queue, event = await check_running_tasks(listener)
    if add_to_queue:
        LOGGER.info(f"Added to Queue/Download: {listener.name}")
        async with task_dict_lock:
            task_dict[listener.mid] = QueueStatus(listener, gid, "dl")
        await listener.on_download_start()
        if listener.multi <= 1 and not listener.is_rss:
            await send_status_message(listener.message)
        await event.wait()
        if listener.is_cancelled:
            return

    a2c_opt = {
        "follow-torrent": "false",
        "follow-metalink": "false",
        "header": [
            "User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Referer: https://rapidgator.net/"
        ]
    }
    
    directListener = DirectListener(path, listener, a2c_opt)

    async with task_dict_lock:
        task_dict[listener.mid] = RapidgatorStatus(listener, directListener, gid)

    if add_to_queue:
        LOGGER.info(f"Start Queued Download from Rapidgator: {listener.name}")
    else:
        LOGGER.info(f"Download from Rapidgator: {listener.name}")
        await listener.on_download_start()
        if listener.multi <= 1 and not listener.is_rss:
            await send_status_message(listener.message)

    contents = [{"url": url, "filename": filename, "path": ""}]
    await directListener.download(contents)
