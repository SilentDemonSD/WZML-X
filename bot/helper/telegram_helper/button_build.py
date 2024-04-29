from typing import List, Union

from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton

class ButtonMaker:
    """
    Class for creating and managing inline keyboard buttons.
    """

    def __init__(self):
        self.__button_lists: List[List[Union[InlineKeyboardButton, str]]] = [
            [],  # header
            [],  # first body
            [],  # last body
            [],  # footer
            []   # buttons
        ]

    def ubutton(self, key: str, link: str, position: str = None) -> None:
        """
        Adds a URL button to the button list.

        :param key: The text of the button
        :param link: The URL of the button
        :param position: The position of the button. Can be 'header', 'f_body', 'l_body', 'footer', or None
        """
        if position is None:
            position = 'buttons'

        if position not in ['header', 'f_body', 'l_body', 'footer', 'buttons']:
            raise ValueError(f"Invalid position '{position}', must be one of 'header', 'f_body', 'l_body', 'footer', or None")

        self.__button_lists[position].append(InlineKeyboardButton(text=key, url=link))

    def ibutton(self, key: str, data: str, position: str = None) -> None:
        """
        Adds a callback button to the button list.

        :param key: The text of the button
        :param data: The callback data of the button
        :param position: The position of the button. Can be 'header', 'f_body', 'l_body', 'footer', or None
        """
        if position is None:
            position = 'buttons'

        if position not in ['header', 'f_body', 'l_body', 'footer', 'buttons']:
            raise ValueError(f"Invalid position '{position}', must be one of 'header', 'f_body', 'l_body', 'footer', or None")

        self.__button_lists[position].append(InlineKeyboardButton(text=key, callback_data=data))

    def build_menu(self) -> InlineKeyboardMarkup:
        """
        Builds the inline keyboard markup from the button lists.

        :return: The InlineKeyboardMarkup object
        """
        menu = [self.__button_lists[i] for i in [4, 0, 2, 3, 1] if self.__button_lists[i]]
        return InlineKeyboardMarkup(menu)
