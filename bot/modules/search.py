from requests import get as rget
from html import escape
from urllib.parse import quote
from pyrogram.types import CallbackQuery, Message
from pyrogram import filters, Client

from bot import bot, LOGGER, config_dict, get_client
from bot.helper.telegram_helper.message_utils import editMessage, sendMessage
from bot.helper.ext_utils.telegraph_helper import telegraph
from bot.helper.telegram_helper.filters import CustomFilters
from bot.helper.telegram_helper.bot_commands import BotCommands
from bot.helper.ext_utils.bot_utils import get_readable_file_size
from bot.helper.telegram_helper.button_build import ButtonMaker

PLUGINS = []
SITES = None
TELEGRAPH_LIMIT = 300


def initiate_search_tools():
    qbclient = get_client()
    qb_plugins = qbclient.search_plugins()
    if SEARCH_PLUGINS := config_dict['SEARCH_PLUGINS']:
        globals()['PLUGINS'] = []
        src_plugins = eval(SEARCH_PLUGINS)
        if qb_plugins:
            for plugin in qb_plugins:
                qbclient.search_uninstall_plugin(names=plugin['name'])
        qbclient.search_install_plugin(src_plugins)
        qbclient.auth_log_out()
    elif qb_plugins:
        for plugin in qb_plugins:
            qbclient.search_uninstall_plugin(names=plugin['name'])
        globals()['PLUGINS'] = []
    qbclient.auth_log_out()

    if SEARCH_API_LINK := config_dict['SEARCH_API_LINK']:
        global SITES
        try:
            res = rget(f'{SEARCH_API_LINK}/api/v1/sites').json()
            SITES = {str(site): str(site).capitalize()
                     for site in res['supported_sites']}
            SITES['all'] = 'All'
        except Exception as e:
            LOGGER.error(
                "Can't fetching sites from SEARCH_API_LINK make sure use latest version of API")
            SITES = None


@bot.on_message(filters.command(BotCommands.SearchCommand) & (CustomFilters.authorized_chat | CustomFilters.authorized_user))
async def torser(c: Client, message: Message):
    user_id = message.from_user.id
    args = message.text.split()
    buttons = ButtonMaker()
    SEARCH_PLUGINS = config_dict['SEARCH_PLUGINS']
    if SITES is None and not SEARCH_PLUGINS:
        await sendMessage("No API link or search PLUGINS added for this function", c, message)
    elif len(args) == 0 and SITES is None:
        await sendMessage("Send a search key along with command", c, message)
    elif len(args) == 0:
        buttons.sbutton('Trending', f"torser {user_id} apitrend")
        buttons.sbutton('Recent', f"torser {user_id} apirecent")
        buttons.sbutton("Cancel", f"torser {user_id} cancel")
        button = buttons.build_menu(2)
        await sendMessage("Send a search key along with command", c, message, button)
    elif SITES is not None and SEARCH_PLUGINS:
        buttons.sbutton('Api', f"torser {user_id} apisearch")
        buttons.sbutton('Plugins', f"torser {user_id} plugin")
        buttons.sbutton("Cancel", f"torser {user_id} cancel")
        button = buttons.build_menu(2)
        await sendMessage('Choose tool to search:', c, message, button)
    elif SITES is not None:
        button = __api_buttons(user_id, "apisearch")
        await sendMessage('Choose site to search | API:', c, message, button)
    else:
        button = __plugin_buttons(user_id)
        await sendMessage('Choose site to search | Plugins:', c, message, button)


