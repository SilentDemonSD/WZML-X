#!/usr/bin/env python3

import asyncio
import os
import secrets
from aiofiles.os import makedirs
from typing import Dict, Union

import logging
import mega

# Import helper functions and classes
import bot
import config_dict
import download_dict_lock
import download_dict
import non_queued_dl
import queue_dict_lock
import stop_duplicate_check

def get_mega_link_type(mega_link: str) -> str:
    # ... (function body)

async def async_to_sync(func):
    # ... (function body)

def sync_to_async(func):
    # ... (function body)

class MegaDownloadStatus:
    # ... (class attributes)

