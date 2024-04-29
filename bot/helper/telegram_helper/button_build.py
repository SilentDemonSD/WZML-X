from typing import List, Union

from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton

class ButtonMaker:
    """
    Class for creating and managing inline keyboard buttons.
    """

    def __init__(self):
        # Initialize the button lists with empty lists for each position: header, first body, last body, footer, and buttons
        self.__button_lists = {
            'header': [],  # header
            'f_body': [],  # first body
            'l_body': [], 
