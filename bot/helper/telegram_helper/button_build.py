from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from typing import List, Union

class ButtonMaker:
    """
    A class to build InlineKeyboardMarkup with buttons.
    """

    def __init__(self):
        """
        Initialize the class with empty lists for buttons.
        """
        self.__button: List[List[Union[InlineKeyboardButton, str]]] = []
        self.__header_button: List[Union[InlineKeyboardButton, str]] = []
        self.__footer_button: List[Union[InlineKeyboardButton, str]] = []

    def ubutton(self, key: str, link: str, position: str = None) -> None:
        """
        Add a URL button to the buttons list.

        :param key: The text on the button
        :param link: The URL to open when the button is clicked
        :param position: The position of the button (default: None, which means add to the main list)
        """
        if position is None:
            self.__button.append([InlineKeyboardButton(text=key, url=link)])
        elif position == 'header':
            self.__header_button.append(InlineKeyboardButton(text=key, url=link))
        elif position == 'footer':
            self.__footer_button.append(InlineKeyboardButton(text=key, url=link))
        else:
            raise ValueError(f"Invalid position value '{position}', should be None, 'header', or 'footer'")

    def ibutton(self, key: str, data: str, position: str = None) -> None:
        """
        Add a callback button to the buttons list.

        :param key: The text on the button
        :param data: The data to send to the bot when the button is clicked
        :param position: The position of the button (default: None, which means add to the main list)
        """
        if position is None:
            self.__button.append([InlineKeyboardButton(text=key, callback_data=data)])
        elif position == 'header':
            self.__header_button.append(InlineKeyboardButton(text=key, callback_data=data))
        elif position == 'footer':
            self.__footer_button.append(InlineKeyboardButton(text=key, callback_data=data))
        else:
            raise ValueError(f"Invalid position value '{position}', should be None, 'header', or 'footer'")

    def build_menu(self, b_cols: int = 1, h_cols: int = 8, f_cols: int = 8) -> InlineKeyboardMarkup:
        """
        Build the InlineKeyboardMarkup with the buttons.

        :param b_cols: The number of columns in the main buttons list
        :param h_cols: The number of columns in the header buttons list
        :param f_cols: The number of columns in the footer buttons list
        :return: The InlineKeyboardMarkup object
        """
        menu: List[List[Union[InlineKeyboardButton, str]]] = []
        if self.__header_button:
            h_cnt = len(self.__header_button)
            if h_cnt > h_cols:
                header_buttons = [self.__header_button[i:i+h_cols] for i in range(0, h_cnt, h_cols)]
                menu.extend(header_buttons)
            else:
                menu.append(self.__header_button)
        for i in range(0, len(self.__button), b_cols):
            menu.append(self.__button[i:i+b_cols])
        if self.__footer_button:
            f_cnt = len(self.__footer_button)
            if f_cnt > f_cols:
                footer_buttons = [self.__footer_button[i:i+f_cols] for i in range(0, f_cnt, f_cols)]
                menu.append(footer_buttons)
            else:
                menu.append(self.__footer_button)
        return InlineKeyboardMarkup(menu)

    def clear(self) -> None:
        """
        Clear all buttons.
        """
        self.__button.clear()
        self.__header_button.clear()
        self.__footer_button.clear()
