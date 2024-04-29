import sys

import pyrogram
from pyrogram.errors import FloodWait
from pyrogram.handlers import MessageHandler
from pyrogram.filters import command, regex, text, create

from bot import user_data, DATABASE_URL, bot, LOGGER
from bot.helper.telegram_helper.message_utils import sendMessage, deleteMessage
from bot.helper.telegram_helper.filters import CustomFilters
from bot.helper.telegram_helper.bot_commands import BotCommands
from bot.helper.ext_utils.db_handler import DbManger
from bot.helper.ext_utils.bot_utils import is_sudo_user, is_blacklisted_user

AuthorizeFilter = create(lambda _, __, message: is_sudo_user(message))
UnauthorizeFilter = create(lambda _, __, message: is_sudo_user(message))
AddSudoFilter = create(lambda _, __, message: is_sudo_user(message))
RemoveSudoFilter = create(lambda _, __, message: is_sudo_user(message))
AddBlacklistFilter = create(lambda _, __, message: is_sudo_user(message))
RmBlacklistFilter = create(lambda _, __, message: is_sudo_user(message))
BlacklistedFilter = create(lambda _, __, message: is_blacklisted_user(message))

async def authorize(client: pyrogram.Client, message: pyrogram.types.Message) -> None:
    user_id = message.reply_to_message.from_user.id if message.reply_to_message else None
    if not user_id:
        await sendMessage(message, "Please reply to a user's message to authorize them as a sudoer.")
        return
    try:
        await client.edit_banned(
            message.chat.id,
            user_id,
            until_date=0,
            can_send_messages=True,
            can_send_media_messages=True,
            can_send_other_messages=True,
            can_add_web_page_previews=True
        )
        user_data.add_sudoer(user_id)
        await sendMessage(message, f"Successfully authorized {message.reply_to_message.from_user.mention} as a sudoer.")
    except FloodWait as e:
        await asyncio.sleep(e.x)
        await authorize(client, message)

async def unauthorize(client: pyrogram.Client, message: pyrogram.types.Message) -> None:
    user_id = message.reply_to_message.from_user.id if message.reply_to_message else None
    if not user_id:
        await sendMessage(message, "Please reply to a user's message to unauthorize them as a sudoer.")
        return
    try:
        await client.edit_banned(
            message.chat.id,
            user_id,
            until_date=0,
            can_send_messages=False,
            can_send_media_messages=False,
            can_send_other_messages=False,
            can_add_web_page_previews=False
        )
        user_data.remove_sudoer(user_id)
        await sendMessage(message, f"Successfully unauthorized {message.reply_to_message.from_user.mention} as a sudoer.")
    except FloodWait as e:
        await asyncio.sleep(e.x)
        await unauthorize(client, message)

async def add_sudo(client: pyrogram.Client, message: pyrogram.types.Message) -> None:
    user_id = message.text.split()[1]
    if user_id.isdigit():
        user_data.add_sudoer(int(user_id))
        await sendMessage(message, f"Successfully added {user_id} to the sudoers list.")
    else:
        await sendMessage(message, "Invalid user ID. Please provide a valid user ID to add to the sudoers list.")

async def remove_sudo(client: pyrogram.Client, message: pyrogram.types.Message) -> None:
    user_id = message.text.split()[1]
    if user_id.isdigit():
        user_data.remove_sudoer(int(user_id))
        await sendMessage(message, f"Successfully removed {user_id} from the sudoers list.")
    else:
        await sendMessage(message, "Invalid user ID. Please provide a valid user ID to remove from the sudoers list.")

async def add_blacklist(client: pyrogram.Client, message: pyrogram.types.Message) -> None:
    user_id = message.text.split()[1]
    if user_id.isdigit():
        user_data.add_blacklisted_user(int(user_id))
        await sendMessage(message, f"Successfully added {user_id} to the blacklist.")
    else:
        await sendMessage(message, "Invalid user ID. Please provide a valid user ID to add to the blacklist.")

async def rm_blacklist(client: pyrogram.Client, message: pyrogram.types.Message) -> None:
    user_id = message.text.split()[1]
    if user_id.isdigit():
        user_data.remove_blacklisted_user(int(user_id))
        await sendMessage(message, f"Successfully removed {user_id} from the blacklist.")
    else:
        await sendMessage(message, "Invalid user ID. Please provide a valid user ID to remove from the blacklist.")

async def black_listed(client: pyrogram.Client, message: pyrogram.types.Message) -> None:
    if await user_data.is_user_blacklisted(message.from_user.id):
        await sendMessage(message, "You are blacklisted and cannot send messages in this chat.")
        await deleteMessage(message)

if __name__ == "__main__":
    bot.add_handler(MessageHandler(authorize, filters=command(BotCommands.AuthorizeCommand) & AuthorizeFilter))
    bot.add_handler(MessageHandler(unauthorize, filters=command(BotCommands.UnAuthorizeCommand) & UnauthorizeFilter))
    bot.add_handler(MessageHandler(add_sudo, filters=command(BotCommands.AddSudoCommand) & AddSudoFilter))
    bot.add_handler(MessageHandler(remove_sudo, filters=command(BotCommands.RmSudoCommand) & RemoveSudoFilter))
    bot.add_handler(MessageHandler(add_blacklist, filters=command(BotCommands.AddBlackListCommand) & AddBlacklistFilter))
    bot.add_handler(MessageHandler(rm_blacklist, filters=command(BotCommands.RmBlackListCommand) & RmBlacklistFilter))
    bot.add_handler(MessageHandler(black_listed, filters=BlacklistedFilter))
