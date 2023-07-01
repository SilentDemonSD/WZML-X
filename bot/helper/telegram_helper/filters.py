#!/usr/bin/env python3
from pyrogram.filters import create

from bot import user_data, OWNER_ID, config_dict, LOGGER
from bot.helper.telegram_helper.message_utils import chat_info


class CustomFilters:

    async def owner_filter(self, _, message):
        user = message.from_user or message.sender_chat
        uid = user.id
        return uid == OWNER_ID

    owner = create(owner_filter)

    async def authorized_user(self, _, message):
        user = message.from_user or message.sender_chat
        uid = user.id
        chat_id = message.chat.id
        return bool(uid == OWNER_ID or (uid in user_data and (user_data[uid].get('is_auth', False) or
                                                              user_data[uid].get('is_sudo', False))) or (chat_id in user_data and user_data[chat_id].get('is_auth', False)))

    authorized = create(authorized_user)
    
    async def authorized_usetting(self, _, message):
        uid = (message.from_user or message.sender_chat).id
        #if uid == OWNER_ID or (uid in user_data and (user_data[uid].get('is_auth', False) or user_data[uid].get('is_sudo', False))):
        #    LOGGER.info("Access Given uset")
        #    return True
        isExists = False
        LOGGER.info("uset check")
        for channel_id in config_dict['AUTHORIZED_CHATS']:
            LOGGER.info("For Loop check")
            try:
                auth_chat = await chat_info(channel_id)
                user = await auth_chat.get_member(uid)
                LOGGER.info(user)
                if user:
                    isExists = True
                    break
            except Exception as e:
                LOGGER.info(e)
                continue
        return isExists
        
    authorized_uset = create(authorized_usetting)

    async def sudo_user(self, _, message):
        user = message.from_user or message.sender_chat
        uid = user.id
        return bool(uid == OWNER_ID or uid in user_data and user_data[uid].get('is_sudo'))

    sudo = create(sudo_user)
