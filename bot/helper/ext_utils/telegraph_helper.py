from telegraph import Telegraph, exceptions as telegraph_exceptions

from bot import LOGGER, config_dict

class TelegraphHelper:
    """
    A helper class for interacting with the Telegraph API.
    """

    def __init__(self, author_name: str = None, author_url: str = None):
        self.telegraph = Telegraph(domain="graph.org")
        self.short_name = "".join(SystemRandom().choices(ascii_letters, k=8))
        self.access_token = None
        self.author_name = author_name
        self.author_url = author_url
        self.create_account()

    def create_account(self):
        """
        Create a new Telegraph account.
        """
        try:
            account_info = self.telegraph.create_account(
                short_name=self.short_name,
                author_name=self.author_name,
                author_url=self.author_url,
            )
        except telegraph_exceptions.TelegraphException as e:
            LOGGER.warning(f"Telegraph create account error: {e}")
            return

        self.access_token = account_info["access_token"]
        LOGGER.info("Telegraph account created")

    def create_page(self, title: str, content: str):
        """
        Create a new page with the given title and content.

        :return: The created page's info or None if an error occurred.
        """
        try:
            return self.telegraph.create_page(
                title=title,
                author_name=self.author_name,
                author_url=self.author_url,
                html_content=content,
            )
        except telegraph_exceptions.RetryAfterError as e:
            LOGGER.warning(
                f"Telegraph flood control exceeded. Sleeping for {e.retry_after} seconds."
            )
            sleep(e.retry_after)
            return self.create_page(title, content)
        except telegraph_exceptions.TelegraphException as e:
            LOGGER.warning(f"Telegraph create page error: {e}")
            return None

    def edit_page(self, path: str, title: str, content: str):
        """
        Edit an existing page with the given path, title, and content.

        :return: The edited page's info or None if an error occurred.
        """
        try:
            return self.telegraph.edit_page(
                path=path,
                title=title,
                author_name=self.author_name,
                author_url=self.author_url,
                html_content=content,
            )
        except telegraph_exceptions.RetryAfterError as e:
            LOGGER.warning(
                f"Telegraph flood control exceeded. Sleeping for {e.retry_after} seconds."
            )
            sleep(e.retry_after)
            return self.edit_page(path, title, content)
        except telegraph_exceptions.TelegraphException as e:
            LOGGER.warning(f"Telegraph edit page error: {e}")
            return None

    def edit_telegraph(self, path: list, telegraph_content: list):
        """
        Edit a series of Telegraph pages.

        :param path: A list of paths for the pages to be edited.
        :param telegraph_content: A list of HTML contents for the pages.
        """
        TITLE_NAME = config_dict["TITLE_NAME"]
        nxt_page = 1
        prev_page = 0
        num_of_path = len(path)

        for i, content in enumerate(telegraph_content):
            if nxt_page == 1:
                content += f'<b><a href="https://telegra.ph/{path[nxt_page]}">Next</a></b>'
                nxt_page += 1
            else:
                if prev_page < num_of_path:
                    content += f'<b><a href="https://telegra.ph/{path[prev_page]}">Prev</a></b>'
                    prev_page += 1
                if nxt_page < num_of_path:
                    content += f'<b> | <a href="https://telegra.ph/{path[nxt_page]}">Next</a></b>'
                    nxt_page += 1

            page_info = self.edit_page(path[prev_page], TITLE_NAME, content)
            if not page_info:
                LOGGER.warning(f"Failed to edit Telegraph page: {path[prev_page]}")
                continue

            LOGGER.info(f"Edited Telegraph page: {path[prev_page]}")

telegraph = None
try:
    AUTHOR_NAME = config_dict["AUTHOR_NAME"]
    AUTHOR_URL = config_dict["AUTHOR_URL"]

    if AUTHOR_NAME and AUTHOR_URL:
        telegraph = TelegraphHelper(AUTHOR_NAME, AUTHOR_URL)
except Exception as err:
    LOGGER.warning(f"Can't Create Telegraph Account: {err}")

if telegraph:
    # Use the telegraph object here
    pass
else:
    LOGGER.warning("Telegraph object not initialized")
