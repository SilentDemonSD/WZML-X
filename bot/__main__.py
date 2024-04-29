import os
import sys
import time
import uuid
from datetime import datetime
from pytz import timezone
from signal import signal, SIGINT
from typing import Any, Callable, Coroutine, Final, List, Optional, Tuple
from urllib.parse import unquote

import aiofiles
import pyrogram
from pyrogram import Client, filters
from pyrogram.enums import ChatMemberStatus, ChatType
from pyrogram.errors import NetworkError
from pyrogram.handlers import MessageHandler, CallbackQueryHandler
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message

import asyncio
import aiogram
from aiogram import Bot, types
from aiogram.dispatcher import Dispatcher
from aiogram.dispatcher.handler import CancelHandler
from aiogram.dispatcher.middlewares import BaseMiddleware
from aiogram.types import ContextType
from aiogram.utils.executor import Executor

import logging
import re
import requests
from bs4 import BeautifulSoup

# Initialize bot and dispatcher
bot = Bot(token=os.environ.get("BOT_TOKEN"))
dp = Dispatcher(bot)

# Initialize logger
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
    datefmt="%Y-%m-%d %H:%M:%S"
)
LOGGER = logging.getLogger(__name__)

class StatsMiddleware(BaseMiddleware):
    def __init__(self, db: Any):
        self.db = db

    async def on_process_message(self, message: Message, data: dict) -> None:
        if message.chat.type == ChatType.PRIVATE:
            user_id = message.from_user.id
            user_data = await self.db.get_user_data(user_id)
            data["user_data"] = user_data

# Initialize database
try:
    import database_module # replace with the actual database initialization module
except Exception as e:
    LOGGER.error(f"Failed to initialize database: {e}")
    sys.exit(1)

db = database_module.Database() # replace with the actual database instance

# Initialize bot theme
try:
    from theme_module import Theme # replace with the actual bot theme initialization module
except Exception as e:
    LOGGER.error(f"Failed to initialize bot theme: {e}")
    sys.exit(1)

theme = Theme()

# Initialize bot commands
try:
    from command_module import Commands # replace with the actual bot commands initialization module
except Exception as e:
    LOGGER.error(f"Failed to initialize bot commands: {e}")
    sys.exit(1)

bot_commands = Commands()

# Initialize button builder
try:
    from button_builder_module import ButtonBuilder # replace with the actual button builder initialization module
except Exception as e:
    LOGGER.error(f"Failed to initialize button builder: {e}")
    sys.exit(1)

button_builder = ButtonBuilder()

# Initialize message utils
try:
    from message_utils_module import MessageUtils # replace with the actual message utils initialization module
except Exception as e:
    LOGGER.error(f"Failed to initialize message utils: {e}")
    sys.exit(1)

message_utils = MessageUtils()

# Initialize telegram helper
try:
    from telegram_helper_module import TelegramHelper # replace with the actual telegram helper initialization module
except Exception as e:
    LOGGER.error(f"Failed to initialize telegram helper: {e}")
    sys.exit(1)

telegram_helper = TelegramHelper()

# Initialize external utils
try:
    from external_utils_module import ExternalUtils # replace with the actual external utils initialization module
except Exception as e:
    LOGGER.error(f"Failed to initialize external utils: {e}")
    sys.exit(1)

ext_utils = ExternalUtils()

# Initialize aria2 listener
try:
    from aria2_listener_module import Aria2Listener # replace with the actual aria2 listener initialization module
except Exception as e:
    LOGGER.error(f"Failed to initialize aria2 listener: {e}")
    sys.exit(1)

aria2_listener = Aria2Listener()

# Initialize config dictionary
config_dict: dict = {
    'TOKEN_TIMEOUT': False,
    'LOGIN_PASS': None,
    'BOT_PM': True,
    'IMG_SEARCH': ['anime', 'nature', 'space', 'car', 'girl', 'guy', 'dog', 'cat', 'wolf', 'lion'],
    'IMG_PAGE': 5,
    'TIMEZONE': 'Asia/Kolkata',
    'USER_BOT_TOKEN': None,
    'USER_BOT_NAME': None,
    'LEECH_LOG_ID': None,
    'STATUS_LIMIT': 5,
}

# Initialize user data dictionary
try:
    user_data = {
        user_id: {
            'token': token,
            'time': int(time.time())
        } for user_id, token in db.get_all_user_data().items()
    }
except Exception as e:
    LOGGER.error(f"Failed to initialize user data: {e}")
    sys.exit(1)

# Initialize bot start time
bot_start_time = time.time()

