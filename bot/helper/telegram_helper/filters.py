import pyrogram
from pyrogram.enums import ChatType
from pyrogram.filters import User, ChatAdmin

class CustomFilters:

    OWNER_ID: int
    """Owner ID."""

    def __init__(self, context: dict):
        """
        Initialize the CustomFilters class with a context dictionary.

        :param context: A dictionary containing user data.
        """
        self.context = context

    @property
    def owner(self) -> Callable[[pyrogram.Client, pyrogram.types.Message], Coroutine[Any, Any, bool]]:
        """Check if the message is sent by the owner."""

        async def filter_(client: pyrogram.Client, message: pyrogram.types.Message) -> bool:
            user = message.from_user or message.sender_chat
            return user.id == self.OWNER_ID

        return filter_

    @property
    def authorized_user(self, raise_error: bool = False) -> Callable[[pyrogram.Client, pyrogram.types.Message], Coroutine[Any, Any, bool]]:
        """Check if the user is authorized to use the command."""

        async def filter_(client: pyrogram.Client, message: pyrogram.types.Message) -> bool:
            user = message.from_user or message.sender_chat
            user_id = user.id

            if user_id == self.OWNER_ID or (user_id in self.context and self.context[user_id].get('is_auth', False)):
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

            if raise_error:
                raise pyrogram.errors.UserNotParticipant

            return False

        return filter_

    @property
    def authorized_user_setting(self) -> Callable[[pyrogram.Client, pyrogram.types.Message], Coroutine[Any, Any, bool]]:
        """Check if the user is authorized to use the setting command."""

        async def filter_(client: pyrogram.Client, message: pyrogram.types.Message) -> bool:
            user_id = (message.from_user or message.sender_chat).id
            chat = message.chat

            if (
                user_id == self.OWNER_ID
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

        return filter_

    @property
    def sudo(self) -> Callable[[pyrogram.Client, pyrogram.types.Message], Coroutine[Any, Any, bool]]:
        """Check if the user is a sudo user."""

        async def filter_(client: pyrogram.Client, message: pyrogram.types.Message) -> bool:
            user = message.from_user or message.sender_chat
            user_id = user.id
            return user_id == self.OWNER_ID or (user_id in self.context and self.context[user_id].get('is_sudo'))

        return filter_

    @property
    def blacklisted(self) -> Callable[[pyrogram.Client, pyrogram.types.Message], Coroutine[Any, Any, bool]]:
        """Check if the user is blacklisted."""

        async def filter_(client: pyrogram.Client, message: pyrogram.types.Message) -> bool:
            user = message.from_user or message.sender_chat
            user_id = user.id
            return user_id != self.OWNER_ID and user_id in self.context and self.context[user_id].get('is_blacklist')

        return filter_

    def __getattr__(self, name: str) -> Callable[[pyrogram.Client, pyrogram.types.Message], Coroutine[Any, Any, bool]]:
        """Return a filter by name."""
        return getattr(self, name)

