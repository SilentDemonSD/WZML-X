from typing import List, Union

from pyrogram import Client
from pyrogram.errors import RPCError

from bot.helper.ext_utils.bot_utils import initialize_bot, start_cleanup, set_commands
from bot.helper.ext_utils.db_handler import DbManger
from bot.helper.listeners.aria2_listener import start_aria2_listener
from bot.helper.telegram_helper.bot_commands import BotCommands
from bot.helper.telegram_helper.filters import CustomFilters
from bot.helper.telegram_helper.message_utils import sendMessage, editMessage, editReplyMarkup, sendFile, deleteMessage, delete_all_messages
from bot.modules import authorize, clone, gd_count, gd_delete, gd_list, cancel_mirror, mirror_leech, status, torrent_search, torrent_select, ytdlp, \
                     rss, shell, eval, users_settings, bot_settings, speedtest, save_msg, images, imdb, anilist, mediainfo, mydramalist, gen_pyro_sess, \
                     gd_clean, broadcast, category_select

async def main():
    bot, user = initialize_bot()
    await set_commands(bot)
    await start_cleanup()
    await start_aria2_listener()
    await gather(
        torrent_search.initiate_search_tools(),
        restart_notification(),
        search_images(),
        log_check(),
    )

    bot.add_handler(MessageHandler(start, filters=command(BotCommands.StartCommand) & private))
    bot.add_handler(CallbackQueryHandler(token_callback, filters=regex(r'^pass')))
    bot.add_handler(MessageHandler(login, filters=command(BotCommands.LoginCommand) & private))
    bot.add_handler(MessageHandler(log, filters=command(BotCommands.LogCommand) & CustomFilters.sudo))
    bot.add_handler(MessageHandler(restart, filters=command(BotCommands.RestartCommand) & CustomFilters.sudo))
    bot.add_handler(MessageHandler(ping, filters=command(BotCommands.PingCommand) & CustomFilters.authorized & ~CustomFilters.blacklisted))
    bot.add_handler(MessageHandler(bot_help, filters=command(BotCommands.HelpCommand) & CustomFilters.authorized & ~CustomFilters.blacklisted))
    bot.add_handler(MessageHandler(stats, filters=command(BotCommands.StatsCommand) & CustomFilters.authorized & ~CustomFilters.blacklisted))

    logging.info(f"WZML-X Bot {@bot.me.username} Started!")
    if user:
        logging.info(f"WZ's User {@user.me.username} Ready!")
    signal(SIGINT, exit_clean_up)

    try:
        await bot.run()
    except RPCError as e:
        logging.error(e)
        if e.code == 401:
            logging.error("Unauthorized: Make sure the API token is correct!")
        elif e.code == 429:
            logging.error("Too many requests: Try reducing the number of requests or increasing the flood_sleep_time in config.py!")
        else:
            logging.error("An error occurred: Check the logs for more information!")


bot_run = bot.loop.run_until_complete
bot_run(main())
bot_run(idle())
bot_run(stop_signals())



from os import execl, environ
from sys import executable
from time import time, monotonic
from datetime import datetime
from signal import signal, SIGINT
from logging import basicConfig, INFO, error, debug

import pyrogram
from pyrogram.errors import FloodWait, RPCError
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from bot.config import Config
from bot.helper.ext_utils.fs_utils import start_cleanup, exit_clean_up, clean_all
from bot.helper.ext_utils.bot_utils import initialize_bot, set_commands
from bot.helper.ext_utils.db_handler import DbManger
from bot.helper.telegram_helper.bot_commands import BotCommands
from bot.helper.telegram_helper.filters import CustomFilters
from bot.helper.telegram_helper.message_utils import sendMessage, editMessage, editReplyMarkup, sendFile, deleteMessage, delete_all_messages
from bot.helper.telegram_helper.button_build import ButtonMaker
from bot.helper.listeners.aria2_listener import start_aria2_listener
from bot.modules import authorize, clone, gd_count, gd_delete, gd_list, cancel_mirror, mirror_leech, status, torrent_search, torrent_select, ytdlp, \
                     rss, shell, eval, users_settings, bot_settings, speedtest, save_msg, images, imdb, anilist, mediainfo, mydramalist, gen_pyro_sess, \
                     gd_clean, broadcast, category_select

# Config
CONFIG: Config = Config()

# Initialize bot
bot, user = initialize_bot()

# Initialize database
db = DbManger()

# Initialize logging
basicConfig(
    level=INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logging = {
    "debug": debug,
    "error": error,
}

# Initialize filters
CustomFilters.bot = bot
CustomFilters.user = user
CustomFilters.db = db
CustomFilters.CONFIG = CONFIG

# Initialize command handlers
@bot.message_handler(command=BotCommands.StartCommand, func=CustomFilters.private)
async def start(client, message):
    ...

@bot.callback_query_handler(func=CustomFilters.regex.match("^pass"))
async def token_callback(client, query):
    ...

@bot.message_handler(command=BotCommands.LoginCommand, func=CustomFilters.private)
async def login(client, message):
    ...

@bot.message_handler(command=BotCommands.LogCommand, func=CustomFilters.sudo)
async def log(client, message):
    ...

