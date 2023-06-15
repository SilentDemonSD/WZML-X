#!/usr/bin/env python3
from bot import bot
from pyrogram.types import InlineKeyboardMarkup 
from pyrogram.handlers import CallbackQueryHandler
from pyrogram.filters import regex

async def save_message(_, query):
    if query.data == "save":
        try:
            await query.message.copy(query.from_user.id, reply_markup=InlineKeyboardMarkup(BTN) if (BTN := query.message.reply_markup.inline_keyboard[:-1]) else None)
            await query.answer('Message Saved Successfully, Check Bot PM', show_alert=True)        
        except:
            await query.answer('Start the Bot in Private and Try Again', show_alert=True)

bot.add_handler(CallbackQueryHandler(save_message, filters=regex(r"^save")))
