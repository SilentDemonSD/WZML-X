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
from pyrogram.errors import PeerIdInvalid
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

# Rest of the code remains the same
