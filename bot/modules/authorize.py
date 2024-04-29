#!/usr/bin/env python3
from pyrogram.handlers import MessageHandler
from pyrogram.filters import command, regex
from pyrogram.client import AsyncContextManager
from typing import Any

from bot import user_data, DATABASE_URL, bot, LOGGER
from bot.helper.telegram_helper.message_utils import send_message
from bot.helper.telegram_helper.filters import CustomFilters
from bot.helper.telegram_helper.bot_commands import BotCommands
from bot.helper.ext_utils.db_handler import DbManager as DbManger
from bot.helper.ext_utils.bot_utils import update_user_ldata


async def a_authorize(client: AsyncContextManager, m):
    """Authorize a user or topic."""
    user_id = _get_user_id(m)
    tid = _get_topic_id(m, user_id)

    if user_id in user_data and user_data[user_id].get("is_auth"):
        msg = "Already Authorized!"
    else:
        update_user_ldata(user_id, "is_auth", True)
        msg = "Authorized"

    if tid:
        if tid not in (tids := user_data[user_id].get("topic_ids", [])):
            tids.append(tid)
            update_user_ldata(user_id, "topic_ids", tids)
            if DATABASE_URL:
                await DbManger().update_user_data(user_id)
            msg = "Topic Authorized!"
        else:
            msg = "Topic Already Authorized!"

    await send_message(m, msg)


async def a_unauthorize(client: AsyncContextManager, m):
    """Unauthorize a user or topic."""
    user_id = _get_user_id(m)
    tid = _get_topic_id(m, user_id)

    if user_id not in user_data or not user_data[user_id].get("is_auth"):
        msg = "Unauthorized"
    else:
        tids = []
        if tid:
            if tid in (tids := user_data[user_id].get("topic_ids", [])):
                tids.remove(tid)
                update_user_ldata(user_id, "topic_ids", tids)

        if not tids:
            update_user_ldata(user_id, "is_auth", False)
            if DATABASE_URL:
                await DbManger().update_user_data(user_id)
            msg = "Unauthorized"
        else:
            msg = "Already Unauthorized!"

    await send_message(m, msg)


async def a_add_sudo(client: AsyncContextManager, m):
    """Add sudo privileges to a user."""
    user_id = _get_user_id(m)

    if user_id in user_data and user_data[user_id].get("is_sudo"):
        msg = "Already Sudo!"
    else:
        update_user_ldata(user_id, "is_sudo", True)
        if DATABASE_URL:
            await DbManger().update_user_data(user_id)
        msg = "Promoted as Sudo"

    await send_message(m, msg)


async def a_remove_sudo(client: AsyncContextManager, m):
    """Remove sudo privileges from a user."""
    user_id = _get_user_id(m)

    if user_id in user_data and not user_data[user_id].get("is_sudo"):
        msg = "Not a Sudo User, Already Demoted"
    else:
        update_user_ldata(user_id, "is_sudo", False)
        if DATABASE_URL:
            await DbManger().update_user_data(user_id)
        msg = "Demoted"

    await send_message(m, msg)


async def a_add_blacklist(client: AsyncContextManager, m):
    """Add a user to the blacklist."""
    user_id = _get_user_id(m)

    if user_id in user_data and user_data[user_id].get("is_blacklist"):
        msg = "User Already BlackListed!"
    else:
        update_user_ldata(user_id, "is_blacklist", True)
        if DATABASE_URL:
            await DbManger().update_user_data(user_id)
        msg = "User BlackListed"

    await send_message(m, msg)


async def a_rm_blacklist(client: AsyncContextManager, m):
    """Remove a user from the blacklist."""
    user_id = _get_user_id(m)

    if user_id in user_data and not user_data[user_id].get("is_blacklist"):
        msg = "<i>User Already Freed</i>"
    else:
        update_user_ldata(user_id, "is_blacklist", False)
        if DATABASE_URL:
            await DbManger().update_user_data(user_id)
        msg = "<i>User Set Free as Bird!</i>"

    await send_message(m, msg)


async def a_black_listed(client: AsyncContextManager, m):
    """Restrict a blacklisted user from using the bot."""
    await send_message(m, "<i>BlackListed Detected, Restricted from Bot</i>")


def _get_user_id(m: Any) -> int:
    """Get the user ID from the message."""
    msg = m.text.split()
    user_id = m.chat.id
    if len(msg) > 1:
        user_id = int(msg[1].strip())
    elif m.reply_to_message:
        user_id = m.reply_to_message.from_user.id
    return user_id


def _get_topic_id(m: Any, user_id: int) -> int:
    """Get the topic ID from the message."""
    msg = m.text.split()
    tid = ""
    if len(msg) > 1:
        nid = msg[1].split(":")
        tid = int(nid[1]) if len(nid) > 1 else ""
    elif m.reply_to_message:
        tid = m.reply_to_message.message_id
    return tid


if __name__ == "__main__":
    bot.add_handler(MessageHandler(a_authorize, filters=command(BotCommands.AuthorizeCommand) & CustomFilters.sudo))
    bot.add_handler(MessageHandler(a_unauthorize, filters=command(BotCommands.UnAuthorizeCommand) & CustomFilters.sudo))
    bot.add_handler(MessageHandler(a_add_sudo, filters=command(BotCommands.AddSudoCommand) & CustomFilters.sudo))
    bot.add_handler(MessageHandler(a_remove_sudo, filters=command(BotCommands.RmSudoCommand) & CustomFilters.sudo))
    bot.add_handler(MessageHandler(a_add_blacklist, filters=command(BotCommands.AddBlackListCommand) & CustomFilters.sudo))
    bot.add_handler(MessageHandler(a_rm_blacklist, filters=command(BotCommands.RmBlackListCommand) & CustomFilters.sudo))
    bot.add_handler(MessageHandler(a_black_listed, filters=regex(r"^/") & CustomFilters.authorized & CustomFilters.blacklisted))
