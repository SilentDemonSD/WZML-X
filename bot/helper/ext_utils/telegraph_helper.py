#!/usr/bin/env python3
from string import ascii_letters
from random import SystemRandom
from asyncio import sleep
from telegraph.aio import Telegraph
from telegraph.exceptions import RetryAfterError
from typing import Any, Dict, List, Optional
import logging
import contextlib

from bot import LOGGER, bot_loop, config_dict

logger = logging.getLogger(__name__)

class TelegraphHelper:
    """
    Helper class for interacting with Telegraph API.
    """

    def __init__(self, author_name: str = None, author_url: str = None):
        self.telegraph = Telegraph(domain="graph.org")
        self.short_name = "".join(SystemRandom().choices(ascii_letters, k=8))
        self.access_token = None
        self.author_name = author_name
        self.author_url = author_url

    async def create_account(self) -> None:
        """
        Create a new Telegraph account.
        """
        try:
            await self.telegraph.create_account(
                short_name=self.short_name,
                author_name=self.author_name,
                author_url=self.author_url,
            )
            self.access_token = self.telegraph.get_access_token()
            logger.info(f"Telegraph Account Generated : {self.short_name}")
        except RetryAfterError as e:
            logger.warning(f"Telegraph Flood control exceeded. Retrying in {e.retry_after} seconds...")
            await sleep(e.retry_after)
            await self.create_account()

    async def create_page(
        self, title: str, content: str, retry_after_error: bool = True
    ) -> Optional[Dict[str, Any]]:
        """
        Create a new Telegraph page.

        Args:
            title (str): The title of the page.
            content (str): The content of the page.
            retry_after_error (bool): Whether to retry if a RetryAfterError exception is raised.

        Returns:
            Optional[Dict[str, Any]]: The response from the Telegraph API, or None if an error occurred.
        """
        try:
            return await self.telegraph.create_page(
                title=title,
                author_name=self.author_name,
                author_url=self.author_url,
                html_content=content,
            )
        except RetryAfterError as e:
            if retry_after_error:
                logger.warning(f"Telegraph Flood control exceeded. Retrying in {e.retry_after} seconds...")
                await sleep(e.retry_after)
                return await self.create_page(title, content, retry_after_error=False)
            else:
                logger.error(f"Telegraph Flood control exceeded and retry is disabled.")
                return None

    async def edit_page(
        self, path: str, title: str, content: str, retry_after_error: bool = True
    ) -> Optional[Dict[str, Any]]:
        """
        Edit an existing Telegraph page.

        Args:
            path (str): The path of the page.
            title (str): The title of the page.
            content (str): The content of the page.
            retry_after_error (bool): Whether to retry if a RetryAfterError exception is raised.

        Returns:
            Optional[Dict[str, Any]]: The response from the Telegraph API, or None if an error occurred.
        """
        try:
            return await self.telegraph.edit_page(
                path=path,
                title=title,
                author_name=self.author_name,
                author_url=self.author_url,
                html_content=content,
            )
        except RetryAfterError as e:
            if retry_after_error:
                logger.warning(f"Telegraph Flood control exceeded. Retrying in {e.retry_after} seconds...")
                await sleep(e.retry_after)
                return await self.edit_page(path, title, content, retry_after_error=False)
            else:
                logger.error(f"Telegraph Flood control exceeded and retry is disabled.")
                return None

    async def edit_telegraph(
        self, path: List[str], telegraph_content: List[str]
    ) -> None:
        """
        Edit multiple Telegraph pages.

        Args:
            path (List[str]): The paths of the pages.
            telegraph_content (List[str]): The content of the pages.
        """
        with contextlib.suppress(RetryAfterError):
            nxt_page = 1
            prev_page = 0
            num_of_path = len(path)
            for content in telegraph_content:
                if nxt_page == 1:
                    content += f'<b><a href="https://telegra.ph/{path[nxt_page]}">Next</a></b>'
                    nxt_page += 1
                else:
                    if prev_page <= num_of_path:
                        content += f'<b><a href="https://telegra.ph/{path[prev_page]}">Prev</a></b>'
                        prev_page += 1
                    if nxt_page < num_of_path:
                        content += f'<b> | <a href="https://telegra.ph/{path[nxt_page]}">Next</a></b>'
                        nxt_page += 1
                await self.edit_page(
                    path=path[prev_page],
                    title=f"{config_dict['TITLE_NAME']} Torrent Search",
                    content=content,
                )

# Ensure that the config_dict variable is defined
if "config_dict" in globals():
    telegraph = TelegraphHelper(config_dict["AUTHOR_NAME"], config_dict["AUTHOR_URL"])
    bot_loop.run_until_complete(telegraph.create_account())
else:
    logger.error("config_dict variable is not defined.")
