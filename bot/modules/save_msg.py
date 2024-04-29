#!/usr/bin/env python3

import asyncio
from typing import Dict, Any, Optional
from pyrogram.types import InlineKeyboardMarkup, CallbackQuery
from pyrogram.handlers import CallbackQueryHandler
from pyrogram.filters import regex

# Import bot and bot_name from bot.py
from bot import bot, bot_name, user_data

# Define the asynchronous function save_message
async def save_message(_, query: CallbackQuery) -> None:
    # Get the user ID from the query
    user_id = query.from_user.id
    
    # Get the user data dictionary
    user_dict: Optional[Dict[str, Any]] = user_data.get(user_id, None)
    
    # Check if the user data dictionary exists
    if user_dict is None:
        # If the user data dictionary doesn't exist, send an error message to the user
        await query.answer('User not found in the database. Please start the bot again.', show_alert=True)
        return
    
    # Check if the query data is 'save'
    if query.data == "save":
        # Check if the user has 'save_mode' enabled
        if user_dict.get('save_mode'):
            # If 'save_mode' is enabled, get the user ID to save the message to
            try:
                usr = next(iter(user_dict.get('ldump', {}).values()))
            except StopIteration:
                # If the user doesn't have any chats to save messages to, send an error message to the user
                await query.answer('No chats found to save messages to.', show_alert=True)
                return
        
        # Try to copy the message to the specified user's chat
        try:
            # Get the reply markup (if it exists)
            reply_markup = query.message.reply_markup
            BTN = reply_markup.inline_keyboard[:-1] if reply_markup else None
            # Copy the message with its reply markup (if it exists)
            await query.message.copy(usr, reply_markup=InlineKeyboardMarkup(BTN) if BTN else None)
            
            # Send a success message to the user
            await query.answer("Message/Media Successfully Saved !", show_alert=True)
            
        # Catch any exceptions that occur during the copy operation
        except Exception as e:
            # Check if 'save_mode' is enabled
            if user_dict.get('save_mode'):
                # If 'save_mode' is enabled, check if the exception is related to insufficient permissions
                if 'POST' in str(e):
                    # If the exception is related to insufficient permissions, send an error message to the user
                    await query.answer('Make Bot as Admin and give Post Permissions and Try Again', show_alert=True)
                else:
                    # If the exception is not related to insufficient permissions, send a generic error message to the user
                    await query.answer('An error occurred while saving the message. Please try again later.', show_alert=True)
            # Check if 'save_mode' is not enabled
            else:
                # If 'save_mode' is not enabled, redirect the user to the bot's start message
                await query.answer(url=f"https://t.me/{bot_name}?start=start")
                # Wait for 1 second before copying the message to the user's chat
                await asyncio.sleep(1)
                # Try to copy the message to the user's chat again
                try:
                    # Get the reply markup (if it exists)
                    reply_markup = query.message.reply_markup
                    BTN = reply_markup.inline_keyboard[:-1] if reply_markup else None
                    # Copy the message with its reply markup (if it exists)
                    await query.message.copy(usr, reply_markup=InlineKeyboardMarkup(BTN) if BTN else None)
                except Exception as e:
                    # If an exception occurs during the second copy attempt, send a generic error message to the user
                    await query.answer('An error occurred while saving the message. Please try again later.', show_alert=True)

# Add the save_message function as a CallbackQueryHandler
bot.add_handler(CallbackQueryHandler(save_message, filters=regex(r"^save")))

