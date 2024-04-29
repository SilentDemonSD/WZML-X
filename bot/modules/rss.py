import asyncio
import aiosession
import dataclasses
import re
import typing as t
from collections import defaultdict
from functools import lru_cache, partial
from urllib.parse import urlparse

import feedparser
import pyrogram
from pyrogram.errors import FloodWait, RpcError
from pyrogram.handlers import MessageHandler, CallbackQueryHandler
from pyrogram.filters import command, regex, create
from pyrogram.raw.functions.messages import (
    SendMediaGroup,
    EditMessageMedia,
    EditMessageText,
    SendMessage,
    DeleteMessages,
    AnswerCallbackQuery,
)
from pyrogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    InputMediaPhoto,
    Message,
)

from bot import scheduler, rss_dict, LOGGER, DATABASE_URL, config_dict, bot
from bot.helper.telegram_helper.message_utils import (
    sendMessage,
    editMessage,
    sendRss,
    sendFile,
)
from bot.helper.telegram_helper.filters import CustomFilters
from bot.helper.telegram_helper.bot_commands import BotCommands
from bot.helper.ext_utils.db_handler import DbManger
from bot.helper.telegram_helper.button_build import ButtonMaker
from bot.helper.ext_utils.bot_utils import new_thread
from bot.helper.ext_utils.exceptions import RssShutdownException
from bot.helper.ext_utils.help_messages import RSS_HELP_MESSAGE

rss_dict_lock = asyncio.Lock()
handler_dict = defaultdict(bool)


@dataclasses.dataclass
class RssFeed:
    link: str
    last_feed: str = ""
    last_title: str = ""
    paused: bool = False
    inf: t.List[t.List[str]] = dataclasses.field(default_factory=list)
    exf: t.List[t.List[str]] = dataclasses.field(default_factory=list)
    command: str = ""
    tag: str = ""


async def rssMenu(event: Message) -> tuple[str, InlineKeyboardMarkup]:
    user_id = event.from_user.id
    buttons = ButtonMaker()
    buttons.ibutton("Subscribe", f"rss sub {user_id}")
    buttons.ibutton("Subscriptions", f"rss list {user_id} 0")
    buttons.ibutton("Get Items", f"rss get {user_id}")
    buttons.ibutton("Edit", f"rss edit {user_id}")
    buttons.ibutton("Pause", f"rss pause {user_id}")
    buttons.ibutton("Resume", f"rss resume {user_id}")
    buttons.ibutton("Unsubscribe", f"rss unsubscribe {user_id}")
    if await CustomFilters.sudo("", event):
        buttons.ibutton("All Subscriptions", f"rss listall {user_id} 0")
        buttons.ibutton("Pause All", f"rss allpause {user_id}")
        buttons.ibutton("Resume All", f"rss allresume {user_id}")
        buttons.ibutton("Unsubscribe All", f"rss allunsub {user_id}")
        buttons.ibutton("Delete User", f"rss deluser {user_id}")
        if scheduler.running:
            buttons.ibutton("Shutdown Rss", f"rss shutdown {user_id}")
        else:
            buttons.ibutton("Start Rss", f"rss start {user_id}")
    buttons.ibutton("Close", f"rss close {user_id}")
    button = buttons.build_menu(2)
    msg = f'Rss Menu | Users: {len(rss_dict)} | Running: {scheduler.running}'
    return msg, button

