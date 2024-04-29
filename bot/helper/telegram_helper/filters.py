import pyrogram
from pyrogram.enums import ChatType
from pyrogram.filters import User, ChatAdmin
from typing import Callable, Coroutine

class CustomFilters:
    def __init__(self, context: dict):
        """
        Initialize the CustomFilters class with a context dictionary.
        The context dictionary contains owner_id which is used to check if the message is sent by the owner.
        """
        self.context = context
        self.owner_id = context['owner_id']

    async def owner(self, client: pyrogram.Client, message: pyrogram.types.Message) -> bool:
        """
        Check if the message is sent by the owner.
        This function returns True if the message is sent by the owner, otherwise False.
        """
        user = message.from_user or message.sender_chat
        return user.id == self.owner_id

    async def authorized_user(self, client: pyrogram.Client, message: pyrogram.types.Message) -> bool:
        """
        Check if the user is authorized to use the command.
        This function returns True if the user is authorized, otherwise False.
        """
        user = message.from_user or message.sender_chat
        user_id = user.id

        if user_id == self.owner_id:
            return True

        if user_id in self.context and self.context[user_id].get('is_auth', False):
            return True

        chat = message.chat
        if chat.id in self.context and self.context[chat.id].get('is_auth', False):
            topic_ids = self.context[chat.id].get('topic_ids', [])
            if not topic_ids:
                return True

            is_forum = message.reply_to_message
            if (
                not is_forum.text and not is_forum.caption and is_forum.id in topic_ids
                or (is_forum.text or is_forum.caption)
                and (
                    not is_forum.reply_to_top_message_id and is_forum.reply_to_message_id in topic_ids
                    or is_forum.reply_to_top_message_id in topic_ids
                )
            ):
                return True

        if chat.type == ChatType.PRIVATE:
            for channel_id in self.context:
                if not (self.context[channel_id].get('is_auth') and str(channel_id).startswith('-100')):
                    continue

                try:
                    member = await client.get_chat_member(str(channel_id), user_id)
                    if member.status in (member.status.ADMINISTRATOR, member.status.OWNER):
                        return True
                except Exception:
                    continue

        return False

    async def authorized_user_setting(self, client: pyrogram.Client, message: pyrogram.types.Message) -> bool:
        """
        Check if the user is authorized to use the setting command.
        This function returns True if the user is authorized, otherwise False.
        """
        user_id = (message.from_user or message.sender_chat).id
        chat = message.chat

        if user_id == self.owner_id:
            return True

        if user_id in self.context and self.context[user_id].get('is_auth', False):
            return True

        if chat.id in self.context and self.context[chat.id].get('is_auth', False):
            return True

        if chat.type == ChatType.PRIVATE:
            for channel_id in self.context:
                if not (self.context[channel_id].get('is_auth') and str(channel_id).startswith('-100')):
                    continue

                try:
                    member = await client.get_chat_member(str(channel_id), user_id)
                    if member.status in (member.status.ADMINISTRATOR, member.status.OWNER):
                        return True
                except Exception:
                    continue

        return False

    async def sudo(self, client: pyrogram.Client, message: pyrogram.types.Message) -> bool:
        """
        Check if the user is a sudo user.
        This function returns True if the user is a sudo user, otherwise False.
        """
        user = message.from_user or message.sender_chat
        user_id = user.id
        return user_id == self.owner_id or (user_id in self.context and self.context[user_id].get('is_sudo', False))

    async def blacklisted(self, client: pyrogram.Client, message: pyrogram.types.Message) -> bool:
        """
        Check if the user is blacklisted.
        This function returns True if the user is blacklisted, otherwise False.
        """
        user = message.from_user or message.sender_chat
        user_id = user.id
        return user_id != self.owner_id and user_id in self.context and self.context[user_id].get('is_blacklist', False)

    def __getattr__(self, name: str) -> Callable[[pyrogram.Client, pyrogram.types.Message], Coroutine[Any, Any, bool]]:
        """
        Return a filter by name.
        This function returns a filter by its name.
        """
        return getattr(self, name)
