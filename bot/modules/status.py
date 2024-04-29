#!/usr/bin/env python3

import os  # for access to os-level functionality, such as disk usage
import asyncio  # for asynchronous tasks and time management
import psutil  # for access to system-level information, such as CPU and memory usage
from pyrogram.handlers import MessageHandler, CallbackQueryHandler  # for handling messages and callback queries in Pyrogram
from pyrogram.filters import command, regex  # for filtering messages and callback queries
from bot import bot_cache, status_reply_dict_lock, download_dict, download_dict_lock, botStartTime, Interval, config_dict, bot  # for access to various bot-related variables and functions
from bot.helper.telegram_helper.filters import CustomFilters  # for custom message filters
from bot.helper.telegram_helper.bot_commands import BotCommands  # for bot command definitions
from bot.helper.telegram_helper.message_utils import sendMessage, editMessage, deleteMessage, auto_delete_message, sendStatusMessage, user_info, update_all_messages, delete_all_messages  # for various message-related functions
from bot.helper.ext_utils.bot_utils import get_readable_file_size, get_readable_time, turn_page, setInterval, new_task  # for various utility functions
from bot.helper.themes import BotTheme  # for generating bot messages with custom themes

# A coroutine that sends an updated status message when called
@new_task
async def mirror_status(_, message):
    async with download_dict_lock:
        count = len(download_dict)  # Get the number of active downloads

    if count == 0:  # If there are no active downloads
        currentTime = get_readable_time(time() - botStartTime)  # Calculate the bot's uptime
        free = get_readable_file_size(disk_usage(config_dict['DOWNLOAD_DIR']).free)  # Get the amount of free disk space
        msg = BotTheme('NO_ACTIVE_DL', cpu=cpu_percent(), free=free, free_p=round(100-disk_usage(config_dict['DOWNLOAD_DIR']).percent, 1),  # Create a message with the bot's status
                       ram=virtual_memory().percent, uptime=currentTime)
        reply_message = await sendMessage(message, msg)  # Send the message
        await auto_delete_message(message, reply_message)  # Delete the original message after a short delay
    else:
        await sendStatusMessage(message)  # Send the status message
        await deleteMessage(message)  # Delete the original message
        async with status_reply_dict_lock:
            if Interval:
                Interval[0].cancel()  # Cancel any existing status update intervals
                Interval.clear()  # Clear the list of intervals
                Interval.append(setInterval(config_dict['STATUS_UPDATE_INTERVAL'], update_all_messages))  # Set up a new status update interval

# A coroutine that handles callback queries related to the bot's status page
@new_task
async def status_pages(_, query):
    user_id = query.from_user.id  # Get the user's ID
    data = query.data.split()  # Split the callback query data into a list of strings

    if data[1] == 'ref':  # If the user requested to refresh the status page
        bot_cache.setdefault('status_refresh', {})  # Create a dictionary for tracking status refresh times
        if user_id in (refresh_status := bot_cache['status_refresh']) and (curr := (time() - refresh_status[user_id])) < 7:
            return await query.answer(f'Already Refreshed! Try after {get_readable_time(7 - curr)}', show_alert=True)  # If the user has recently refreshed the status page, show a message and return
        else:
            refresh_status[user_id] = time()  # Update the user's status refresh time
        await editMessage(query.message, f"{(await user_info(user_id)).mention(style='html')}, <i>Refreshing Status...</i>")  # Edit the message to show that the status is being refreshed
        await sleep(1.5)  # Wait for 1.5 seconds
        await update_all_messages(True)  # Update all status messages
    elif data[1] in ['nex', 'pre']:  # If the user requested to go to the next or previous page
        await turn_page(data)  # Handle the page turn request
        await update_all_messages(True)  # Update all status messages
    elif data[1] == 'close':  # If the user requested to close the status page
        await delete_all_messages()  # Delete all status messages
    await query.answer()  # Answer the callback query

# Add handlers for the mirror_status and status_pages coroutines
bot.add_handler(MessageHandler(mirror_status, filters=command(
    BotCommands.StatusCommand) & CustomFilters.authorized & ~CustomFilters.blacklisted))
bot.add_handler(CallbackQueryHandler(status_pages, filters=regex("^status")))
