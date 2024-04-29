from telegram.ext import MessageFilter
from telegram import Message
from bot import user_data, OWNER_ID

class CustomFilters:
    """A class for creating custom filters for Telegram messages."""

    def __init_subclass__(cls):
        """Create a class method for checking if a user is an owner."""
        cls.owner_query = classmethod(lambda cls, uid: (uid == OWNER_ID) or (uid in user_data and user_data[uid].get('is_sudo')))

    class OwnerFilter(MessageFilter):
        """A filter for messages sent by the bot owner."""

        def filter(self, message: Message) -> bool:
            return message.from_user.id == OWNER_ID

    class AuthorizedUserFilter(MessageFilter):
        """A filter for messages sent by authorized users."""

        def filter(self, message: Message) -> bool:
            uid = message.from_user.id
            return uid == OWNER_ID or (uid in user_data and (user_data[uid].get('is_auth') or user_data[uid].get('is_sudo')))

    class AuthorizedChat(MessageFilter):
        """A filter for messages sent in authorized chats."""

        def filter(self, message: Message) -> bool:
            uid = message.chat.id
            return uid in user_data and user_data[uid].get('is_auth')

    class SudoUser(MessageFilter):
        """A filter for messages sent by sudo users."""

        def filter(self, message: Message) -> bool:
            uid = message.from_user.id
            return uid in user_data and user_data[uid].get('is_sudo')

    class PaidUser(MessageFilter):
        """A filter for messages sent by paid users."""

        def filter(self, message: Message) -> bool:
            uid = message.from_user.id
            return uid in user_data and user_data[uid].get('is_paid')
