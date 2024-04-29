#!/usr/bin/env python3

import asyncio
from pyrogram.types import InlineKeyboardMarkup 
from pyrogram.handlers import CallbackQueryHandler
from pyrogram.filters import regex

# Import bot and bot_name from bot.py
from bot import bot, bot_name, user_data

# Define the asynchronous function save_message
async def save_message(_, query):
    # Get the user ID from the query
    usr = query.from_user.id
    
    # Get the user data dictionary
    user_dict = user_data.get(usr, {})
    
    # Check if the query data is 'save'
    if query.data == "save":
        # Check if the user has 'save\_mode' enabled
        if user_dict.get('save_mode'):
            # If 'save\_mode' is enabled, get the user ID to save the message to
            usr = next(iter(user_dict.get('ldump', {}).values()))
        
        # Try to copy the message to the specified user's chat
        try:
            # Copy the message with its reply markup (if it exists)
            await query.message.copy(usr, reply_markup=InlineKeyboardMarkup(BTN) if (BTN := query.message.reply_markup.inline_keyboard[:-1]) else None)
            
            # Send a success message to the user
            await query.answer("Message/Media Successfully Saved !", show_alert=True)
            
        # Catch any exceptions that occur during the copy operation
        except Exception:
            # If 'save\_mode' is enabled, send an error message to the user
            if user_dict.get('save_mode'):
                await query.answer('Make Bot as Admin and give Post Permissions and Try Again', show_alert=True)
            # If 'save\_mode' is not enabled, redirect the user to the bot's start message
            else:
                await query.answer(url=f"https://t.me/{bot_name}?start=start")
                # Wait for 1 second before copying the message to the user's chat
                await asyncio.sleep(1)
                # Copy the message with its reply markup (if it exists)
                await query.message.copy(usr, reply_markup=InlineKeyboardMarkup(BTN) if (BTN := query.message.reply_markup.inline_keyboard[:-1]) else None)

# Add the save_message function as a CallbackQueryHandler
bot.add_handler(CallbackQueryHandler(save_message, filters=regex(r"^save")))

