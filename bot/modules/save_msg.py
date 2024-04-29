#!/usr/bin/env python3
from pyrogram.types import InlineKeyboardMarkup, CallbackQuery
from pyrogram.handlers import CallbackQueryHandler
from pyrogram.filters import regex
from asyncio import sleep
from typing import Optional

from bot import bot, bot_name, user_data

async def save_message(query: CallbackQuery) -> None:
    """Save the current message/media to the user's chat."""
    
    user_id = query.from_user.id
    user_dict = user_data.get(user_id, {})
    
    if query.data == "save":
        try:
            save_mode = user_dict.get('save_mode')
            if save_mode:
                user_to_save_to = next(iter(user_dict.get('ldump', {}).values()))
            else:
                raise ValueError("Save mode not enabled.")
        except (StopIteration, KeyError) as e:
            await query.answer("An error occurred while saving the message.", show_alert=True)
            return
        
        try:
            reply_markup = query.message.reply_markup
            keyboard = InlineKeyboardMarkup(inline_keyboard := reply_markup.inline_keyboard[:-1]) if reply_markup else None
            await query.message.copy(user_to_save_to, reply_markup=keyboard)
            await query.answer("Message/Media successfully saved!", show_alert=True)
        except Exception as e:
            if save_mode:
                await query.answer("Make the bot an admin and give it post permissions.", show_alert=True)
            else:
                url = f"https://t.me/{bot_name}?start=start"
                await query.answer(url, show_alert=True)
                await sleep(1)
                await query.message.copy(user_to_save_to, reply_markup=keyboard)
