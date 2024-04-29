from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from typing import List, Union

class ButtonMaker:
    """
    A class for building Telegram inline keyboards.
    """

    def __init__(self):
        self.__buttons: List[List[Union[InlineKeyboardButton, List[InlineKeyboardButton]]]] = [[]]
        self.__header_buttons: List[InlineKeyboardButton] = []
        self.__footer_buttons: List[InlineKeyboardButton] = []

    def build_button(
        self, key: str, link: str, position: str = None
    ) -> "ButtonMaker":
        """
        Add a new InlineKeyboardButton to the list of buttons.

        :param key: The text of the button
        :param link: The URL of the button
        :param position: The position of the button in the keyboard. Can be 'header', 'footer', or None.
        :return: The instance of the ButtonMaker class
        """
        button = InlineKeyboardButton(text=key, url=link)
        if position == "header":
            self.__header_buttons.append(button)
        elif position == "footer":
            self.__footer_buttons.append(button)
        else:
            self.__buttons[-1].append(button)
        return self

    def switch_button(
        self, key: str, data: str, position: str = None
    ) -> "ButtonMaker":
        """
        Add a new InlineKeyboardButton with callback data to the list of buttons.

        :param key: The text of the button
        :param data: The callback data of the button
        :param position: The position of the button in the keyboard. Can be 'header', 'footer', or None.
        :return: The instance of the ButtonMaker class
        """
        button = InlineKeyboardButton(text=key, callback_data=data)
        if position == "header":
            self.__header_buttons.append(button)
        elif position == "footer":
            self.__footer_buttons.append(button)
        else:
            self.__buttons[-1].append(button)
        return self

    def build_menu(
        self, n_cols: int = 3
    ) -> InlineKeyboardMarkup:
        """
        Build the final InlineKeyboardMarkup object.

        :param n_cols: The number of columns in the keyboard.
        :return: The InlineKeyboardMarkup object
        """
        if self.__header_buttons:
            self.__buttons.insert(0, self.__header_buttons)

        if self.__footer_buttons:
            if len(self.__footer_buttons) > 8:
                self.__buttons.append([self.__footer_buttons[i:i + 8] for i in range(0, len(self.__footer_buttons), 8)])
            else:
                self.__buttons.append(self.__footer_buttons)

        menu = [button for row in self.__buttons for button in row if button]
        return InlineKeyboardMarkup(menu)
