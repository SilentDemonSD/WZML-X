#!/usr/bin/env python3

import asyncio
import secrets
from aiofiles.os import makedirs
from typing import Dict, Union

import logging
from mega import MegaApi, MegaListener, MegaRequest, MegaTransfer, MegaError

# Import helper functions and classes
# Assuming bot, config_dict, download_dict_lock, download_dict, non_queued_dl, queue_dict_lock, get_mega_link_type, async_to_sync, sync_to_async, MegaDownloadStatus, QueueStatus, is_queued, limit_checker, and stop_duplicate_check are imported here.

class MegaAppListener(MegaListener):
    """Custom MegaListener class for handling Mega events."""

    # ... (class methods)

class AsyncExecutor:
    """Asynchronous task executor class."""

    # ... (class methods)


async def add_mega_download(mega_link: str, path: str, listener: MegaAppListener, name: str) -> None:
    """
    Add a Mega download with the given parameters.

    :param mega_link: The Mega link to download.
    :param path: The destination path.
    :param listener: The MegaAppListener instance.
    :param name: The name of the download.
    :return: None
    """
    # ... (function body)
