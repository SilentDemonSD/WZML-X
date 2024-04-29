import asyncio
import logging
import random
import string
from typing import Any, Dict, List, Optional

import aiohttp
from telegraph import Telegraph, exceptions as tg_exceptions

logger = logging.getLogger(__name__)

class TelegraphHelper:
    """
    Helper class for interacting with Telegraph API.
    """

    def __init__(self, author_name: str = None, author_url: str = None):
        self.telegraph = Telegraph(domain="graph.org")
        self.short_name = "".join(random.choices(string.ascii_letters, k=8))
        self.access_token = None
        self.author_name = author_name
        self.author_url = author_url

    def _get_telegraph_kwargs(
        self,
        request_func,
        *args,
        retry_on_flood_control: bool = True,
        **kwargs,
    ) -> Dict[str, Any]:
        kwargs["short_name"] = self.short_name
        kwargs["author_name"] = self.author_name
        kwargs["author_url"] = self.author_url
        return kwargs

    async def create_account(self) -> None:
        """
        Create a new Telegraph account.
        """
        retry_after = 0
        while retry_after < 5:
            try:
                response = await self.telegraph.create_account(
                    **self._get_telegraph_kwargs(self.telegraph.create_account)
                )
                self.access_token = self.telegraph.get_access_token()
                logger.info(f"Telegraph Account Generated : {self.short_name}")
                return response
            except tg_exceptions.RetryAfterError as e:
                logger.warning(f"Telegraph Flood control exceeded. Retrying in {e.retry_after} seconds...")
                retry_after = retry_after + e.retry_after
                await asyncio.sleep(e.retry_after)
        logger.error("Failed to create Telegraph account after 5 retries.")

    async def create_page(
        self, title: str, content: str, retry_on_flood_control: bool = True
    ) -> Optional[Dict[str, Any]]:
        """
        Create a new Telegraph page.

        Args:
            title (str): The title of the page.
            content (str): The content of the page.
            retry_on_flood_control (bool): Whether to retry if a RetryAfterError exception is raised.

        Returns:
            Optional[Dict[str, Any]]: The response from the Telegraph API, or None if an error occurred.
        """
        return await self._request_telegraph(
            self.telegraph.create_page,
            title=title,
            html_content=content,
            retry_on_flood_control=retry_on_flood_control,
            **self._get_telegraph_kwargs(self.telegraph.create_page),
        )

    async def edit_page(
        self, path: str, title: str, content: str, retry_on_flood_control: bool = True
    ) -> Optional[Dict[str, Any]]:
        """
        Edit an existing Telegraph page.

        Args:
            path (str): The path of the page.
            title (str): The title of the page.
            content (str): The content of the page.
            retry_on_flood_control (bool): Whether to retry if a RetryAfterError exception is raised.

        Returns:
            Optional[Dict[str, Any]]: The response from the Telegraph API, or None if an error occurred.
        """
        return await self._request_telegraph(
            self.telegraph.edit_page,
            path=path,
            title=title,
            html_content=content,
            retry_on_flood_control=retry_on_flood_control,
            **self._get_telegraph_kwargs(self.telegraph.edit_page),
        )

    async def _request_telegraph(
        self,
        request_func,
        *args,
        retry_on_flood_control: bool = True,
        **kwargs,
    ) -> Optional[Dict[str, Any]]:
        try:
            response = await request_func(*args, **kwargs)
            return response
        except tg_exceptions.RetryAfterError as e:
            if retry_on_flood_control:
                logger.warning(
