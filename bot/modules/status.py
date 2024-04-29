import asyncio
import os
import psutil
import time
from typing import Coroutine, Dict, Any

import aiohttp
import aiogram
from aiogram import types, Dispatcher, executor
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.types import ParseMode
from aiogram.utils.exceptions import ThrottlingException
from aiogram.utils.markdown import hbold, hcode
from aiogram.utils.executor import StartMode

from bot.helper.telegram_helper.filters import CustomFilters
from bot.helper.telegram_helper.bot_commands import BotCommands
from bot.helper.telegram_helper.message_utils import sendMessage, editMessage, deleteMessage, auto_delete_message, sendStatusMessage, user_info, update_all_messages, delete_all_messages
from bot.helper.ext_utils.bot_utils import get_readable_file_size, get_readable_time, turn_page, setInterval, new_task
from bot.helper.themes import BotTheme

class StatusPages(StatesGroup):
    REFRESH = State()
    NEXT = State()
    PREV = State()
    CLOSE = State()

async def mirror_status(message: types.Message) -> Coroutine[Any, Any, None]:
    try:
        async with download_dict_lock:
            count = len(download_dict)
        if count == 0:
            current_time = get_readable_time(time() - bot_start_time)
            free = get_readable_file_size(psutil.disk_usage(config_dict["DOWNLOAD_DIR"]).free)
            msg = BotTheme("NO_ACTIVE_DL", cpu=psutil.cpu_percent(), free=free, free_p=round(100 - psutil.disk_usage(config_dict["DOWNLOAD_DIR"]).percent, 1),
                           ram=psutil.virtual_memory().percent, uptime=current_time)
            reply_message = await sendMessage(message, msg)
            await auto_delete_message(message, reply_message)
        else:
            await sendStatusMessage(message)
            await deleteMessage(message)
            async with status_reply_dict_lock:
                if Interval:
                    Interval[0].cancel()
                    Interval.clear()
                    Interval.append(setInterval(config_dict["STATUS_UPDATE_INTERVAL"], update_all_messages))
    except Exception as e:
        print(e)

async def status_pages(query: types.CallbackQuery) -> Coroutine[Any, Any, None]:
    user_id = query.from_user.id
    data = query.data.split()
    if data[1] == "ref":
        bot_cache.setdefault("status_refresh", {})
        if user_id in (refresh_status := bot_cache["status_refresh"]) and (curr := (time() - refresh_status[user_id])) < 7:
            return await query.answer(f"Already Refreshed! Try after {get_readable_time(7 - curr)}", show_alert=True)
        else:
            refresh_status[user_id] = time()
        await editMessage(query.message, f"{hbold(await user_info(user_id))}, <i>Refreshing Status...</i>")
        await asyncio.sleep(1.5)
        await update_all_messages(True)
    elif data[1] in ["nex", "pre"]:
        await turn_page(data)
        await update_all_messages(True)
    elif data[1] == "close":
        await delete_all_messages()
    await query.answer()

def register_handlers(dp: Dispatcher):
    dp.register_message_handler(mirror_status, commands=BotCommands.StatusCommand, state="*", filters=CustomFilters.authorized & ~CustomFilters.blacklisted)
    dp.register_callback_query_handler(status_pages, pattern="status")

if __name__ == "__main__":
    executor.start_polling(dispatcher, on_startup=register_handlers, on_shutdown=stop_and_restart, skip_updates=True)
