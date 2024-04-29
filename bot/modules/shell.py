#!/usr/bin/env python3
import asyncio
import io
import logging
import sys

import pyrogram
from pyrogram.errors import RpcError
from pyrogram.handlers import MessageHandler, EditedMessageHandler
from pyrogram.filters import command

log = logging.getLogger(__name__)

class ShellBot(pyrogram.Client):
    def __init__(self):
        super().__init__(
            name="ShellBot",
            api_id=<your_api_id>,
            api_hash=<your_api_hash>,
            bot_token=<your_bot_token>,
            plugins=dict(root="bot.plugins"),
        )

