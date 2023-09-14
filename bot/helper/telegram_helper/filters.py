#!/usr/bin/env python3
from pyrogram.filters import create
from pyrogram.enums import ChatType

from bot import user_data, OWNER_ID
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
        if bool(uid == OWNER_ID or (uid in user_data and (user_data[uid].get('is_auth', False) or user_data[uid].get('is_sudo', False)))):
            return True
        
        auth_chat = False
        chat_id = message.chat.id
        if chat_id in user_data and user_data[chat_id].get('is_auth', False):
            if len(topic_ids := user_data[chat_id].get('topic_ids', [])) == 0:
                auth_chat = True
            elif (is_forum := message.reply_to_message) and ((is_forum.text is None and is_forum.caption is None and is_forum.id in topic_ids)
                or ((is_forum.text or is_forum.caption) and ((not is_forum.reply_to_top_message_id and is_forum.reply_to_message_id in topic_ids)
                or (is_forum.reply_to_top_message_id in topic_ids)))):
                auth_chat = True
        return auth_chat
    
    authorized = create(authorized_user)
    
    async def authorized_usetting(self, _, message):
        uid = (message.from_user or message.sender_chat).id
        chat_id = message.chat.id
        isExists = False
        if uid == OWNER_ID or (uid in user_data and (user_data[uid].get('is_auth', False) or user_data[uid].get('is_sudo', False))) or (chat_id in user_data and user_data[chat_id].get('is_auth', False)):
            isExists = True
        elif message.chat.type == ChatType.PRIVATE:
            for channel_id in user_data:
                if not (user_data[channel_id].get('is_auth') and str(channel_id).startswith('-100')):
                    continue
                try:
                    if await (await chat_info(str(channel_id))).get_member(uid):
                        isExists = True
                        break
                except:
                    continue
        return isExists
        
    authorized_uset = create(authorized_usetting)

    async def sudo_user(self, _, message):
        user = message.from_user or message.sender_chat
        uid = user.id
        return bool(uid == OWNER_ID or uid in user_data and user_data[uid].get('is_sudo'))

    sudo = create(sudo_user)
    
    async def blacklist_user(self, _, message):
        user = message.from_user or message.sender_chat
        uid = user.id
        return bool(uid != OWNER_ID and uid in user_data and user_data[uid].get('is_blacklist'))
        
    blacklisted = create(blacklist_user)
