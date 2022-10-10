from telegram import Message
import re
import requests
from bs4 import BeautifulSoup
from telegram.ext import CommandHandler
from bot import LOGGER, dispatcher, PAID_SERVICE, PAID_USERS, OWNER_ID
from bot.helper.telegram_helper.filters import CustomFilters
from bot.helper.telegram_helper.bot_commands import BotCommands
from bot.helper.telegram_helper.message_utils import sendMessage


def scrape(update, context):
    user_id_ = update.message.from_user.id
    if PAID_SERVICE is True:
        if user_id_ in PAID_USERS and OWNER_ID:
            message:Message = update.effective_message
            link = None
            if message.reply_to_message: link = message.reply_to_message.text
            else:
                link = message.text.split(' ', 1)
                if len(link) != 2:
                    help_msg = "<b>Send link after command:</b>"
                    help_msg += f"\n<code>/{BotCommands.ScrapeCommand}" + " {link}" + "</code>"
                    help_msg += "\n<b>By replying to message (including link):</b>"
                    help_msg += f"\n<code>/{BotCommands.ScrapeCommand}" + " {message}" + "</code>"
                    return sendMessage(help_msg, context.bot, update.message)
                link = link[1]
            try: link = re.match(r"((http|https)\:\/\/)?[a-zA-Z0-9\.\/\?\:@\-_=#]+\.([a-zA-Z]){2,6}([a-zA-Z0-9\.\&\/\?\:@\-_=#])*", link)[0]
            except TypeError: return sendMessage('Not a valid link.', context.bot, update)
            links = []
            res = requests.get(link)
            soup = BeautifulSoup(res.text, 'html.parser')
            x = soup.select('a[href^="magnet:?xt=urn:btih:"]')
            for a in x:
                links.append(a['href'])
            for o in links:
#                 print(o)
                sent = sendMessage(f"{o}", context.bot, update.message)
        else:
            sendMessage(f"Buy Paid Service to use Feature.", context.bot, update.message)
    else:
        message:Message = update.effective_message
        link = None
        if message.reply_to_message: link = message.reply_to_message.text
        else:
            link = message.text.split(' ', 1)
            if len(link) != 2:
                help_msg = "<b>Send link after command:</b>"
                help_msg += f"\n<code>/{BotCommands.ScrapeCommand}" + " {link}" + "</code>"
                help_msg += "\n<b>By replying to message (including link):</b>"
                help_msg += f"\n<code>/{BotCommands.ScrapeCommand}" + " {message}" + "</code>"
                return sendMessage(help_msg, context.bot, update.message)
            link = link[1]
        try: link = re.match(r"((http|https)\:\/\/)?[a-zA-Z0-9\.\/\?\:@\-_=#]+\.([a-zA-Z]){2,6}([a-zA-Z0-9\.\&\/\?\:@\-_=#])*", link)[0]
        except TypeError: return sendMessage('Not a valid link.', context.bot, update)
        links = []
        res = requests.get(link)
        soup = BeautifulSoup(res.text, 'html.parser')
        x = soup.select('a[href^="magnet:?xt=urn:btih:"]')
        for a in x:
            links.append(a['href'])
        for o in links:
#                print(o)
            sent = sendMessage(f"{o}", context.bot, update.message)



scrape_handler = CommandHandler(BotCommands.ScrapeCommand, scrape,
                                filters=CustomFilters.authorized_chat | CustomFilters.authorized_user, run_async=True)


dispatcher.add_handler(scrape_handler)