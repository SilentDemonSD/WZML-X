#!/usr/bin/env python3

import asyncio
from typing import Dict, Any, Optional, TypeVar, Union  # Importing various types from the typing module

from pyrogram.types import InlineKeyboardMarkup, CallbackQuery  # Importing InlineKeyboardMarkup and CallbackQuery from the pyrogram.types module
from pyrogram.handlers import CallbackQueryHandler  # Importing CallbackQueryHandler from the pyrogram.handlers module
from pyrogram.filters import regex  # Importing regex from the pyrogram.filters module

import bot  # Importing the bot module
from bot import bot, bot_name, user_data  # Importing bot, bot_name, and user_data from the bot module

