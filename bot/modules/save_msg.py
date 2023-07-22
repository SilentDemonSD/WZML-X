#!/usr/bin/env python3
from bot import bot, bot_name, user_data
from bot.helper.telegram_helper.message_utils import chat_info
from pyrogram.types import InlineKeyboardMarkup 
from pyrogram.handlers import CallbackQueryHandler
from pyrogram.filters import regex

async def save_message(_, query):
    usr = query.from_user
    user_dict = user_data.get(usr.id, {})
    if query.data == "save":
        try:
            if user_dict.get('save_mode'):
                usr = await chat_info((user_dict.get('ldump', '')).split()[0])
            await query.message.copy(usr.id, reply_markup=InlineKeyboardMarkup(BTN) if (BTN := query.message.reply_markup.inline_keyboard[:-1]) else None)
            await query.answer("Message/Media Successfully Saved !", show_alert=True)
        except:
            await query.answer('Make Bot as Admin and give Post Permissions and Try Again' if user_dict.get('save_mode') else 'Start the Bot in Private and Try Again', show_alert=True)

bot.add_handler(CallbackQueryHandler(save_message, filters=regex(r"^save")))
