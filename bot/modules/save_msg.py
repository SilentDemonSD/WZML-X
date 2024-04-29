#!/usr/bin/env python3
from typing import Any, Callable, Optional

import pyrogram
from pyrogram.types import InlineKeyboardMarkup, CallbackQuery
from pyrogram.handlers import CallbackQueryHandler
from pyrogram.filters import regex
from asyncio import sleep

from bot import bot, bot_name, user_data

def save_message(client: pyrogram.Client, query: CallbackQuery) -> None:
    """Save the current message/media to the user's chat."""
    usr = query.from_user.id
    user_dict: dict[str, Any] = user_data.get(usr, {})

    if query.data == "save":
        try:
            save_mode = user_dict.get('save_mode')
            if save_mode:
                usr = next(iter(user_dict.get('ldump', {}).values()))
            else:
                raise ValueError("Save mode not enabled.")
        except StopIteration:
            await query.answer("No chat selected to save to.", show_alert=True)
            return
        except (KeyError, ValueError) as e:
            await query.answer(url=f"https://t.me/{bot_name}?start=start")
            await sleep(1)
            await query.message.copy(usr, reply_markup=InlineKeyboardMarkup(query.message.reply_markup.inline_keyboard[:-1]) if query.message.reply_markup and query.message.reply_markup.inline_keyboard else None)
            return

        try:
            await query.message.copy(usr, reply_markup=InlineKeyboardMarkup(BTN) if (BTN := query.message.reply_markup.inline_keyboard[:-1]) else None)
            await query.answer("Message/Media Successfully Saved !", show_alert=True)
        except Exception:
            await query.answer('Make Bot as Admin and give Post Permissions and Try Again', show_alert=True)

bot.add_handler(CallbackQueryHandler(save_message, filters=regex(r"^save")))
