import sys

import pyrogram
from pyrogram.errors import FloodWait
from pyrogram.handlers import MessageHandler
from pyrogram.filters import command, regex, text

from bot import user_data, DATABASE_URL, bot, LOGGER
from bot.helper.telegram_helper.message_utils import sendMessage, deleteMessage
from bot.helper.telegram_helper.filters import CustomFilters
from bot.helper.telegram_helper.bot_commands import BotCommands
from bot.helper.ext_utils.db_handler import DbManger
from bot.helper.ext_utils.bot_utils import update_user_ldata

async def authorize(client: pyrogram.Client, message: pyrogram.types.Message) -> None:
    ...

async def unauthorize(client: pyrogram.Client, message: pyrogram.types.Message) -> None:
    ...

async def add_sudo(client: pyrogram.Client, message: pyrogram.types.Message) -> None:
    ...

async def remove_sudo(client: pyrogram.Client, message: pyrogram.types.Message) -> None:
    ...

async def add_blacklist(client: pyrogram.Client, message: pyrogram.types.Message) -> None:
    ...

async def rm_blacklist(client: pyrogram.Client, message: pyrogram.types.Message) -> None:
    ...

async def black_listed(client: pyrogram.Client, message: pyrogram.types.Message) -> None:
    ...

if __name__ == "__main__":
    bot.add_handler(MessageHandler(authorize, filters=command(BotCommands.AuthorizeCommand) & CustomFilters.sudo))
    bot.add_handler(MessageHandler(unauthorize, filters=command(BotCommands.UnAuthorizeCommand) & CustomFilters.sudo))
    bot.add_handler(MessageHandler(add_sudo, filters=command(BotCommands.AddSudoCommand) & CustomFilters.sudo))
    bot.add_handler(MessageHandler(remove_sudo, filters=command(BotCommands.RmSudoCommand) & CustomFilters.sudo))
    bot.add_handler(MessageHandler(add_blacklist, filters=command(BotCommands.AddBlackListCommand) & CustomFilters.sudo))
    bot.add_handler(MessageHandler(rm_blacklist, filters=command(BotCommands.RmBlackListCommand) & CustomFilters.sudo))
    bot.add_handler(MessageHandler(black_listed, filters=regex(r'^/') & CustomFilters.authorized & CustomFilters.blacklisted))