class Bot:
    def __init__(self, config_dict: dict, user_data: dict, bot_start_time: float, logger: logging.Logger):
        self.config_dict = config_dict
        self.user_data = user_data
        self.bot_start_time = bot_start_time
        self.logger = logger

    async def start(self):
        self.client = Client(self.config_dict['TOKEN'])

        dp.middleware.setup(StatsMiddleware(db))

        @dp.message_handler(filters=filters.command(bot_commands.StartCommand) & filters.private)
        async def start_handler(message: Message):
            """Handle /start command in private chats"""
            await message_utils.send_message(message, theme.get_start_message(bot_commands.HelpCommand))

        @dp.callback_query_handler(lambda c: c.data and c.data.startswith("pass"))
        async def token_callback_handler(callback_query: types.CallbackQuery):
            """Handle callback queries starting with 'pass'"""
            user_id = callback_query.from_user.id
            input_token = callback_query.data.split()[1]
            data = user_data.get(user_id, {})
            if 'token' not in data or data['token'] != input_token:
                return await callback_query.answer(theme.get_token_used(), show_alert=True)
            await db.update_user_data(user_id, {'token': str(uuid.uuid4()), 'time': int(time.time())})
            await callback_query.answer(theme.get_token_activated(), show_alert=True)
            kb = callback_query.message.reply_markup.inline_keyboard[1:]
            kb.insert(0, [InlineKeyboardButton(theme.get_activated(), callback_data='pass activated')])
            await callback_query.message.edit_reply_markup(InlineKeyboardMarkup(kb))

        @dp.message_handler(filters=filters.command(bot_commands.LoginCommand) & filters.private)
        async def login_handler(message: Message):
            """Handle /login command in private chats"""
            if config_dict['LOGIN_PASS'] is None:
                return
            elif len(message.command) > 1:
                user_id = message.from_user.id
                input_pass = message.command[1]
                if user_data.get(user_id, {}).get('token', '') == config_dict['LOGIN_PASS']:
                    return await message_utils.send_message(message, theme.get_logged_in())
                if input_pass != config_dict['LOGIN_PASS']:
                    return await message_utils.send_message(message, theme.get_invalid_pass())
                await db.update_user_data(user_id, {'token': config_dict['LOGIN_PASS']})
                return await message_utils.send_message(message, theme.get_pass_logged())
            else:
                await message_utils.send_message(message, theme.get_login_used())

        @dp.message_handler(filters=filters.command(bot_commands.RestartCommand) & filters.sudo)
        async def restart_handler(message: Message):
            """Handle /restart command by sudo users"""
            await message_utils.send_message(message, theme.get_restarting())
            if dp.running_jobs:
                dp.stop_polling()
            for interval in [QbInterval, Interval]:
                if interval:
                    interval[0].cancel()
            await asyncio.gather(
                asyncio.create_subprocess_exec('pkill', '-9', '-f', 'gunicorn|aria2c|qbittorrent-nox|ffmpeg|rclone'),
                asyncio.create_subprocess_exec('python3', 'update.py')
            )
            async with aiofiles.open(".restartmsg", "w") as f:
                await f.write(f"{message.chat.id}\n{message.id}\n")
            os.execl(sys.executable, sys.executable, "-m", "bot")

        @dp.message_handler(filters=filters.command(bot_commands.PingCommand) & filters.authorized & ~filters.blacklisted)
        async def ping_handler(message: Message):
            """Handle /ping command by authorized and non-blacklisted users"""
            start_time = time.monotonic()
            reply = await message_utils.send_message(message, theme.get_ping())
            end_time = time.monotonic()
            await message_utils.edit_message(reply, theme.get_ping_value(int((end_time - start_time) * 1000)))

        @dp.message_handler(filters=filters.command(bot_commands.HelpCommand) & filters.authorized & ~filters.blacklisted)
        async def help_handler(message: Message):
            """Handle /help command by authorized and non-blacklisted users"""
            buttons = button_builder.build_menu(2)
            await message_utils.send_message(message, theme.get_help_header(), buttons=buttons)

        @dp.message_handler(filters=filters.command(bot_commands.StatsCommand) & filters.authorized & ~filters.blacklisted)
        async def stats_handler(message: Message):
            """Handle /stats command by authorized and non-blacklisted users"""
            msg, btns = await get_stats(message)
            await message_utils.send_message(message, msg, buttons=btns, photo='IMAGES')

        @dp.message_handler(filters=filters.command(bot_commands.LogCommand) & CustomFilters.sudo)
        async def log_handler(message: Message):
            """Handle /log command by sudo users"""
            pass

        dp.run()

bot = Bot(config_dict, user_data, bot_start_time, LOGGER)
try:
    asyncio.run(bot.start())
except KeyboardInterrupt:
    LOGGER.info("Shutting down...")
