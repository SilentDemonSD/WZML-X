#!/usr/bin/env python3

import asyncio
import os
import secrets
import logging
import mega
from aiofiles.os import makedirs
from typing import Dict, Union, Optional

import bot
import config_dict
import download_dict_lock
import download_dict
import non_queued_dl
import queue_dict_lock
import stop_duplicate_check

def get_mega_link_type(mega_link: str) -> str:
    # Implement the function to get mega link type
    pass

def async_to_sync(func):
    async def wrapper(*args, **kwargs):
        return asyncio.run(func(*args, **kwargs))
    return wrapper

def sync_to_async(func):
    async def wrapper(*args, **kwargs):
        return await asyncio.get_event_loop().run_in_executor(None, func, *args, **kwargs)
    return wrapper

class MegaApi:
    def __init__(self, email, password):
        self.mega = mega.Mega()
        self.email = email
        self.password = password

    async def login(self):
        await self.mega.login(self.email, self.password)

    def get_node_by_link(self, link):
        return self.mega.get_node_by_link(link)

class MegaDownloadManager:
    COMPLETED = "completed"
    FAILED = "failed"
    PENDING = "pending"
    CANCELED = "canceled"

    def __init__(self, mega_api: MegaApi):
        self.mega_api = mega_api
        self.download_status = {}

    async def download_file(self, link: str, dest_folder: str):
        node = await self.mega_api.get_node_by_link(link)
        if node is None:
            self.download_status[link] = MegaDownloadStatus(link, status=MegaDownloadManager.FAILED)
            return

        status = MegaDownloadStatus(link, status=MegaDownloadManager.PENDING, node=node, size=node.size)
        self.download_status[link] = status

        try:
            await non_queued_dl.download_file(mega_api.mega, node, dest_folder)
            status.status = MegaDownloadManager.COMPLETED
        except Exception as e:
            logging.error(f"Failed to download {link}: {e}")
            status.status = MegaDownloadManager.FAILED


