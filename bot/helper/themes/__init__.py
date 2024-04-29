#!/usr/bin/env python3
import os
from os.path import join
from importlib import import_module
from random import choice as rchoice
from bot import config_dict, LOGGER
from bot.helper.themes import wzml_minimal

AVAILABLE_THEMES = {}
theme_directory = join('bot', 'helper', 'themes')
for theme in os.listdir(theme_directory):
    if theme.startswith('wzml_') and theme.endswith('.py'):
        theme_name = theme[5:-3]
        AVAILABLE_THEMES[theme_name] = import_module(f'bot.helper.themes.{theme_name}')

def bot_theme(var_name: str, **format_vars: dict) -> str:
    text = None
    theme_ = config_dict.get('BOT_THEME')

    if theme_ and theme_ in AVAILABLE_THEMES:
        theme_module = AVAILABLE_THEMES[theme_]
        if hasattr(theme_module, 'WZMLStyle'):
            style_module = getattr(theme_module, 'WZMLStyle')
            if hasattr(style_module(), var_name):
                text = getattr(style_module(), var_name)
                return text.format_map(format_vars)
            else:
                LOGGER.error(f"{var_name} not found in {theme_}. Please recheck with Official Repo")
    elif theme_ == 'random':
        available_themes = list(AVAILABLE_THEMES.values())
        rtheme = rchoice(available_themes)
        LOGGER.info(f"Random Theme Chosen: {rtheme}")
        if hasattr(rtheme, 'WZMLStyle'):
            style_module = getattr(rtheme, 'WZMLStyle')
            if hasattr(style_module(), var_name):
                text = getattr(style_module(), var_name)
                return text.format_map(format_vars)
    else:
        if hasattr(wzml_minimal, 'WZMLStyle'):
            style_module = getattr(wzml_minimal, 'WZMLStyle')
            if hasattr(style_module(), var_name):
                text = getattr(style_module(), var_name)
                return text.format_map(format_vars)

    LOGGER.error(f"{var_name} not found in any available themes. Please recheck with Official Repo")
    return None

