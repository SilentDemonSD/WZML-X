#!/usr/bin/env python3
import asyncio
from typing import List, Tuple

import pyrogram.filters as Filters
from pyrogram.handlers import MessageHandler, CallbackQueryHandler
from pyrogram.types import Message, CallbackQuery

from bot import download_dict, bot, bot_name, download_dict_lock, OWNER_ID, user_data
from bot.helper.telegram_helper.bot_commands import BotCommands
from bot.helper.telegram_helper.filters import CustomFilters
from bot.helper.telegram_helper.message_utils import sendMessage, deleteMessage, auto_delete_message
from bot.helper.ext_utils.bot_utils import get_download_by_gid, get_all_downloads, MirrorStatus, new_task
from bot.helper.telegram_helper import button_build


async def cancel_mirror(client, message):
    user_id = message.from_user.id
    args = message.text.split('_', maxsplit=1)
    if len(args) > 1:
        gid, cmd_name = args[1].split('@', maxsplit=1)
    else:
        return await send_message(message, "Invalid format. Use /cancel_mirror_gid_botname or reply to an active task.")

    if cmd_name != bot_name:
        return

    download_info = await get_download_by_gid(gid)
    if not download_info:
        return await send_message(message, f"GID: `{gid}` Not Found.")

    if (user_id not in user_data or not user_data[user_id].get('is_sudo')) and download_info.message.from_user.id != user_id:
        return await send_message(message, "This task is not for you!")

    download_info.download().cancel_download()


async def cancel_all(status: MirrorStatus) -> bool:
    matches = await get_all_downloads(status)
    if not matches:
        return False

    for download_info in matches:
        download_info.download().cancel_download()
        await asyncio.sleep(1)

    return True


async def cancel_all_buttons(client, message: Message):
    async with download_dict_lock:
        count = len(download_dict)
    if count == 0:
        return await send_message(message, "No active tasks!")

    buttons = button_build.ButtonMaker()
    buttons.ibutton("Downloading", f"canall {MirrorStatus.STATUS_DOWNLOADING}")
    buttons.ibutton("Uploading", f"canall {MirrorStatus.STATUS_UPLOADING}")
    buttons.ibutton("Seeding", f"canall {MirrorStatus.STATUS_SEEDING}")
    buttons.ibutton("Cloning", f"canall {MirrorStatus.STATUS_CLONING}")
    buttons.ibutton("Extracting", f"canall {MirrorStatus.STATUS_EXTRACTING}")
    buttons.ibutton("Archiving", f"canall {MirrorStatus.STATUS_ARCHIVING}")
    buttons.ibutton("QueuedDl", f"canall {MirrorStatus.STATUS_QUEUEDL}")
    buttons.ibutton("QueuedUp", f"canall {MirrorStatus.STATUS_QUEUEUP}")
    buttons.ibutton("Paused", f"canall {MirrorStatus.STATUS_PAUSED}")
    buttons.ibutton("All", "canall all")
    buttons.ibutton("Close", "canall close")
    button = buttons.build_menu(2)
    can_msg = await send_message(message, 'Choose tasks to cancel.', button)
    await auto_delete_message(message, can_msg)


@new_task
async def cancel_all_update(client, query: CallbackQuery):
    data = query.data.split()
    message = query.message
    reply_to = message.reply_to_message
    await query.answer()

    if data[1] == 'close':
        await delete_message(reply_to)
        await delete_message(message)
    else:
        res = await cancel_all(MirrorStatus(data[1]))
        if not res:
            await send_message(reply_to, f"No matching tasks for {data[1]}!")


bot.add_handler(MessageHandler(cancel_mirror, filters=Filters.regex(
    f"^/{BotCommands.CancelMirror}(_\w+)?(?!all)") & CustomFilters.authorized & ~CustomFilters.blacklisted))
bot.add_handler(MessageHandler(cancel_all_buttons, filters=Filters.command(
    BotCommands.CancelAllCommand) & CustomFilters.sudo))
bot.add_handler(CallbackQueryHandler(cancel_all_update, filters=Filters.regex(r"^canall")))
