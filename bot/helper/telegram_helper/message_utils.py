import asyncio
import os
from re import match as re_match
from typing import Any, Dict, List, Optional

import aiofiles.os as aio_os
import cryptography.fernet as fernet
import pyrogram
from pyrogram.enums import ParseMode
from pyrogram.errors import (
    FloodWait,

