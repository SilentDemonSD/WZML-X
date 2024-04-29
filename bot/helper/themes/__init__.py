#!/usr/bin/env python3
import os
from os import listdir
from importlib import import_module
from random import choice as rchoice
from typing import Any, Dict, Union

from bot import config_dict, LOGGER
from bot.helper.themes import WzmlMinimal

AVAILABLE_THEMES: Dict[str, Any] = {}
for theme in listdir('bot/helper/themes'):
    if theme.startswith('wzml_') and theme.endswith('.py'):
        AVAILABLE_THEMES[theme[5:-3]] = import_module(f'bot.helper.themes.{theme[:-3]}')

def bot_theme(var_name: str, **format_vars: Any) -> str:
    text = None
    theme_name = config_dict.get('BOT_THEME')

    if theme_name and theme_name in AVAILABLE_THEMES:
        theme_module = AVAILABLE_THEMES[theme_name]
        text = getattr(theme_module.WzmlStyle(), var_name, None)
        if text is None:
            LOGGER.error(f"{var_name} not found in {theme_name}. Please recheck with Official Repo")
    elif theme_name == 'random':
        valid_themes = list(AVAILABLE_THEMES.values())
        if valid_themes:
            rtheme = rchoice(valid_themes)
            LOGGER.info(f"Random Theme Chosen: {rtheme}")
            theme_module = rtheme
            text = getattr(theme_module.WzmlStyle(), var_name, None)
            if text is None:
                LOGGER.error(f"{var_name} not found in {theme_name}. Please recheck with Official Repo")
    else:
        theme_module = WzmlMinimal

    if text is not None and var_name in dir(theme_module.WzmlStyle()) and callable(getattr(theme_module.WzmlStyle(), var_name)):
        if format_vars:
            return getattr(theme_module.WzmlStyle(), var_name)(**format_vars)
        else:
            LOGGER.error("No format variables provided")
    else:
        LOGGER.error(f"{var_name} is not a valid attribute of WzmlStyle or not callable")
