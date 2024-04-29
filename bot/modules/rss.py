from feedparser import parse as feedparse
from time import sleep
from typing import Dict, Any, List, Tuple, Union
from telegram.ext import CommandHandler, CallbackQueryHandler
from threading import Lock, Thread

from bot import dispatcher, job_queue, rss_dict, LOGGER, DATABASE_URL, config_dict, RSS_DELAY, RSS_CHAT_ID
from bot.helper.telegram_helper.message_utils import send_message, edit_message, send_message, auto_delete_message, send_rss
from bot.helper.telegram_helper.filters import CustomFilters
from bot.helper.telegram_helper.bot_commands import BotCommands
from bot.helper.ext_utils.db_handler import DbManger
from bot.helper.telegram_helper.button_build import ButtonMaker

rss_dict_lock = Lock()

def rss_list(update: telegram.Update, context: telegram.ext.CallbackContext) -> None:
    """List all subscribed RSS feeds."""
    if len(rss_dict) > 0:
        list_feed = "<b>Your subscriptions: </b>\n\n"
        for title, data in list(rss_dict.items()):
            list_feed += f"<b>Title:</b> <code>{title}</code>\n<b>Feed Url: </b><code>{data['link']}</code>\n\n"
        send_message(list_feed, context.bot, update.message)
    else:
        send_message("No subscriptions.", context.bot, update.message)

def rss_get(update: telegram.Update, context: telegram.ext.CallbackContext) -> None:
    """Get items from a specific RSS feed."""
    try:
        title = context.args[0]
        count = int(context.args[1])
        data = rss_dict.get(title)
        if data is not None and count > 0:
            try:
                msg = send_message(f"Getting the last <b>{count}</b> item(s) from {title}", context.bot, update.message)
                rss_d = feedparse(data['link'])
                item_info = ""
                for item_num in range(count):
                    try:
                        link = rss_d.entries[item_num]['links'][1]['href']
                    except IndexError:
                        link = rss_d.entries[item_num]['link']
                    item_info += f"<b>Name: </b><code>{rss_d.entries[item_num]['title'].replace('>', '').replace('<', '')}</code>\n"
                    item_info += f"<b>Link: </b><code>{link}</code>\n\n"
                edit_message(item_info, msg)
            except IndexError as e:
                LOGGER.error(str(e))
                edit_message("Parse depth exceeded. Try again with a lower value.", msg)
            except Exception as e:
                LOGGER.error(str(e))
                edit_message(str(e), msg)
        else:
            send_message("Enter a valid title/value.", context.bot, update.message)
    except (IndexError, ValueError):
        send_message(f"Use this format to fetch:\n/{BotCommands.RssGetCommand[0]} Title value", context.bot, update.message)

