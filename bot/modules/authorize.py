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
from bot.helper.ext_utils.bot_utils import update_user_ldata

AuthorizeFilter = create(lambda _, __, message: message.chat.id == message.from_user.id and message.from_user.is_self)
UnauthorizeFilter = create(lambda _, __, message: message.chat.id == message.from_user.id and message.from_user.is_self)
AddSudoFilter = create(lambda _, __, message: message.chat.id == message.from_user.id and message.from_user.is_self)
RemoveSudoFilter = create(lambda _, __, message: message.chat.id == message.from_user.id and message.from_user.is_self)
AddBlacklistFilter = create(lambda _, __, message: message.chat.id == message.from_user.id and message.from_user.is_self)
RmBlacklistFilter = create(lambda _, __, message: message.chat.id == message.from_user.id and message.from_user.is_self)
BlacklistedFilter = create(lambda _, __, message: message.from_user.id not in user_data.get_sudoers() and user_data.is_user_blacklisted(message.from_user.id))

async def authorize(client: pyrogram.Client, message: pyrogram.types.Message) -> None:
    """Authorize a user as a sudoer."""
    try:
        user_id = message.reply_to_message.from_user.id
    except AttributeError:
        await sendMessage(message, "Please reply to a user's message to authorize them as a sudoer.")
        return
    await client.invoke(pyrogram.raw.functions.channels.EditBanned(
        channel=message.chat.id,
        user_id=user_id,
        banned_rights=pyrogram.raw.types.ChatBannedRights(
            until_date=0,
            view_messages=True,
            send_messages=True,
            send_media=True,
            send_stickers=True,
            send_gifs=True,
            send_games=True,
            send_inline=True,
            embed_links=True
        )
    ))
    user_data.add_sudoer(user_id)
    await sendMessage(message, f"Successfully authorized {message.reply_to_message.from_user.mention} as a sudoer.")

async def unauthorize(client: pyrogram.Client, message: pyrogram.types.Message) -> None:
    """Unauthorize a user as a sudoer."""
    try:
        user_id = message.reply_to_message.from_user.id
    except AttributeError:
        await sendMessage(message, "Please reply to a user's message to unauthorize them as a sudoer.")
        return
    await client.invoke(pyrogram.raw.functions.channels.EditBanned(
        channel=message.chat.id,
        user_id=user_id,
        banned_rights=pyrogram.raw.types.ChatBannedRights(
            until_date=0,
            view_messages=False,
            send_messages=False,
            send_media=False,
            send_stickers=False,
            send_gifs=False,
            send_games=False,
            send_inline=False,
            embed_links=False
        )
    ))
    user_data.remove_sudoer(user_id)
    await sendMessage(message, f"Successfully unauthorized {message.reply_to_message.from_user.mention} as a sudoer.")

async def add_sudo(client: pyrogram.Client, message: pyrogram.types.Message) -> None:
    """Add a user to the sudoers list."""
    user_id = message.text.split()[1]
    if user_id.isdigit():
        user_data.add_sudoer(int(user_id))
        await sendMessage(message, f"Successfully added {user_id} to the sudoers list.")
    else:
        await sendMessage(message, "Invalid user ID. Please provide a valid user ID to add to the sudoers list.")

async def remove_sudo(client: pyrogram.Client, message: pyrogram.types.Message) -> None:
    """Remove a user from the sudoers list."""
    user_id = message.text.split()[1]
    if user_id.isdigit():
        user_data.remove_sudoer(int(user_id))
        await sendMessage(message, f"Successfully removed {user_id} from the sudoers list.")
    else:
        await sendMessage(message, "Invalid user ID. Please provide a valid user ID to remove from the sudoers list.")

async def add_blacklist(client: pyrogram.Client, message: pyrogram.types.Message) -> None:
    """Add a user to the blacklist."""
    user_id = message.text.split()[1]
    if user_id.isdigit():
        user_data.add_blacklisted_user(int(user_id))
        await sendMessage(message, f"Successfully added {user_id} to the blacklist.")
    else:
        await sendMessage(message, "Invalid user ID. Please provide a valid user ID to add to the blacklist.")

async def rm_blacklist(client: pyrogram.Client, message: pyrogram.types.Message) -> None:
    """Remove a user from the blacklist."""
    user_id = message.text.split()[1]
    if user_id.isdigit():
        user_data.remove_blacklisted_user(int(user_id))
        await sendMessage(message, f"Successfully removed {user_id} from the blacklist.")
    else:
        await sendMessage(message, "Invalid user ID. Please provide a valid user ID to remove from the blacklist.")

async def black_listed(client: pyrogram.Client, message: pyrogram.types.Message) -> None:
    """Respond to a message from a blacklisted user."""
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
