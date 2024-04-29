#!/usr/bin/env python3
from typing import AsyncContextManager, Callable, Optional

import pyrogram.filters
from pyrogram.enums import ChatType
from pyrogram.types import Message

from bot import user_data, OWNER_ID
from bot.helper.telegram_helper.message_utils import chat_info


class CustomFilters:
    async def owner_filter(self, _: None, message: Message) -> bool:
        """Return True if the message is sent by the owner, False otherwise."""
        user = message.from_user or message.sender_chat
        return user.id == OWNER_ID

    owner = pyrogram.filters.create(owner_filter)

    async def authorized_user(self, _: None, message: Message) -> bool:
        """Return True if the user is authorized, False otherwise."""
        user = message.from_user or message.sender_chat
        chat_id = message.chat.id
        is_auth = user_data.get(str(user.id), {}).get('is_auth', False)
        is_sudo = user_data.get(str(user.id), {}).get('is_sudo', False)
        chat_is_auth = user_data.get(str(chat_id), {}).get('is_auth', False)
        return user.id == OWNER_ID or is_auth or is_sudo or chat_is_auth

    authorized = pyrogram.filters.create(authorized_user)

    async def authorized_user_setting(self, _: None, message: Message) -> bool:
        """Return True if the user is authorized to change settings, False otherwise."""
        user = message.from_user or message.sender_chat
        chat_id = message.chat.id
        is_auth = user_data.get(str(user.id), {}).get('is_auth', False)
        is_sudo = user_data.get(str(user.id), {}).get('is_sudo', False)
        chat_is_auth = user_data.get(str(chat_id), {}).get('is_auth', False)
        if (
            user.id == OWNER_ID
            or is_auth
            or is_sudo
            or chat_is_auth
        ):
            return True
        if message.chat.type != ChatType.PRIVATE:
            return False
        for channel_id in user_data:
            if not (user_data[channel_id].get('is_auth') and not str(channel_id).startswith('-100')):
                continue
            try:
                if await chat_info(str(channel_id)).get_member(user.id):
                    return True
            except:
                continue
        return False

    authorized_user_setting = pyrogram.filters.create(authorized_user_setting)

    async def sudo_user(self, _: None, message: Message) -> bool:
        """Return True if the user is a sudo user, False otherwise."""
        user = message.from_user or message.sender_chat
        is_sudo = user_data.get(str(user.id), {}).get('is_sudo', False)
        return user.id == OWNER_ID or is_sudo

    sudo = pyrogram.filters.create(sudo_user)

    async def blacklist_user(self, _: None, message: Message) -> bool:
        """Return True if the user is blacklisted, False otherwise."""
        user = message.from_user or message.sender_chat
        is_blacklist = user_data.get(str(user.id), {}).get('is_blacklist', False)
        return user.id != OWNER_ID and is_blacklist

    blacklisted = pyrogram.filters.create(blacklist_user)
