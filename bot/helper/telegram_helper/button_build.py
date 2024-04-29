from typing import List, Union, Dict

from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton

def create_keyboard(buttons: List[List[str]], row_width: int = 3) -> InlineKeyboardMarkup:
    """
    Create an InlineKeyboardMarkup object from a list of buttons.

    :param buttons: A list of lists of button labels.
    :param row_width: The maximum number of buttons in a single row.
    :return: An InlineKeyboardMarkup object.
    """
    keyboard = []
    row = []
    for button_labels in buttons:
        for button_label in button_labels:
            row.append(InlineKeyboardButton(button_label, callback_data=button_label))
            if len(row) == row_width:
                keyboard.append(row)
                row = []
        if row:
            keyboard.append(row)
            row = []
    return InlineKeyboardMarkup(keyboard)

