from pymongo import MongoClient
from random import choice as rchoice
from telegram.ext import CommandHandler

from bot import config_dict, dispatcher, OWNER_ID
from bot.helper.telegram_helper.filters import CustomFilters
from bot.helper.telegram_helper.bot_commands import BotCommands
from bot.helper.telegram_helper.message_utils import sendMessage, sendPhoto

def dbusers(update, context):
    if not config_dict['DATABASE_URL']:
        context.bot.send_message(chat_id=update.effective_chat.id, text=f"DATABASE_URL not provided")
    else:
        conn = MongoClient(config_dict['DATABASE_URL'])
        db = conn.mltb
        users_count = db.users.count_documents({})
        context.bot.send_message(chat_id=update.effective_chat.id, text=f"Total users in database: {users_count}")

def get_id(update, context):
    chat_id = update.effective_chat.id
    if update.effective_chat.type == 'private':
        user_id = update.message.from_user.id
        context.bot.send_message(chat_id=user_id, text=f"Your user ID is: <code>{user_id}</code>")
    else:
        context.bot.send_message(chat_id=chat_id, text=f"This group's ID is: <code>{chat_id}</code>")

def bot_limit(update, context):
    TORRENT_DIRECT_LIMIT = config_dict['TORRENT_DIRECT_LIMIT']
    CLONE_LIMIT = config_dict['CLONE_LIMIT']
    MEGA_LIMIT = config_dict['MEGA_LIMIT']
    LEECH_LIMIT = config_dict['LEECH_LIMIT']
    ZIP_UNZIP_LIMIT = config_dict['ZIP_UNZIP_LIMIT']
    TOTAL_TASKS_LIMIT = config_dict['TOTAL_TASKS_LIMIT']
    USER_TASKS_LIMIT = config_dict['USER_TASKS_LIMIT']

    torrent_direct = 'No Limit Set' if TORRENT_DIRECT_LIMIT == '' else f'{TORRENT_DIRECT_LIMIT}GB/Link'
    clone_limit = 'No Limit Set' if CLONE_LIMIT == '' else f'{CLONE_LIMIT}GB/Link'
    mega_limit = 'No Limit Set' if MEGA_LIMIT == '' else f'{MEGA_LIMIT}GB/Link'
    leech_limit = 'No Limit Set' if LEECH_LIMIT == '' else f'{LEECH_LIMIT}GB/Link'
    zip_unzip = 'No Limit Set' if ZIP_UNZIP_LIMIT == '' else f'{ZIP_UNZIP_LIMIT}GB/Link'
    total_task = 'No Limit Set' if TOTAL_TASKS_LIMIT == '' else f'{TOTAL_TASKS_LIMIT} Total Tasks/Time'
    user_task = 'No Limit Set' if USER_TASKS_LIMIT == '' else f'{USER_TASKS_LIMIT} Tasks/user'

    limit = f"<b>BOT LIMITATIONS:</b>\n\n"\
                f"<b>• Torrent-Direct:</b> {torrent_direct}\n"\
                f"<b>• Zip-Unzip:</b> {zip_unzip}\n"\
                f"<b>• Leech:</b> {leech_limit}\n"\
                f"<b>• Clone:</b> {clone_limit}\n"\
                f"<b>• Mega:</b> {mega_limit}\n"\
                f"<b>• Total Tasks:</b> {total_task}\n"\
                f"<b>• User Tasks:</b> {user_task}\n\n"

    if config_dict['PICS']:
        sendPhoto(limit, context.bot, update.message, rchoice(config_dict['PICS']))
    else:
        sendMessage(limit, context.bot, update.message)



limit_handler = CommandHandler(BotCommands.LimitCommand, bot_limit, filters=CustomFilters.authorized_chat | CustomFilters.authorized_user)
dbusers_handler = CommandHandler("dbusers", dbusers, filters=CustomFilters.owner_filter | CustomFilters.sudo_user)
id_handler = CommandHandler("id", get_id)

dispatcher.add_handler(dbusers_handler)
dispatcher.add_handler(id_handler)
dispatcher.add_handler(limit_handler)