def rss_sub(update: telegram.Update, context: telegram.ext.CallbackContext) -> None:
    """Subscribe to a new RSS feed."""
    try:
        args = update.message.text.split(maxsplit=3)
        title = args[1].strip()
        feed_link = args[2].strip()
        f_lists = []
        filters = None

        if len(args) == 4:
            filters = args[3].lstrip().lower()
            if filters.startswith('f: '):
                filters = filters.split('f: ', 1)[1]
                filters_list = filters.split('|')
                for x in filters_list:
                   y = x.split(' or ')
                   f_lists.append(y)
            else:
                filters = None

        exists = rss_dict.get(title)
        if exists:
            return send_message("This title already subscribed! Choose another title!", context.bot, update.message)
        try:
            rss_d = feedparse(feed_link)
            sub_msg = "<b>Subscribed!</b>"
            sub_msg += f"\n\n<b>Title: </b><code>{title}</code>\n<b>Feed Url: </b>{feed_link}"
            sub_msg += f"\n\n<b>latest record for </b>{rss_d.feed.title}:"
            sub_msg += f"\n\n<b>Name: </b><code>{rss_d.entries[0]['title'].replace('>', '').replace('<', '')}</code>"
            try:
                link = rss_d.entries[0]['links'][1]['href']
            except IndexError:
                link = rss_d.entries[0]['link']
            sub_msg += f"\n\n<b>Link: </b><code>{link}</code>"
            sub_msg += f"\n\n<b>Filters: </b><code>{filters}</code>"
            last_link = rss_d.entries[0]['link']
            last_title = rss_d.entries[0]['title']
            with rss_dict_lock:
                if len(rss_dict) == 0:
                    rss_job.enabled = True
                rss_dict[title] = {'link': feed_link, 'last_feed': last_link, 'last_title': last_title, 'filters': f_lists}
            DbManger().rss_update(title)
            send_message(sub_msg, context.bot, update.message)
            LOGGER.info(f"Rss Feed Added: {title} - {feed_link} - {filters}")
        except (IndexError, AttributeError) as e:
            msg = "The link doesn't seem to be a RSS feed or it's region-blocked!"
            send_message(msg + '\nError: ' + str(e), context.bot, update.message)
        except Exception as e:
            send_message(str(e), context.bot, update.message)
    except IndexError:
        msg = f"Use this format to add feed url:\n/{BotCommands.RssSubCommand[0]} Title https://www.rss-url.com"
        msg += " f: 1080 or 720 or 144p|mkv or mp4|hevc (optional)\n\nThis filter will parse links that it's titles"
        msg += " contains `(1080 or 720 or 144p) and (mkv or mp4) and hevc` words. You can add whatever you want.\n\n"
        msg += "Another example: f:  1080  or 720p|.web. or .webrip.|hvec or x264. This will parse titles that contains"
        msg += " ( 1080  or 720p) and (.web. or .webrip.) and (hvec or x264). I have added space before and after 1080"
        msg += " to avoid wrong matching. If this `10805695` number in title it will match 1080 if added 1080 without"
        msg += " spaces after it."
        msg += "\n\nFilters Notes:\n\n1. | means and.\n\n2. Add `or` between similar keys, you can add it"
        msg += " between qualities or between extensions, so don't add filter like this f: 1080|mp4 or 720|web"
        msg += " because this will parse 10805695 and (mp4 or 720) and web ... not (1080 and mp4) or (720 and web)."
        msg += "\n\n3. You can add `or` and `|` as much as you want."
        msg += "\n\n4. Take look on title if it has static special character after or before the qualities or extensions"
        msg += " or whatever and use them in filter to avoid wrong match"
        send_message(msg, context.bot, update.message)

def rss_unsub(update: telegram.Update, context: telegram.ext.CallbackContext) -> None:
    """Unsubscribe from an RSS feed."""
    try:
        title = context.args[0]
        exists = rss_dict.get(title)
        if not exists:
            msg = "Rss link not exists! Nothing removed!"
            send_message(msg, context.bot, update.message)
        else:
            DbManger().rss_delete(title)
            with rss_dict_lock:
                del rss_dict[title]
            send_message(f"Rss link with Title: <code>{title}</code> has been removed!", context.bot, update.message)
            LOGGER.info(f"Rss link with Title: {title} has been removed!")
    except IndexError:
        send_message(f"Use this format to remove feed url:\n/{BotCommands.RssUnSubCommand[0]} Title", context.bot, update.message)

def rss_settings(update: telegram.Update, context: telegram.ext.CallbackContext) -> None:
    """Show RSS settings."""
    buttons = ButtonMaker()
    buttons.sbutton("Unsubscribe All", "rss unsuball")
    if rss_job.enabled:
        buttons.sbutton("Pause", "rss pause")
    else:
        buttons.sbutton("Start", "rss start")
    if config_dict['AUTO_DELETE_MESSAGE_DURATION'] == -1:
        buttons.sbutton("Close", "rss close")
    button = buttons.build_menu(1)
    setting = send_message('Rss Settings', context.bot, update.message, button)
    Thread(target=auto_delete_message, args=(context.bot, update.message, setting)).start()

