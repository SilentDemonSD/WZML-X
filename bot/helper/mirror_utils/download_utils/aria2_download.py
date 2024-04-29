import asyncio
import logging
from typing import (
    Any,
    Dict,
    List,
    Optional,
    Union,
)

import aiofiles.os as aio_os
import aiopath
from aiogram import Bot, types
from aiogram.methods import ForceReply
from aiogram.types import CallbackQuery
from aiogram.utils import executor
from bot import aria2, download_dict_lock, download_dict, LOGGER, config_dict, aria2_options, aria2c_global, non_queued_dl, queue_dict_lock
from bot.helper.ext_utils.bot_utils import bt_selection_buttons, sync_to_async
from bot.helper.mirror_utils.status_utils.aria2_status import Aria2Status
from bot.helper.telegram_helper.message_utils import sendStatusMessage, sendMessage
from bot.helper.ext_utils.task_manager import is_queued

class Constants:
    TORRENT_TIMEOUT: Optional[int] = config_dict.get('TORRENT_TIMEOUT')

async def add_aria2c_download(
    link: str,
    path: str,
    listener: types.User,
    filename: Optional[str] = None,
    header: Optional[Dict[str, str]] = None,
    ratio: Optional[float] = None,
    seed_time: Optional[int] = None,
) -> Union[None, Aria2Status]:
    """
    Adds a download to aria2c.

    :param link: The link to download.
    :param path: The path to download the file to.
    :param listener: The user who initiated the download.
    :param filename: The filename to use for the download.
    :param header: The headers to use for the download.
    :param ratio: The seed ratio to use for the download.
    :param seed_time: The seed time to use for the download.
    :return: The Aria2Status object for the download.
    """
    a2c_opt: Dict[str, Any] = {**aria2_options}
    [a2c_opt.pop(k) for k in aria2c_global if k in aria2_options]
    a2c_opt['dir'] = path
    if filename:
        a2c_opt['out'] = filename
    if header:
        a2c_opt['header'] = header
    if ratio:
        a2c_opt['seed-ratio'] = ratio
    if seed_time:
        a2c_opt['seed-time'] = seed_time
    if Constants.TORRENT_TIMEOUT is not None:
        a2c_opt['bt-stop-timeout'] = f'{Constants.TORRENT_TIMEOUT}'
    added_to_queue, event = await is_queued(listener.id)
    if added_to_queue:
        if link.startswith('magnet:'):
            a2c_opt['pause-metadata'] = 'true'
        else:
            a2c_opt['pause'] = 'true'
    try:
        download = await asyncio.wait_for(sync_to_async(aria2.add, link, a2c_opt), timeout=30)
    except asyncio.TimeoutError as e:
        LOGGER.debug(f"Aria2c Download Timeout: {e}")
        await sendMessage(listener.message, 'Download request timed out.')
        return
    except Exception as e:
        LOGGER.debug(f"Aria2c Download Error: {e}")
        await sendMessage(listener.message, f'{e}')
        return
    if await aiopath.is_file(link):
        await aio_os.remove(link)
    if download.error_message:
        error = str(download.error_message).replace('<', ' ').replace('>', ' ')
        LOGGER.debug(f"Aria2c Download Error: {error}")
        await sendMessage(listener.message, error)
        return

    gid = download.gid
    name = download.name
    async with download_dict_lock:
        download_dict[listener.id] = Aria2Status(
            gid, listener, queued=added_to_queue)
    if added_to_queue:
        LOGGER.debug(f"Added to Queue/Download: {name}. Gid: {gid}")
        if not listener.select or not download.is_torrent:
            await sendStatusMessage(listener.message)
    else:
        async with queue_dict_lock:
            non_queued_dl.add(listener.id)
        LOGGER.debug(f"Aria2Download started: {name}. Gid: {gid}")

    await listener.onDownloadStart()

    if not added_to_queue and (not listener.select or not config_dict['BASE_URL']):
        await sendStatusMessage(listener.message)
    elif listener.select and download.is_torrent and not download.is_metadata:
        if not added_to_queue:
            await asyncio.create_task(sync_to_async(aria2.client.force_pause, gid))
        SBUTTONS = bt_selection_buttons(gid)
        msg = "Your download paused. Choose files then press Done Selecting button to start downloading."
        await sendMessage(listener.message, msg, reply_markup=ForceReply(selective=True))

    if added_to_queue:
        await event.wait()

        async with download_dict_lock:
            if listener.id not in download_dict:
                return
            download = download_dict[listener.id]
            download.queued = False
            new_gid = download.gid()

        await asyncio.create_task(sync_to_async(aria2.client.unpause, new_gid))
        LOGGER.debug(f'Start Queued Download from Aria2c: {name}. Gid: {gid}')

        async with queue_dict_lock:
            non_queued_dl.add(listener.id)

if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    executor.start_polling(bot)
