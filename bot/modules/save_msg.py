#!/usr/bin/env python3
from pyrogram.types import InlineKeyboardMarkup 
from pyrogram.handlers import CallbackQueryHandler
from pyrogram.filters import regex
from asyncio import sleep

from bot import bot, bot_name, user_data

async def save_message(_, query):
    usr = query.from_user.id
    user_dict = user_data.get(usr, {})
    if query.data == "save":
        if user_dict.get('save_mode'):
            usr = next(iter(user_dict.get('ldump', {}).values()))
        try:
            await query.message.copy(usr, reply_markup=InlineKeyboardMarkup(BTN) if (BTN := query.message.reply_markup.inline_keyboard[:-1]) else None)
            await query.answer("Message/Media Successfully Saved !", show_alert=True)
        except Exception:
            if user_dict.get('save_mode'):
                await query.answer('Make Bot as Admin and give Post Permissions and Try Again', show_alert=True)
            else:
                await query.answer(url=f"https://t.me/{bot_name}?start=start")
                await sleep(1)
                await query.message.copy(usr, reply_markup=InlineKeyboardMarkup(BTN) if (BTN := query.message.reply_markup.inline_keyboard[:-1]) else None)

bot.add_handler(CallbackQueryHandler(save_message, filters=regex(r"^save")))