def rss_set_update(update: telegram.Update, context: telegram.ext.CallbackContext) -> None:
    """Handle RSS settings callback queries."""
    query = update.callback_query
    user_id = query.from_user.id
    msg = query.message
    data = query.data
    data = data.split()
    if not CustomFilters.owner_query(user_id):
        query.answer(text="You don't have permission to use these buttons!", show_alert=True)
    elif data[1] == 'unsuball':
        query.answer()
        if len(rss_dict) > 0:
            DbManger().trunc_table('rss')
            with rss_dict_lock:
                rss_dict.clear()
            rss_job.enabled = False
            edit_message("All Rss Subscriptions have been removed.", msg)
            LOGGER.info("All Rss Subscriptions have been removed.")
        else:
            edit_message("No subscriptions to remove!", msg)
    elif data[1] == 'pause':
        query.answer()
        rss_job.enabled = False
        edit_message("Rss Paused", msg)
        LOGGER.info("Rss Paused")
    elif data[1] == 'start':
        query.answer()
        rss_job.enabled = True
        edit_message("Rss Started", msg)
        LOGGER.info("Rss Started")
    else:
        query.answer()
        query.message.delete()
        query.message.reply_to_message.delete()

def rss_monitor(context: telegram.ext.CallbackContext) -> None:
    """Monitor RSS feeds."""
    if not job_queue or not rss_dict:
        return
    with rss_dict_lock:
        if len(rss_dict) == 0:
            rss_job.enabled = False
            return
    for title, data in list(rss_dict.items()):
        try:
            rss_d = feedparse(data['link'])
            last_link = rss_d.entries[0]['link']
            last_title = rss_d.entries[0]['title']
            if data['last_feed'] == last_link or data['last_title'] == last_title:
                continue
            feed_count = 0
            while True:
                try:
                    if data['last_feed'] == rss_d.entries[feed_count]['link'] or \
                       data['last_title'] == rss_d.entries[feed_count]['title']:
                        break
                except IndexError:
                    LOGGER.warning(f"Reached Max index no. {feed_count} for this feed: {title}. Maybe you need to use less RSS_DELAY to not miss some torrents")
                    break
                parse = True
                for flist in data['filters']:
                    if all(x not in str(rss_d.entries[feed_count]['title']).lower() for x in flist):
                        parse = False
                        feed_count += 1
                        break
                if not parse:
                    continue
                try:
                    url = rss_d.entries[feed_count]['links'][1]['href']
                except IndexError:
                    url = rss_d.entries[feed_count]['link']
                if RSS_COMMAND := config_dict['RSS_COMMAND']:
                    feed_msg = f"{RSS_COMMAND} {url}"
                else:
                    feed_msg = f"<b>Name: </b><code>{rss_d.entries[feed_count]['title'].replace('>', '').replace('<', '')}</code>\n\n"
                    feed_msg += f"<b>Link: </b><code>{url}</code>"
                send_rss(feed_msg, context.bot)
                feed_count += 1
                sleep(5)
            with rss_dict_lock:
                if title not in rss_dict:
                    continue
                rss_dict[title].update({'last_feed': last_link, 'last_title': last_title})
            DbManger().rss_update(title)
            LOGGER.info(f"Feed Name: {title}")
            LOGGER.info(f"Last item: {last_link}")
        except Exception as e:
            LOGGER.error(f"{e} Feed Name: {title} - Feed Link: {data['link']}")
            continue

if DATABASE_URL and RSS_CHAT_ID and RSS_DELAY and job_queue and rss_dict:
    rss_list_handler = CommandHandler(BotCommands.RssListCommand, rss_list,
                                      filters=CustomFilters.owner_filter | CustomFilters.sudo_user)
    rss_get_handler = CommandHandler(BotCommands.RssGetCommand, rss_get,
                                      filters=CustomFilters.owner_filter | CustomFilters.sudo_user)
    rss_sub_handler = CommandHandler(BotCommands.RssSubCommand, rss_sub,
                                      filters=CustomFilters.owner_filter | CustomFilters.sudo_user)
    rss_unsub_handler = CommandHandler(BotCommands.RssUnSubCommand, rss_unsub,
                                      filters=CustomFilters.owner_filter | CustomFilters.sudo_user)
    rss_settings_handler = CommandHandler(BotCommands.RssSettingsCommand, rss_settings,
                
