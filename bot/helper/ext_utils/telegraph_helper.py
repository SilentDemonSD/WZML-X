#!/usr/bin/env python3
from string import ascii_letters
from random import SystemRandom
from asyncio import sleep
from telegraph.aio import Telegraph
from telegraph.exceptions import RetryAfterError

from bot import LOGGER, bot_loop, config_dict

class TelegraphHelper:
    """
    A helper class for working with the Telegraph API.
    """

    def __init__(self, telegraph: Telegraph, author_name: str = None, author_url: str = None):
        """
        Initialize a new `TelegraphHelper` instance.

        :param telegraph: A `Telegraph` object for interacting with the Telegraph API.
        :param author_name: The name of the account author.
        :param author_url: The URL of the account author.
        """
        self.telegraph = telegraph
        self.short_name = ''.join(SystemRandom().choices(ascii_letters, k=8))
        self.access_token = None
        self.author_name = author_name
        self.author_url = author_url

    def __str__(self):
        """
        Return a human-readable representation of the `TelegraphHelper` object.

        :return: A string representation of the object.
        """
        return f"TelegraphHelper(access_token='{self.access_token}', author_name='{self.author_name}', author_url='{self.author_url}', short_name='{self.short_name}')"

    async def create_account(self):
        """
        Create a new Telegraph account.

        :return: None
        """
        try:
            await self.telegraph.create_account(
                short_name=self.short_name,
                author_name=self.author_name,
                author_url=self.author_url
            )
            self.access_token = self.telegraph.get_access_token()
            LOGGER.info("Creating Telegraph Account")
        except Exception as e:
            LOGGER.error(f"Error creating Telegraph account: {e}")

    async def create_page(self, title: str, content: str):
        """
        Create a new Telegraph page.

        :param title: The title of the page.
        :param content: The content of the page.
        :return: The created page object.
        """
        try:
            return await self.telegraph.create_page(
                title=title,
                author_name=self.author_name,
                author_url=self.author_url,
                html_content=content
            )
        except RetryAfterError as st:
            LOGGER.warning(
                f'Telegraph Flood control exceeded. I will sleep for {st.retry_after} seconds.')
            await sleep(st.retry_after)
            return await self.create_page(title, content)

    async def edit_page(self, path: str, title: str, content: str):
        """
        Edit an existing Telegraph page.

        :param path: The path of the page.
        :param title: The title of the page.
        :param content: The content of the page.
        :return: The edited page object.
        """
        try:
            return await self.telegraph.edit_page(
                path=path,
                title=title,
                author_name=self.author_name,
                author_url=self.author_url,
                html_content=content
            )
        except RetryAfterError as st:
            LOGGER.warning(
                f'Telegraph Flood control exceeded. I will sleep for {st.retry_after} seconds.')
            await sleep(st.retry_after)
            return await self.edit_page(path, title, content)

    async def edit_telegraph(self, path: list, telegraph_content: list):
        """
        Edit multiple Telegraph pages.

        :param path: A list of paths for the pages to be edited.
        :param telegraph_content: A list of content strings for the pages.
        :return: None
        """
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
                content=content
            )
        return


if __name__ == "__main__":
    if config_dict is not None:
        telegraph = TelegraphHelper(Telegraph(domain='graph.org'), config_dict['AUTHOR_NAME'],
                                    config_dict['AUTHOR_URL'])

        bot_loop.run_until_complete(telegraph.create_account())
    else:
        LOGGER.error("config_dict is not defined")
