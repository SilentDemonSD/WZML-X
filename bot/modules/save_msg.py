#!/usr/bin/env python3
from bot import bot, bot_name, user_data
from pyrogram.types import InlineKeyboardMarkup 
from pyrogram.handlers import CallbackQueryHandler
from pyrogram.filters import regex

async def save_message(_, query):
    uid = query.from_user.id
    user_dict = user_data.get(uid, {})
    if query.data == "save":
        try:
            chat_id = uid
            if user_dict.get('save_mode'):
                chat_id = (user_dict.get('ldump', '')).split()[0]
            await query.message.copy(chat_id, reply_markup=InlineKeyboardMarkup(BTN) if (BTN := query.message.reply_markup.inline_keyboard[:-1]) else None)
            await query.answer(url=f"https://t.me/{bot_name}?start=wzmlx")
        except:
            await query.answer('Start the Bot in Private and Try Again', show_alert=True)

bot.add_handler(CallbackQueryHandler(save_message, filters=regex(r"^save")))
