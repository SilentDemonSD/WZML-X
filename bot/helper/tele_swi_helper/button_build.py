class ButtonMaker:
    def __init__(self, isSwitch=False):
        if isSwitch:
            from swibots import InlineKeyboardButton, InlineMarkup
            self.InlineKeyboardButton = InlineKeyboardButton
            self.InlineMarkup = InlineMarkup
        else:
            from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup
            self.InlineKeyboardButton = InlineKeyboardButton
            self.InlineMarkup = InlineKeyboardMarkup
        self.isSwitch = isSwitch
        self.__button = []
        self.__header_button = []
        self.__first_body_button = []
        self.__last_body_button = []
        self.__footer_button = []
        self.button_lists = {
            None: self.__button,
            "header": self.__header_button,
            "f_body": self.__first_body_button,
            "l_body": self.__last_body_button,
            "footer": self.__footer_button,
        }

    def ubutton(self, key, link, position=None):
        self.button_lists.get(position, self.__button).append(self.InlineKeyboardButton(text=key, url=link))

    def ibutton(self, key, data, position=None):
        self.button_lists.get(position, self.__button).append(self.InlineKeyboardButton(text=key, callback_data=data))
    
    def add_buttons(self, button_list, cols, menu, insert_at_start=False):
        if button_list:
            chunks = [button_list[i: i + cols] for i in range(0, len(button_list), cols)]
            if insert_at_start:
                menu[:0] = chunks
            else:
                menu.extend(chunks)

    def build_menu(self, b_cols=1, h_cols=8, fb_cols=2, lb_cols=2, f_cols=8):
        menu = [self.__button[i: i + b_cols] for i in range(0, len(self.__button), b_cols)]

        self.add_buttons(self.__header_button, h_cols, menu, True)
        self.add_buttons(self.__first_body_button, fb_cols, menu)
        self.add_buttons(self.__last_body_button, lb_cols, menu)
        self.add_buttons(self.__footer_button, f_cols, menu)

        return self.InlineMarkup(menu)
    
    def reset(self):
        self.__button, self.__header_button, self.__first_body_button, self.__last_body_button, self.__footer_button = [], [], [], [], []
