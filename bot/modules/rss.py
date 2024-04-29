import asyncio  # for handling asynchronous tasks
import aiosession  # for making HTTP requests
import dataclasses  # for creating data classes
import re  # for regular expressions
import typing as t  # for type hints
from collections import defaultdict  # for creating a defaultdict
from functools import lru_cache, partial  # for caching and partial function application
from urllib.parse import urlparse  # for parsing URLs

import feedparser  # for parsing RSS feeds
import pyrogram  # for creating a Telegram bot
from pyrogram.errors import FloodWait, RpcError  # for handling errors
from pyrogram.handlers import MessageHandler, CallbackQueryHandler  # for handling messages and callback queries
from pyrogram.filters import command, regex, create  # for filtering messages
from pyrogram.raw.functions.messages import (
    SendMediaGroup,  # for sending media groups
    EditMessageMedia,  # for editing message media
    EditMessageText,  # for editing message text
    SendMessage,  # for sending messages
    DeleteMessages,  # for deleting messages
    AnswerCallbackQuery,  # for answering callback queries
)
from pyrogram.types import (
    CallbackQuery,  # for handling callback queries
    InlineKeyboardButton,  # for creating inline buttons
    InlineKeyboardMarkup,  # for creating inline keyboards
    InputMediaPhoto,  # for sending photos as InputMedia
    Message,  # for handling messages
)

from bot import scheduler, rss_dict, LOGGER, DATABASE_URL, config_dict, bot  # for importing necessary modules
from bot.helper.telegram_helper.message_utils import (  # for importing message utilities
    sendMessage,
    editMessage,
    sendRss,
    sendFile,
)
from bot.helper.telegram_helper.filters import CustomFilters  # for importing custom filters
from bot.helper.telegram_helper.bot_commands import BotCommands  # for importing bot commands
from bot.helper.ext_utils.db_handler import DbManger  # for importing database manager
from bot.helper.telegram_helper.button_build import ButtonMaker  # for importing button builder
from bot.helper.ext_utils.bot_utils import new_thread  # for importing new thread creation
from bot.helper.ext_utils.exceptions import RssShutdownException  # for importing custom exceptions
from bot.helper.ext_utils.help_messages import RSS_HELP_MESSAGE  # for importing help messages

rss_dict_lock = asyncio.Lock()  # for creating a lock for rss_dict
handler_dict = defaultdict(bool)  # for creating a defaultdict for handler_dict


@dataclasses.dataclass  # for creating a data class for RssFeed
class RssFeed:
    link: str  # for storing the RSS feed link
    last_feed: str = ""  # for storing the last feed
    last_title: str = ""  # for storing the last feed title
    paused: bool = False  # for storing whether the feed is paused or not
    inf: t.List[t.List[str]] = dataclasses.field(default_factory=list)  # for storing the included feed items
    exf: t.List[t.List[str]] = dataclasses.field(default_factory=list)  # for storing the excluded feed items
    command: str = ""  # for storing the command to subscribe to the feed
    tag: str = ""  # for storing the tag for the feed


async def rss_menu(client, event):  # for creating a function to handle the RSS menu
    user_id = event.from_user.id  # for getting the user ID
    buttons = ButtonMaker()  # for creating a button maker
    buttons.ibutton("Subscribe", f"rss sub {user_id}")  # for creating a subscribe button
    buttons.ibutton("Subscriptions", f"rss list {user_id} 0")  # for creating a subscriptions button
    buttons.ibutton("Get Items", f"rss get {user_id}")  # for creating a get items button
    buttons.ibutton("Edit", f"rss edit {user_id}")  # for creating an edit button
    buttons.ibutton("Pause", f"rss pause {user_id}")  # for creating a pause button
    buttons.ibutton("Resume", f"rss resume {user_id}")  # for creating a resume button
    buttons.ibutton("Unsubscribe", f"rss unsubscribe {user_id}")  # for creating an unsubscribe button
    if await CustomFilters.sudo("", event):  # if the user is a sudo user
        buttons.ibutton("All Subscriptions", f"rss listall {user_id} 0")  # for creating an all subscriptions button
        buttons.ibutton("Pause All", f"rss allpause {user_id}")  # for creating a pause all button
        buttons.ibutton("Resume All", f"rss allresume {user_id}")  # for creating a resume all button
        buttons.ibutton("Unsubscribe All", f"rss allunsub {user_id}")  # for creating an unsubscribe all button
        buttons.ibutton("Delete User", f"rss deluser {user_id}")  # for creating a delete user button
        if scheduler.running:  # if the scheduler is running
            buttons.ibutton("Shutdown Rss", f"rss shutdown {user_id}")  # for creating a shutdown RSS button
        else:
            buttons.ibutton("Start Rss", f"rss start {user_id}")  # for creating a start RSS button
    buttons.ibutton("Close", f"rss close {user_id}")  # for creating a close button
    button = buttons.build_menu(2)  # for building the inline keyboard markup
    msg = f'Rss Menu | Users: {len(rss_dict)} | Running: {scheduler.running}'  # for creating the message to be sent
    await sendMessage(event.chat.id, msg, buttons=button)  # for sending the message with the inline keyboard markup