@bot.on_callback_query(filters.regex(r"^torser"))
async def torserbut(c: Client, query: CallbackQuery):
    user_id = query.from_user.id
    message = query.message
    key = message.reply_to_message.text.split(maxsplit=1)
    key = key[1].strip() if len(key) > 1 else None
    data = query.data
    data = data.split()
    if user_id != int(data[1]):
        await query.answer(text="Not Yours!", show_alert=True)
    elif data[2].startswith('api'):
        await query.answer()
        button = __api_buttons(user_id, data[2])
        await editMessage('Choose site:', message, button)
    elif data[2] == 'plugin':
        await query.answer()
        button = __plugin_buttons(user_id)
        await editMessage('Choose site:', message, button)
    elif data[2] != "cancel":
        await query.answer()
        site = data[2]
        method = data[3]
        if method.startswith('api'):
            if key is None:
                if method == 'apirecent':
                    endpoint = 'Recent'
                elif method == 'apitrend':
                    endpoint = 'Trending'
                await editMessage(f"<b>Listing {endpoint} Items...\nTorrent Site:- <i>{SITES.get(site)}</i></b>", message)
            else:
                await editMessage(f"<b>Searching for <i>{key}</i>\nTorrent Site:- <i>{SITES.get(site)}</i></b>", message)
        else:
            await editMessage(f"<b>Searching for <i>{key}</i>\nTorrent Site:- <i>{site.capitalize()}</i></b>", message)
        await __search(key, site, message, method)
    else:
        await query.answer()
        await editMessage("Search has been canceled!", message)


async def __search(key, site, message, method):
    if method.startswith('api'):
        SEARCH_API_LINK = config_dict['SEARCH_API_LINK']
        SEARCH_LIMIT = config_dict['SEARCH_LIMIT']
        if method == 'apisearch':
            LOGGER.info(f"API Searching: {key} from {site}")
            if site == 'all':
                api = f"{SEARCH_API_LINK}/api/v1/all/search?query={key}&limit={SEARCH_LIMIT}"
            else:
                api = f"{SEARCH_API_LINK}/api/v1/search?site={site}&query={key}&limit={SEARCH_LIMIT}"
        elif method == 'apitrend':
            LOGGER.info(f"API Trending from {site}")
            if site == 'all':
                api = f"{SEARCH_API_LINK}/api/v1/all/trending?limit={SEARCH_LIMIT}"
            else:
                api = f"{SEARCH_API_LINK}/api/v1/trending?site={site}&limit={SEARCH_LIMIT}"
        elif method == 'apirecent':
            LOGGER.info(f"API Recent from {site}")
            if site == 'all':
                api = f"{SEARCH_API_LINK}/api/v1/all/recent?limit={SEARCH_LIMIT}"
            else:
                api = f"{SEARCH_API_LINK}/api/v1/recent?site={site}&limit={SEARCH_LIMIT}"
        try:
            resp = rget(api)
            search_results = resp.json()
            if 'error' in search_results or search_results['total'] == 0:
                return await editMessage(f"No result found for <i>{key}</i>\nTorrent Site:- <i>{SITES.get(site)}</i>", message)
            msg = f"<b>Found {min(search_results['total'], TELEGRAPH_LIMIT)}</b>"
            if method == 'apitrend':
                msg += f" <b>trending result(s)\nTorrent Site:- <i>{SITES.get(site)}</i></b>"
            elif method == 'apirecent':
                msg += f" <b>recent result(s)\nTorrent Site:- <i>{SITES.get(site)}</i></b>"
            else:
                msg += f" <b>result(s) for <i>{key}</i>\nTorrent Site:- <i>{SITES.get(site)}</i></b>"
            search_results = search_results['data']
        except Exception as e:
            return await editMessage(str(e), message)
    else:
        LOGGER.info(f"PLUGINS Searching: {key} from {site}")
        client = get_client()
        search = client.search_start(pattern=key, plugins=site, category='all')
        search_id = search.id
        while True:
            result_status = client.search_status(search_id=search_id)
            status = result_status[0].status
            if status != 'Running':
                break
        dict_search_results = client.search_results(search_id=search_id)
        search_results = dict_search_results.results
        total_results = dict_search_results.total
        if total_results == 0:
            return await editMessage(f"No result found for <i>{key}</i>\nTorrent Site:- <i>{site.capitalize()}</i>", message)
        msg = f"<b>Found {min(total_results, TELEGRAPH_LIMIT)}</b>"
        msg += f" <b>result(s) for <i>{key}</i>\nTorrent Site:- <i>{site.capitalize()}</i></b>"
    link = await __getResult(search_results, key, message, method)
    buttons = ButtonMaker()
    buttons.buildbutton("🔎 VIEW", link)
    button = buttons.build_menu(1)
    await editMessage(msg, message, button)
    if not method.startswith('api'):
        client.search_delete(search_id=search_id)


