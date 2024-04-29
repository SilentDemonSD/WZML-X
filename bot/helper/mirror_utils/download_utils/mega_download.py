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

class QueueStatus:
    # ... (class attributes)

class MegaAppListener(mega.MegaListener):
    # ... (class methods)

class AsyncExecutor:
    # ... (class methods)

async def is_queued(name: str) -> bool:
    # ... (function body)

async def limit_checker():
    # ... (function body)

async def main():
    api = mega.MegaApi()
    await api.login(config_dict['mega_email'], config_dict['mega_password'])

    listener = MegaAppListener(api)
    executor = AsyncExecutor()

    @api.add_listener(listener)
    def on_login(self, api):
        logging.info("Logged in.")

    @api.add_listener(listener)
    def on_logout(self, api):
        logging.info("Logged out.")

    @api.add_listener(listener)
    def on_transfer_start(self, api, transfer):
        logging.info(f"Download started: {transfer.name}")

    @api.add_listener(listener)
    def on_transfer_data(self, api, transfer):
        status = MegaDownloadStatus(transfer)
        if status.is_completed():
            logging.info(f"Download completed: {transfer.name}")

    @api.add_listener(listener)
    def on_transfer_abort(self, api, transfer):
        logging.info(f"Download aborted: {transfer.name}")

    @api.add_listener(listener)
    def on_transfer_error(self, api, transfer, error):
        logging.error(f"Download error: {transfer.name}, Error: {error}")

    @api.add_listener(listener)
    def on_transfer_cancel(self, api, transfer):
        logging.info(f"Download canceled: {transfer.name}")

    while True:
        if not api or not api.is_logged_in():
            logging.info("Trying to log in...")
            api = mega.MegaApi()
            await api.login(config_dict['mega_email'], config_dict['mega_password'])
            continue

        if not await limit_checker():
            logging.info("Limit reached, waiting...")
            await asyncio.sleep(60)
            continue

        if await stop_duplicate_check.is_stopped():
            logging.info("Duplicate check stopped, exiting...")
            break

        for mega_link, path in config_dict['downloads'].items():
            if not await is_queued(mega_link):
                await add_mega_download(mega_link, path, listener, mega_link)

        await asyncio.sleep(10)

async def add_mega_download(mega_link: str, path: str, listener: MegaAppListener, name: str) -> None:
    # ... (function body)

if __name__ == "__main__":
    asyncio.run(main())
