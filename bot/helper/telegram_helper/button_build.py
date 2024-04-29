from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from typing import List, Union

class ButtonMaker:
    """
    Class for creating and managing inline keyboard buttons.
    """

    def __init__(self):
        """
        Initialize the class with empty lists for storing buttons.
        """
        self.__buttons: List[List[Union[InlineKeyboardButton, str]]] = [[]]
        self.__positions: List[str] = []

    def ubutton(self, key: str, link: str, position: str = None) -> None:
        """
        Add a URL button to the specified position.

        :param key: The text on the button
        :param link: The URL the button links to
        :param position: The position of the button, can be 'header', 'f_body', 'l_body', 'footer' or None
        """
        self.__add_button(InlineKeyboardButton(text=key, url=link), position)

    def ibutton(self, key: str, data: str, position: str = None) -> None:
        """
        Add a callback button to the specified position.

        :param key: The text on the button
        :param data: The data the button sends when clicked
        :param position: The position of the button, can be 'header', 'f_body', 'l_body', 'footer' or None
        """
        self.__add_button(InlineKeyboardButton(text=key, callback_data=data), position)

    def __add_button(self, button: InlineKeyboardButton, position: str = None) -> None:
        """
        Add a button to the appropriate list based on the position.

        :param button: The button to add
        :param position: The position of the button, can be 'header', 'f_body', 'l_body', 'footer' or None
        """
        if position is None:
            self.__buttons[-1].append(button)
        elif position in self.__positions:
            self.__buttons[self.__positions.index(position)].append(button)
        else:
            raise ValueError(f"Invalid position: {position}")

    def build_menu(self) -> InlineKeyboardMarkup:
        """
        Build the inline keyboard markup from the stored buttons.

        :return: The InlineKeyboardMarkup object
        """
        return InlineKeyboardMarkup(self.__buttons)

    def clear_buttons(self) -> None:
        """
        Clear all buttons.
        """
        self.__buttons = [[]]
        self.__positions = []
