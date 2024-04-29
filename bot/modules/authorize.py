#!/usr/bin/env python3
from pyrogram.handlers import MessageHandler
from pyrogram.filters import command, regex
from typing import Optional

from bot import user_data, DATABASE_URL, bot
from bot.helper.telegram_helper.message_utils import send_message
from bot.helper.telegram_helper.filters import CustomFilters
from bot.helper.telegram_helper.bot_commands import BotCommands
from bot.helper.ext_utils.db_handler import DbManager
from bot.helper.ext_utils.bot_utils import update_user_ldata


async def handle_authorization(context, message, is_authorize: bool) -> None:
    """Handles user authorization or unauthorization."""
    user_id = get_user_id(message)
    if user_id in user_data:
        is_already_authorized = user_data[user_id].get("is_auth")
        if is_authorize and is_already_authorized:
            await send_message(message, "Already Authorized!")
            return
        if not is_authorize and not is_already_authorized:
            await send_message(message, "Already Unauthorized!")
            return

    update_user_ldata(user_id, "is_auth", is_authorize)
    if DATABASE_URL:
        async with DbManager() as db_manager:
            try:
                await db_manager.update_user_data(user_id)
            except Exception as e:
                await send_message(message, f"Error updating user data: {e}")
                return

    if is_authorize:
        await send_message(message, "Authorized")
    else:
        await send_message(message, "Unauthorized")


async def handle_sudo(context, message, is_add: bool) -> None:
    """Handles adding or removing sudo users."""
    user_id = get_user_id(message)
    if user_id in user_data:
        is_sudo = user_data[user_id].get("is_sudo")
        if is_add and is_sudo:
            await send_message(message, "Already Sudo!")
            return
        if not is_add and not is_sudo:
            await send_message(message, "Not a Sudo User, Already Demoted")
            return

    update_user_ldata(user_id, "is_sudo", is_add)
    if DATABASE_URL:
        async with DbManager() as db_manager:
            try:
                await db_manager.update_user_data(user_id)
            except Exception as e:
                await send_message(message, f"Error updating user data: {e}")
                return

    if is_add:
        await send_message(message, "Promoted as Sudo")
    else:
        await send_message(message, "Demoted")


async def handle_blacklist(context, message, is_add: bool) -> None:
    """Handles adding or removing users from the blacklist."""
    user_id = get_user_id(message)
    if user_id in user_data:
        is_blacklisted = user_data[user_id].get("is_blacklist")
        if is_add and is_blacklisted:
            await send_message(message, "User Already BlackListed!")
            return
        if not is_add and not is_blacklisted:
            await send_message(message, "User Already Freed")
            return

    update_user_ldata(user_id, "is_blacklist", is_add)
    if DATABASE_URL:
        async with DbManager() as db_manager:
            try:
                await db_manager.update_user_data(user_id)
            except Exception as e:
                await send_message(message, f"Error updating user data: {e}")
                return

    if is_add:
        await send_message(message, "User BlackListed")
    else:
        await send_message(message, "User Set Free as Bird!")


def get_user_id(message:
