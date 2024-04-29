#!/usr/bin/env python3
from typing import List, Union

import asyncio
from pyrogram.handlers import MessageHandler, CallbackQueryHandler
from pyrogram.filters import command, regex
from pyrogram.errors import FloodWait

from bot import LOGGER, bot, config_dict
from bot.helper.mirror_utils.upload_utils.gdriveTools import GoogleDriveHelper
from bot.helper.telegram_helper.message_utils import sendMessage, editMessage, delete_links
from bot.helper.telegram_helper.filters import CustomFilters
from bot.helper.telegram_helper.bot_commands import BotCommands
from bot.helper.telegram_helper.button_build import ButtonMaker
from bot.helper.ext_utils.bot_utils import sync_to_async, new_task, get_telegraph_list, checking_access
from bot.helper.themes import BotTheme

async def list_buttons(user_id: int, is_recursive: bool = True) -> List[List[str]]:
    buttons = ButtonMaker()
    buttons.ibutton("Only Folders", f"list_types {user_id} folders {is_recursive}")
    buttons.ibutton("Only Files", f"list_types {user_id} files {is_recursive}")
    buttons.ibutton("Both", f"list_types {user_id} both {is_recursive}")
    buttons.ibutton(f"{'✅️' if is_recursive else ''} Recursive", f"list_types {user_id} rec {is_recursive}")
    buttons.ibutton("Cancel", f"list_types {user_id} cancel")
    return buttons.build_menu(2)

async def _list_drive(key: str, message, user_id: int, item_type: str, is_recursive: bool):
    LOGGER.info(f"GDrive List: {key}")
    gdrive = GoogleDriveHelper()
    try:
        async with gdrive:
            telegraph_content, contents_no = await sync_to_async(gdrive.drive_list, key, is_recursive=is_recursive, itemType=item_type, userId=user_id)
    except Exception as e:
        LOGGER.error(e)
        await editMessage(message, "An error occurred while listing the drive.")
        return

    if telegraph_content:
        try:
            button = await get_telegraph_list(telegraph_content)
        except Exception as e:
            await editMessage(message, str(e))
            return
        msg = BotTheme('LIST_FOUND', NO=contents_no, NAME=key)
        await editMessage(message, msg, button)
    else:
        await editMessage(message, BotTheme('LIST_NOT_FOUND', NAME=key))

async def select_type(_, query):
    user_id = query.from_user.id
    message = query.message
    key = message.reply_to_message.text.split(maxsplit=1)[1].strip()
    data = query.data.split()
    if user_id != int(data[1]):
        await query.answer(text="Not Yours!", show_alert=True)
        return
    elif data[2] == 'rec':
        is_recursive = not bool(eval(data[3]))
        buttons = await list_buttons(user_id, is_recursive)
        await query.answer()
        return await editMessage(message, '<b>Choose drive list options:</b>', buttons)
    elif data[2] == 'cancel':
        await query.answer()
        return await editMessage(message, "<b>List has been canceled!</b>")
    await query.answer()
    item_type = data[2]
    is_recursive = eval(data[3])
    await editMessage(message, BotTheme('LIST_SEARCHING', NAME=key))
    await _list_drive(key, message, user_id, item_type, is_recursive)

async def drive_list(_, message):
    args = message.text.split() if message.text else ['/cmd']
    if len(args) == 1:
        return await sendMessage(message, '<i>Send a search key along with command</i>')
    user_id = message.from_user.id
    msg, btn = await checking_access(user_id)
    if msg is not None:
        await sendMessage(message, msg, btn.build_menu(1))
        return
    buttons = await list_buttons(user_id)
    await sendMessage(message, '<b>Choose drive list options:</b>', buttons, 'IMAGES')

bot.add_handler(MessageHandler(drive_list, filters=command(
    BotCommands.ListCommand) & CustomFilters.authorized & ~CustomFilters.blacklisted))
bot.add_handler(CallbackQueryHandler(select_type, filters=regex("^list_types")))
