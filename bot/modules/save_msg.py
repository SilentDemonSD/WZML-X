import pyrogram #req for Internal Usages
from pyrogram import filters, Client
from pyrogram.types import CallbackQuery, InlineKeyboardMarkup 
from pyrogram.errors import Unauthorized
from bot import bot, LOGGER

@bot.on_callback_query(filters.regex(r"^save"))
async def save_message(c: Client, query: CallbackQuery):
    """ Based Upon ( https://github.com/junedkh/jmdkh-mltb ) """

    if query.data == "save":
        try:
            await query.message.copy(query.from_user.id, reply_markup=InlineKeyboardMarkup(query.message.reply_markup.inline_keyboard[:1]))
            await query.answer('Message Saved Successfully, Check Bot PM', show_alert=True)
        except:
            await query.answer('Start the Bot in Private and Try Again', show_alert=True)
