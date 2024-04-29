#!/usr/bin/env python3
import asyncio
import os

import pyrogram
from pyrogram.errors import UserIsBlocked, MessageNotModified, ChatAdminRequired
from pyrogram.handlers import MessageHandler, CallbackQueryHandler
from pyrogram.filters import command, regex
from pyrogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton

from bot import LOGGER, bot, config_dict
from bot.helper.mirror_utils.upload_utils.gdriveTools import GoogleDriveHelper
from bot.helper.telegram_helper.message_utils import sendMessage, editMessage, delete_messages
from bot.helper.telegram_helper.filters import CustomFilters
from bot.helper.telegram_helper.bot_commands import BotCommands
from bot.helper.telegram_helper.button_build import ButtonMaker
from bot.helper.ext_utils.bot_utils import sync_to_async, new_task, get_telegraph_list, checking_access
from bot.helper.themes import BotTheme

async def list_buttons(user_id: int, is_recursive: bool = True) -> InlineKeyboardMarkup:
    buttons = ButtonMaker()
    buttons.ibutton("Only Folders", f"list_types {user_id} folders {is_recursive}")
    buttons.ibutton("Only Files", f"list_types {user_id} files {is_recursive}")
    buttons.ibutton("Both", f"list_types {user_id} both {is_recursive}")
    buttons.ibutton(f"{'✅️' if is_recursive else ''} Recursive", f"list_types {user_id} rec {not is_recursive}")
    buttons.ibutton("Cancel", f"list_types {user_id} cancel")
    return buttons.build_menu(2)

async def _list_drive(key: str, message: Message, user_id: int, item_type: str, is_recursive: bool):
    LOGGER.info(f"GDrive List: {key}")
    gdrive = GoogleDriveHelper()
    try:
        telegraph_content, contents_no = await sync_to_async(gdrive.drive_list, key, is_recursive=is_recursive, itemType=item_type, userId=user_id)
    except Exception as e:
        await bot.edit_message_text(chat_id=message.chat.id, message_id=message.id, text=str(e))
        return

    if telegraph_content:
        try:
            button = await get_telegraph_list(telegraph_content)
        except Exception as e:
            await bot.edit_message_text(chat_id=message.chat.id, message_id=message.id, text=str(e))
            return
        msg = BotTheme.get_string('LIST_FOUND', NO=contents_no, NAME=key)
        await bot.edit_message_text(chat_id=message.chat.id, message_id=message.id, text=msg, reply_markup=button)
    else:
        await bot.edit_message_text(chat_id=message.chat.id, message_id=message.id, text=BotTheme.get_string('LIST_NOT_FOUND', NAME=key))

async def select_type(query: CallbackQuery):
    user_id = query.from_user.id
    message = query.message
    key = message.reply_to_message.text.split(maxsplit=1)[1].strip()
    data = query.data.split()
    if user_id != int(data[1]):
        await bot.answer(query, text="Not Yours!", show_alert=True)
        return
    elif data[2] == 'rec':
        is_recursive = not bool(eval(data[3]))
        buttons = await list_buttons(user_id, is_recursive)
        await bot.edit_message_text(chat_id=message.chat.id, message_id=message.id, text='<b>Choose drive list options:</b>', reply_markup=buttons)
        await bot.answer(query)
        return
    elif data[2] == 'cancel':
        await bot.answer(query)
        await bot.edit_message_text(chat_id=message.chat.id, message_id=message.id, text="<b>List has been canceled!</b>")
        return
    await bot.answer(query)
    item_type = data[2]
    is_recursive = eval(data[3])
    await bot.edit_message_text(chat_id=message.chat.id, message_id=message.id, text=BotTheme.get_string('LIST_SEARCHING', NAME=key))
    await _list_drive(key, message, user_id, item_type, is_recursive)

async def drive_list(message: Message):
    args = message.text.split() if message.text else ['/cmd']
    if len(args) == 1:
        return await sendMessage(message, BotTheme.get_string('SEND_KEY'))
    user_id = message.from_user.id
    msg, btn = await checking_access(user_id)
    if msg is not None:
        await sendMessage(message, msg, btn.build_menu(1))
        return
    buttons = await list_buttons(user_id)
    await sendMessage(message, BotTheme.get_string('CHOOSE_OPTIONS'), buttons, 'IMAGES')

bot.add_handler(MessageHandler(drive_list, filters=command(BotCommands.ListCommand) & CustomFilters.authorized & ~CustomFilters.blacklisted), group=2)
bot.add_handler(CallbackQueryHandler(select_type, filters=regex("^list_types")), group=2)
