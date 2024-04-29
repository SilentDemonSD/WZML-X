import typing
from pyrogram.handlers import MessageHandler, CallbackQueryHandler
from pyrogram.filters import command, regex
from pyrogram.context import AsyncContextManager
from html import escape
from urllib.parse import quote
from bot.helper.telegram_helper.message_utils import editMessage, sendMessage
from bot.helper.ext_utils.telegraph_helper import telegraph
from bot.helper.telegram_helper.filters import CustomFilters
from bot.helper.telegram_helper.bot_commands import BotCommands
from bot.helper.ext_utils.bot_utils import get_readable_file_size, sync_to_async, new_task, checking_access
from bot.helper.telegram_helper.button_build import ButtonMaker

PLUGINS: list = []
SITES: dict = None
TELEGRAPH_LIMIT: int = 300


async def initiate_search_tools() -> None:
    """Initialize search tools."""
    async with AsyncContextManager(get_client()) as qbclient:
        qb_plugins = await sync_to_async(qbclient.search_plugins)
        if SEARCH_PLUGINS := config_dict.get('SEARCH_PLUGINS'):
            globals()['PLUGINS'] = []
            src_plugins = eval(SEARCH_PLUGINS)
            if qb_plugins:
                names = [plugin['name'] for plugin in qb_plugins]
                await sync_to_async(qbclient.search_uninstall_plugin, names=names)
            await sync_to_async(qbclient.search_install_plugin, src_plugins)
        elif qb_plugins:
            for plugin in qb_plugins:
                await sync_to_async(qbclient.search_uninstall_plugin, names=plugin['name'])
            globals()['PLUGINS'] = []
        await sync_to_async(qbclient.auth_log_out)

        if SEARCH_API_LINK := config_dict.get('SEARCH_API_LINK'):
            global SITES
            try:
                async with AsyncContextManager(ClientSession(trust_env=True)) as c:
                    async with c.get(f'{SEARCH_API_LINK}/api/v1/sites') as res:
                        data = await res.json()
                SITES = {str(site): str(site).capitalize() for site in data['supported_sites']}
                SITES['all'] = 'All'
            except Exception as e:
                LOGGER.error(
                    f"{e} Can't fetching sites from SEARCH_API_LINK make sure use latest version of API")
                SITES = None


async def __search(key: str, site: str, message, method: str) -> None:
    ...

