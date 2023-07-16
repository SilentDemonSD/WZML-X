#!/usr/bin/env python3
from os import listdir
from importlib import import_module
from random import choice as rchoice
from bot import config_dict, LOGGER
from bot.helper.themes import wzml_minimal

AVL_THEMES = {}
for theme in listdir('bot/helper/themes'):
    if theme.startswith('wzml') and theme.endswith('.py'):
        AVL_THEMES[str(theme[5:-3])] = import_module(f'bot.helper.themes.{theme[:-3]}')

class BotTheme():
    def __init__(self, var_name, fast_build=True, **init_vars):
        self.format_vars = {}
        self.var_name = var_name
        self.format_vars.update(init_vars)
        if fast_build:
            return self.build_theme()
        
    def add_val(self, **more_vars):
        self.format_vars.update(more_vars)
        
    def build_theme(self):
        text = None
        theme_ = config_dict['BOT_THEME']
        LOGGER.info(AVL_THEMES)
        if theme_ in AVL_THEMES:
            text = getattr(AVL_THEMES[theme_].WZMLStyle(), self.var_name, None)
        elif theme_ == 'random':
            rantheme = rchoice(list(AVL_THEMES.values()))
            LOGGER.info(f"Random Theme Chosen: {rantheme}")
            text = getattr(rantheme.WZMLStyle(), self.var_name, None)
        if text is None:
            text = getattr(wzml_minimal.WZMLStyle(), self.var_name)

        return text.format_map(self.format_vars)
