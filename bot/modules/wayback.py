import re
import random
from typing import Optional

import requests
from telegram import Message, Bot, User, ParseMode
from telegram.ext import CommandHandler, Filters, CallbackContext
from bot.helper.ext_utils.shortenurl import short_url
from bot.helper.telegram_helper.filters import CustomFilters
from bot.helper.telegram_helper.bot_commands import BotCommands
from bot.helper.telegram_helper.message_utils import (
    editMessage,
    sendMessage,
)
from bot.logger import LOGGER

def get_random_user_agent() -> str:
    agents = [
        "Mozilla/5.0 (Windows NT 6.0; WOW64) AppleWebKit/534.24 (KHTML, like Gecko) Chrome/11.0.699.0 Safari/534.24",
        "Mozilla/5.0 (Windows NT 6.0; WOW64) AppleWebKit/535.1 (KHTML, like Gecko) Chrome/13.0.782.220 Safari/535.1",
        "Mozilla/5.0 (Windows NT 6.0; WOW64) AppleWebKit/535.1 (KHTML, like Gecko) Chrome/13.0.782.41 Safari/535.1",
        "Mozilla/5.0 (Windows NT 6.0; WOW64) AppleWebKit/535.11 (KHTML, like Gecko) Chrome/17.0.963.56 Safari/535.11",
        "Mozilla/5.0 (X11; CrOS i686 0.13.507) AppleWebKit/534.35 (KHTML, like Gecko) Chrome/13.0.763.0 Safari/534.35",
        "Mozilla/5.0 (X11; CrOS i686 0.13.587) AppleWebKit/535.1 (KHTML, like Gecko) Chrome/13.0.782.14 Safari/535.1",
        "Mozilla/5.0 (X11; CrOS i686 1193.158.0) AppleWebKit/535.7 (KHTML, like Gecko) Chrome/16.0.912.75 Safari/535.7",
        "Mozilla/5.0 (X11; CrOS i686 12.0.742.91) AppleWebKit/534.30 (KHTML, like Gecko) Chrome/12.0.742.93 Safari/534.30",
        "Mozilla/5.0 (X11; CrOS i686 12.433.109) AppleWebKit/534.30 (KHTML, like Gecko) Chrome/12.0.742.93 Safari/534.30",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/534.24 (KHTML, like Gecko) Chrome/11.0.696.34 Safari/534.24",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/534.24 (KHTML, like Gecko) Ubuntu/10.04 Chromium/11.0.696.34 Chrome/11.0.696.34 Safari/534.24",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/534.24 (KHTML, like Gecko) Ubuntu/10.10 Chromium/12.0.703.0 Chrome/12.0.703.0 Safari/534.24",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/535.21 (KHTML, like Gecko) Chrome/19.0.1042.0 Safari/535.21",
        "Opera/9.80 (Windows NT 5.1; U; sk) Presto/2.5.22 Version/10.50",
        "Opera/9.80 (Windows NT 5.1; U; zh-sg) Presto/2.9.181 Version/12.00",
        "Opera/9.80 (Windows NT 5.1; U; zh-tw) Presto/2.8.131 Version/11.10",
        "Opera/9.80 (Windows NT 5.1; U;) Presto/2.7.62 Version/11.01",
        "Opera/9.80 (Windows NT 5.2; U; en) Presto/2.6.30 Version/10.63",
        "Opera/9.80 (Windows NT 5.2; U; ru) Presto/2.5.22 Version/10.51",
        "Opera/9.80 (Windows NT 5.2; U; ru) Presto/2.6.30 Version/10.61",
        "Opera/9.80 (Windows NT 5.2; U; ru) Presto/2.7.62 Version/11.01",
        "Opera/9.80 (X11; Linux x86_64; U; pl) Presto/2.7.62 Version/11.00",
        "Opera/9.80 (X11; Linux x86_64; U; Ubuntu/10.10 (maverick); pl) Presto/2.7.62 Version/11.01",
        "Opera/9.80 (X11; U; Linux i686; en-US; rv:1.9.2.3) Presto/2.2.15 Version/10.10",
        "Mozilla/5.0 (Linux; Android 10; SM-G975F) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/81.0.4044.117 Mobile Safari/537.36"
    ]
    return random.choice(agents)

async def wayback(update: Message, context: CallbackContext) -> None:
    args = context.args
    user = update.effective_user
    bot = context.bot

    if not args:
        await sendMessage(
            (
                f"<b>Usage:</b>\n"
                f"<code>{BotCommands.WayBackCommand} {link}</code>\n"
                f"<b>OR</b>\n"
                f"<code>{BotCommands.WayBackCommand}</code> <b>reply to a message containing a link"
            ),
            bot,
            update,
            parse_mode=ParseMode.HTML,
        )
        return

    link = args[0]

    if not re.match(r"((http|https)\:\/\/)?[a-zA-Z0-9\.\/\?\:@\-_=#]+\.([a-zA-Z]){2,6}([a-zA-Z0-9\.\&\/\?\:@\-_=#])*", link):
        await sendMessage("Not a valid link for wayback.", bot, update)
        return

    await sendMessage("Running WayBack. Wait about 20 secs.", bot, update)
    archive_url = await save_webpage(link, user.id)

    if archive_url:
        await editMessage(
            f"Saved webpage: {short_url(archive_url, user.id)}",
            update.message,
        )
    else:
        await editMessage("Cannot archive. Try again later.", update.message)

async def save_webpage(page_url: str, user_id: int) -> Optional[str]:
    LOGGER.info("Wayback running for: %s", page_url)
    user_agent = get_random_user_agent()
    headers = {
        "User-Agent": user_agent,
    }

    try:
        response = requests.get(
            f"https://web.archive.org/save/{page_url}", headers=headers, timeout=30
        )
        response.raise_for_status()
        LOGGER.info("wayback success for: %s", page_url)
        return response.url
    except requests.exceptions.RequestException as e:
        LOGGER.error("wayback unsuccessful for: %s, %s", page_url, str(e))
        return None

authfilter = CustomFilters.authorized_chat if config_dict["WAYBACK_ENABLED"] else CustomFilters.owner_filter

wayback_handler = CommandHandler(
    BotCommands.WayBackCommand,
    wayback,
    filters=authfilter | Filters.user(config_dict["OWNER_ID"]),
)

dispatcher.add_handler(wayback_handler)
