from random import choice as rchoice
from bot import config_dict, LOGGER, user_data 
from bot.helper.themes import wzml_minimal, wzml_emoji

AVL_THEMES = {'emoji': wzml_emoji, 'minimal': wzml_minimal}

def BotTheme(user_id):
    '''Author: MysterySD'''
    theme_ = user_data[user_id]['themes'] if user_id in user_data and user_data[user_id].get('themes') else config_dict['BOT_THEME']
    if theme_ in AVL_THEMES.keys():
        return (AVL_THEMES.get(theme_)).WZMLStyle()
    elif theme_ == "random":
        rantheme = rchoice(list(AVL_THEMES.values()))
        LOGGER.info(f"Random Theme Choosen : {rantheme}")
        return rantheme.WZMLStyle()
    else:
        return wzml_minimal.WZMLStyle()
