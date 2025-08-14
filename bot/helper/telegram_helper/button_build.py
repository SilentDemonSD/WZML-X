from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup


class ButtonMaker:
    def __init__(self):
        self.buttons = {
            "default": [],
            "header": [],
            "f_body": [],
            "l_body": [],
            "footer": [],
        }

    def url_button(self, key, link, position=None):
        self.buttons[position if position in self.buttons else "default"].append(
            InlineKeyboardButton(text=key, url=link)
        )

    def data_button(self, key, data, position=None):
        self.buttons[position if position in self.buttons else "default"].append(
            InlineKeyboardButton(text=key, callback_data=data)
        )

    def build_menu(self, b_cols=1, h_cols=8, fb_cols=2, lb_cols=2, f_cols=8):
        def chunk(lst, n):
            return [lst[i: i + n] for i in range(0, len(lst), n)]
        
        menu = chunk(self.buttons["default"], b_cols)
        menu = (
            chunk(self.buttons["header"], h_cols) if self.buttons["header"] else []
        ) + menu
        for key, cols in (("f_body", fb_cols), ("l_body", lb_cols), ("footer", f_cols)):
            if self.buttons[key]:
                menu += chunk(self.buttons[key], cols)
        return InlineKeyboardMarkup(menu)

    def reset(self):
        for key in self.buttons:
            self.buttons[key].clear()