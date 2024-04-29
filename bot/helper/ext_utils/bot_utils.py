import os
import re
import asyncio
import base64
import datetime
import aiofiles
import aiohttp
import mega
import pyrogram
from pyrogram.enums import ChatType
from pyrogram.types import BotCommand
from psutil import (
    disk_usage,
    disk_io_counters,
    cpu_percent,
    swap_memory,
    cpu_count,
    cpu_freq,
    getloadavg,
    virtual_memory,
    net_io_counters,
    boot_time,
)

# Initialize the bot
bot = pyrogram.Client("bot")  # Creating a Pyrogram client instance with the name 'bot'

# Define bot commands
START_COMMAND = BotCommand("start", "Start the bot")  # A command object for the /start command
HELP_COMMAND = BotCommand("help", "Show this help message")  # A command object for the /help command

@bot.on_message(pyrogram.Filters.command(START_COMMAND))
async def start_command(client, message):
    """
    This is an asynchronous function that is called when the /start command is issued.
    It responds with a simple message indicating that the bot has started.
    """
    await message.reply("Bot has started!")

@bot.on_message(pyrogram.Filters.command(HELP_COMMAND))
async def help_command(client, message):
    """
    This is an asynchronous function that is called when the /help command is issued.
    It responds with a list of available commands and their descriptions.
    """
    await message.reply("Available commands: \n/start - Start the bot \n/help - Show this help message")

# Rest of the code remains the same

