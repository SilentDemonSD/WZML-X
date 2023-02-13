from pyrogram import filters
from bot import user_data, OWNER_ID


class CustomFilters():

    async def custom_owner_filer(self, client, message):
        return message.from_user.id == OWNER_ID

    owner_filter = filters.create(custom_owner_filer)

    async def custom_authorizedUser_filter(self, client, message):
        uid = message.from_user.id
        return uid == OWNER_ID or uid in user_data and (user_data[uid].get('is_auth') or user_data[uid].get('is_sudo'))

    authorized_user = filters.create(custom_authorizedUser_filter)

    async def custom_authorizedChat_filter(self, client, message):
        uid = message.chat.id
        return uid in user_data and user_data[uid].get('is_auth')

    authorized_chat = filters.create(custom_authorizedChat_filter)

    async def custom_sudoUser_filter(self, client, message):
        uid = message.from_user.id
        return uid in user_data and user_data[uid].get('is_sudo')

    sudo_user = filters.create(custom_sudoUser_filter)

    async def custom_paidUser_filter(self, client, message):
        uid = message.from_user.id
        return uid in user_data and user_data[uid].get('is_paid')

    paid_user = filters.create(custom_paidUser_filter)

    @staticmethod
    def owner_query(uid):
        return (uid == OWNER_ID) or (uid in user_data and user_data[uid].get('is_sudo'))
