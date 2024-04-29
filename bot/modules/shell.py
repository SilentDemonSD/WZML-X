#!/usr/bin/env python3
import asyncio
import io
import logging
import sys

import pyrogram
from pyrogram.errors import RpcError
from pyrogram.handlers import MessageHandler, EditedMessageHandler

