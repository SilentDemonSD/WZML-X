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

    async def create_account(self) -> None:
        """
        Create a new Telegraph account.
        """
        retry_after = 0
        while retry_after < 5:
            try:
                response = await self.telegraph.create_account(
                    short_name=self.short_name,
                    author_name=self.author_name,
                    author_url=self.author_url,
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
        return await self._request_telegraph(
            self.telegraph.create_page,
            title=title,
            author_name=self.author_name,
            author_url=self.author_url,
            html_content=content,
            retry_after_error=retry_after_error,
        )

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
        return await self._request_telegraph(
            self.telegraph.edit_page,
            path=path,
            title=title,
            author_name=self.author_name,
            author_url=self.author_url,
            html_content=content,
            retry_after_error=retry_after_error,
        )

    async def _request_telegraph(
        self,
        request_func,
        *args,
        retry_after_error: bool = True,
        **kwargs,
    ) -> Optional[Dict[str, Any]]:
        try:
            response = await request_func(*args, **kwargs)
            return response
        except tg_exceptions.RetryAfterError as e:
            if retry_after_error:
                logger.warning(f"Telegraph Flood control exceeded. Retrying in {e.retry_after} seconds...")
                await asyncio.sleep(e.retry_after)
                return await self._request_telegraph(request_func, *args, **kwargs, retry_after_error=False)
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
        async with aiohttp.ClientSession() as session:
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
                try:
                    await self.edit_page(
                        path=path[prev_page],
                        title=f"{config_dict['TITLE_NAME']} Torrent Search",
                        content=content,
                    )
                except tg_exceptions.RetryAfterError as e:
                    logger.warning(f"Telegraph Flood control exceeded. Retrying in {e.retry_after} seconds...")
                    await asyncio.sleep(e.retry_after)

if __name__ == "__main__":
    # Ensure that the config_dict variable is defined
    import sys

    if "config_dict" in globals():
        telegraph = TelegraphHelper(config_dict["AUTHOR_NAME"], config_dict["AUTHOR_URL"])
        bot_loop = asyncio.get_event_loop()
        bot_loop.run_until_complete(telegraph.create_account())
    else:
        logger.error("config_dict variable is not defined.")
        sys.exit(1)
