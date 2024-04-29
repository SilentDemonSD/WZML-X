import requests
from threading import Thread
from html import escape
from urllib.parse import quote
from telegram.ext import CommandHandler, CallbackQueryHandler
from typing import Dict, List, Union, Any, Tuple, Optional

from bot import dispatcher, LOGGER, config_dict, get_client
from bot.helper.telegram_helper.message_utils import editMessage, sendMessage
from bot.helper.ext_utils.telegraph_helper import telegraph
from bot.helper.telegram_helper.filters import CustomFilters
from bot.helper.telegram_helper.bot_commands import BotCommands
from bot.helper.ext_utils.bot_utils import get_readable_file_size
from bot.helper.telegram_helper.button_build import ButtonMaker

PLUGINS: List[str] = []
SITES: Optional[Dict[str, str]] = None
TELEGRAPH_LIMIT = 300

def initiate_search_tools() -> None:
    """Initialize search tools by fetching plugins and sites."""
    qbclient = get_client()
    qb_plugins = qbclient.search_plugins()
    if SEARCH_PLUGINS := config_dict.get('SEARCH_PLUGINS'):
        PLUGINS.clear()
        src_plugins = eval(SEARCH_PLUGINS)
        if qb_plugins:
            for plugin in qb_plugins:
                qbclient.search_uninstall_plugin(names=plugin['name'])
        qbclient.search_install_plugin(src_plugins)
        qbclient.auth_log_out()
    elif qb_plugins:
        for plugin in qb_plugins:
            qbclient.search_uninstall_plugin(names=plugin['name'])
    qbclient.auth_log_out()

    if SEARCH_API_LINK := config_dict.get('SEARCH_API_LINK'):
        try:
            response = requests.get(f'{SEARCH_API_LINK}/api/v1/sites')
            response.raise_for_status()
            SITES = {str(site): str(site).capitalize() for site in response.json()['supported_sites']}
            SITES['all'] = 'All'
        except Exception as e:
            LOGGER.error("Can't fetching sites from SEARCH_API_LINK make sure use latest version of API")
            SITES = None

def torser(update: Any, context: Any) -> None:
    """Handle the /search command."""
    user_id = update.message.from_user.id
    buttons = ButtonMaker()
    SEARCH_PLUGINS = config_dict.get('SEARCH_PLUGINS')

    if SITES is None and not SEARCH_PLUGINS:
        sendMessage("No API link or search PLUGINS added for this function", context.bot, update.message)
    elif len(context.args) == 0 and SITES is None:
        sendMessage("Send a search key along with command", context.bot, update.message)
    elif len(context.args) == 0:
        buttons.sbutton('Trending', f"torser {user_id} apitrend")
        buttons.sbutton('Recent', f"torser {user_id} apirecent")
        buttons.sbutton("Cancel", f"torser {user_id} cancel")
        button = buttons.build_menu(2)
        sendMessage("Send a search key along with command", context.bot, update.message, button)
    elif SITES is not None and SEARCH_PLUGINS:
        buttons.sbutton('Api', f"torser {user_id} apisearch")
        buttons.sbutton('Plugins', f"torser {user_id} plugin")
        buttons.sbutton("Cancel", f"torser {user_id} cancel")
        button = buttons.build_menu(2)
        sendMessage('Choose tool to search:', context.bot, update.message, button)
    elif SITES is not None:
        button = __api_buttons(user_id, "apisearch")
        sendMessage('Choose site to search | API:', context.bot, update.message, button)
    else:
        button = __plugin_buttons(user_id)
        sendMessage('Choose site to search | Plugins:', context.bot, update.message, button)

def torserbut(update: Any, context: Any) -> None:
    """Handle the /search command callback queries."""
    query = update.callback_query
    user_id = query.from_user.id
    message = query.message
    key = message.reply_to_message.text.split(maxsplit=1)
    key = key[1].strip() if len(key) > 1 else None
    data = query.data
    data = data.split()

    if user_id != int(data[1]):
        query.answer(text="Not Yours!", show_alert=True)
    elif data[2].startswith('api'):
        query.answer()
        button = __api_buttons(user_id, data[2])
        editMessage('Choose site:', message, button)
    elif data[2] == 'plugin':
        query.answer()
        button = __plugin_buttons(user_id)
        editMessage('Choose site:', message, button)
    elif data[2] != "cancel":
        query.answer()
        site = data[2]
        method = data[3]

        if method.startswith('api'):
            if key is None:
                if method == 'apirecent':
                    endpoint = 'Recent'
                elif method == 'apitrend':
                    endpoint = 'Trending'
                editMessage(f"<b>Listing {endpoint} Items...\nTorrent Site:- <i>{SITES.get(site)}</i></b>", message)
            else:
                editMessage(f"<b>Searching for <i>{key}</i>\nTorrent Site:- <i>{SITES.get(site)}</i></b>", message)
        else:
            editMessage(f"<b>Searching for <i>{key}</i>\nTorrent Site:- <i>{site.capitalize()}</i></b>", message)

        Thread(target=__search, args=(key, site, message, method)).start()
    else:
        query.answer()
        editMessage("Search has been canceled!", message)

def __search(key: str, site: str, message: Any, method: str) -> None:
    # ... (rest of the function)

def __api_buttons(user_id: int, method: str) -> str:
    # ... (rest of the function)

def __plugin_buttons(user_id: int) -> str:
    # ... (rest of the function)

initiate_search_tools()

torser_handler = CommandHandler(BotCommands.SearchCommand, torser,
                                filters=CustomFilters.authorized_chat | CustomFilters.authorized_user)
torserbut_handler = CallbackQueryHandler(torserbut, pattern="torser")

dispatcher.add_handler(torser_handler)
dispatcher.add_handler(torserbut_handler)
