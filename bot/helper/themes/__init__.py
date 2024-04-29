#!/usr/bin/env python3
import os
from os.path import join
from importlib import import_module
from random import choice as rchoice
from bot import config_dict, LOGGER
from bot.helper.themes import wzml_minimal

AVAILABLE_THEMES: dict = {}
theme_directory: str = join('bot', 'helper', 'themes')

if 'BOT_THEME' in config_dict:
    if os.path.exists(theme_directory):
        for theme in os.listdir(theme_directory):
            if theme.startswith('wzml_') and theme.endswith('.py'):
                theme_name: str = theme[5:-3]
                try:
                    theme_module: object = import_module(f'bot.helper.themes.{theme_name}')
                except ModuleNotFoundError:
                    continue
                if hasattr(theme_module, 'WZMLStyle'):
                    style_module: object = getattr(theme_module, 'WZMLStyle')
                    if hasattr(style_module(), var_name):
                        AVAILABLE_THEMES[theme_name] = style_module

def bot_theme(var_name: str, **format_vars: dict) -> str:
    text: str = None
    theme_: str = config_dict.get('BOT_THEME')

    if theme_ and theme_ in AVAILABLE_THEMES:
        style_module: object = AVAILABLE_THEMES[theme_]
        if hasattr(style_module, var_name):
            text = getattr(style_module, var_name)
            if text and hasattr(text, 'format_map'):
                if format_vars:
                    return text.format_map(format_vars)
                else:
                    LOGGER.error(f"No format variables provided for {var_name} in {theme_}")
            else:
                LOGGER.error(f"{var_name} not a string or doesn't have a format_map method in {theme_}")
    elif theme_ == 'random':
        if AVAILABLE_THEMES:
            rtheme: str = rchoice(list(AVAILABLE_THEMES.keys()))
            LOGGER.info(f"Random Theme Chosen: {rtheme}")
            style_module: object = AVAILABLE_THEMES[rtheme]
            if hasattr(style_module, var_name):
                text = getattr(style_module, var_name)
                if text and hasattr(text, 'format_map'):
                    if format_vars:
                        return text.format_map(format_vars)
                    else:
                        LOGGER.error(f"No format variables provided for {var_name} in {rtheme}")
                else:
                    LOGGER.error(f"{var_name} not a string or doesn't have a format_map method in {rtheme}")
    else:
        style_module: object = wzml_minimal
        if hasattr(style_module, 'WZMLStyle'):
            style_module = getattr(style_module, 'WZMLStyle')
            if hasattr(style_module, var_name):
                text = getattr(style_module, var_name)
                if text and hasattr(text, 'format_map'):
                    if format_vars:
                        return text.format_map(format_vars)
                    else:
                        LOGGER.error(f"No format variables provided for {var_name} in wzml_minimal")
                else:
                    LOGGER.error(f"{var_name} not a string or doesn't have a format_map method in wzml_minimal")

    if text and hasattr(text, 'format_map'):
        if format_vars:
            return text.format_map(format_vars)
        else:
            LOGGER.error(f"No format variables provided for {var_name} in any available themes")
    else:
        LOGGER.error(f"{var_name} not a string or doesn't have a format_map method in any available themes")
    return None

