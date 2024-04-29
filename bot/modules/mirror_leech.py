import asyncio
import re
from typing import Dict, List, Tuple, Union

import aiofiles
import aiofiles.os
import cloudscraper
import html
import pyrogram.filters
import pyrogram.handlers
import pyrogram.scaffold
import pyrogram.types
from base64 import b64encode
from re import match as re_match
from traceback import format_exc
from urllib.parse import unquote

