from typing import List, Union, Dict

from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton

class ButtonMaker:
    """
    Class for creating and managing inline keyboard buttons.
    """

    def __init__(self):
        # Initialize the button lists with empty lists for each position: header, first body, last body, footer, and buttons
        self.__button_lists: Dict[str, List[List[InlineKeyboardButton]]] = {
            'header': [],  # header
            'f_body': [],  # first body
            'l_body': [],  # last body
            'footer': [],  # footer
            'buttons': []  # additional buttons
        }

    def add_button(
        self,
        text: str,
        callback_data: str = None,
        url: str = None,
        switch_inline_query: str = None,
        switch_inline_query_current_chat: str = None,
        callback_game: str = None,
        login_url: str = None,
        pay: bool = False,
        url_button: bool = False
    ) -> 'ButtonMaker':
        """
        Add a button to the 'buttons' list.

        :param text: The text on the button.
        :param callback_data: Data to be sent to the bot when the button is pressed.
        :param url: URL to be opened when the button is pressed.
        :param switch_inline_query: Switch to inline query.
        :param switch_inline_query_current_chat: Switch to inline query in the current chat.
        :param callback_game: Open a game.
        :param login_url: An URL to open in the user's browser.
        :param pay: Payment button.
        :param url_button: URL button.
        :return: The ButtonMaker instance itself for chaining.
        """
        button = InlineKeyboardButton(
            text=text,
            callback_data=callback_data,
            url=url,
            switch_inline_query=switch_inline_query,
            switch_inline_query_current_chat=switch_inline_query_current_chat,
            callback_game=callback_game,
            login_url=login_url,
            pay=pay,
            url_button=url_button
        )
        self.__button_lists['buttons'].append([button])
        return self

    def build_keyboard(self) -> InlineKeyboardMarkup:
        """
        Build and return the InlineKeyboardMarkup.

        :return: The InlineKeyboardMarkup.
        """
        return InlineKeyboardMarkup(self.__button_lists)

    # Add methods for adding buttons to header, first body, last body, and footer here, if needed.