async def __getResult(search_results, key, message, method):
    telegraph_content = []
    if method == 'apirecent':
        msg = "<h4>API Recent Results</h4>"
    elif method == 'apisearch':
        msg = f"<h4>API Search Result(s) For {key}</h4>"
    elif method == 'apitrend':
        msg = "<h4>API Trending Results</h4>"
    else:
        msg = f"<h4>PLUGINS Search Result(s) For {key}</h4>"
    for index, result in enumerate(search_results, start=1):
        if method.startswith('api'):
            try:
                if 'name' in result.keys():
                    msg += f"<code><a href='{result['url']}'>{escape(result['name'])}</a></code><br>"
                if 'torrents' in result.keys():
                    for subres in result['torrents']:
                        msg += f"<b>Quality: </b>{subres['quality']} | <b>Type: </b>{subres['type']} | "
                        msg += f"<b>Size: </b>{subres['size']}<br>"
                        if 'torrent' in subres.keys():
                            msg += f"<a href='{subres['torrent']}'>Direct Link</a><br>"
                        elif 'magnet' in subres.keys():
                            msg += f"<b>Share Magnet to</b> "
                            msg += f"<a href='http://t.me/share/url?url={subres['magnet']}'>Telegram</a><br>"
                    msg += '<br>'
                else:
                    msg += f"<b>Size: </b>{result['size']}<br>"
                    try:
                        msg += f"<b>Seeders: </b>{result['seeders']} | <b>Leechers: </b>{result['leechers']}<br>"
                    except:
                        pass
                    if 'torrent' in result.keys():
                        msg += f"<a href='{result['torrent']}'>Direct Link</a><br><br>"
                    elif 'magnet' in result.keys():
                        msg += f"<b>Share Magnet to</b> "
                        msg += f"<a href='http://t.me/share/url?url={quote(result['magnet'])}'>Telegram</a><br><br>"
                    else:
                        msg += '<br>'
            except:
                continue
        else:
            msg += f"<a href='{result.descrLink}'>{escape(result.fileName)}</a><br>"
            msg += f"<b>Size: </b>{get_readable_file_size(result.fileSize)}<br>"
            msg += f"<b>Seeders: </b>{result.nbSeeders} | <b>Leechers: </b>{result.nbLeechers}<br>"
            link = result.fileUrl
            if link.startswith('magnet:'):
                msg += f"<b>Share Magnet to</b> <a href='http://t.me/share/url?url={quote(link)}'>Telegram</a><br><br>"
            else:
                msg += f"<a href='{link}'>Direct Link</a><br><br>"

        if len(msg.encode('utf-8')) > 39000:
            telegraph_content.append(msg)
            msg = ""

        if index == TELEGRAPH_LIMIT:
            break

    if msg != "":
        telegraph_content.append(msg)

    await editMessage(f"<b>Creating</b> {len(telegraph_content)} <b>Telegraph pages.</b>", message)
    path = [telegraph.create_page(title=f"{config_dict['TITLE_NAME']}",
                                  content=content)["path"] for content in telegraph_content]
    if len(path) > 1:
        await editMessage(f"<b>Editing</b> {len(telegraph_content)} <b>Telegraph pages.</b>", message)
        telegraph.edit_telegraph(path, telegraph_content)
    return f"https://te.legra.ph/{path[0]}"


def __api_buttons(user_id, method):
    buttons = ButtonMaker()
    for data, name in SITES.items():
        buttons.sbutton(name, f"torser {user_id} {data} {method}")
    buttons.sbutton("Cancel", f"torser {user_id} cancel")
    return buttons.build_menu(2)


def __plugin_buttons(user_id):
    buttons = ButtonMaker()
    if not PLUGINS:
        qbclient = get_client()
        pl = qbclient.search_plugins()
        for name in pl:
            PLUGINS.append(name['name'])
        qbclient.auth_log_out()
    for siteName in PLUGINS:
        buttons.sbutton(siteName.capitalize(),
                        f"torser {user_id} {siteName} plugin")
    buttons.sbutton('All', f"torser {user_id} all plugin")
    buttons.sbutton("Cancel", f"torser {user_id} cancel")
    return buttons.build_menu(2)


initiate_search_tools()

