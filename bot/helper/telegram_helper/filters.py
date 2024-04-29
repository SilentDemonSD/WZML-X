import pyrogram
from pyrogram.enums import ChatType
from pyrogram.filters import User, ChatAdmin

class CustomFilters:
    def __init__(self, context: dict):
        self.context = context
        self.owner_id = context['owner_id']

    async def owner(self, client: pyrogram.Client, message: pyrogram.types.Message) -> bool:
        """Check if the message is sent by the owner."""
        user = message.from_user or message.sender_chat
        return user.id == self.owner_id

    async def authorized_user(self, client: pyrogram.Client, message: pyrogram.types.Message) -> bool:
        """Check if the user is authorized to use the command."""
        user = message.from_user or message.sender_chat
        user_id = user.id

        if user_id == self.owner_id or (user_id in self.context and self.context[user_id].get('is_auth', False)):
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
                except:
                    continue

        return False

    async def authorized_user_setting(self, client: pyrogram.Client, message: pyrogram.types.Message) -> bool:
        """Check if the user is authorized to use the setting command."""
        user_id = (message.from_user or message.sender_chat).id
        chat = message.chat

        if (
            user_id == self.owner_id
            or (user_id in self.context and self.context[user_id].get('is_auth', False))
            or (chat.id in self.context and self.context[chat.id].get('is_auth', False))
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
                except:
                    continue

        return False

    async def sudo(self, client: pyrogram.Client, message: pyrogram.types.Message) -> bool:
        """Check if the user is a sudo user."""
        user = message.from_user or message.sender_chat
        user_id = user.id
        return user_id == self.owner_id or (user_id in self.context and self.context[user_id].get('is_sudo'))

    async def blacklisted(self, client: pyrogram.Client, message: pyrogram.types.Message) -> bool:
        """Check if the user is blacklisted."""
        user = message.from_user or message.sender_chat
        user_id = user.id
        return user_id != self.owner_id and user_id in self.context and self.context[user_id].get('is_blacklist')

    def __getattr__(self, name: str) -> Callable[[pyrogram.Client, pyrogram.types.Message], Coroutine[Any, Any, bool]]:
        """Return a filter by name."""
        return getattr(self, name)
