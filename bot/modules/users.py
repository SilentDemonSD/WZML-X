from pymongo import MongoClient
from telegram.ext import CommandHandler, Filters

from bot import bot, dispatcher, LOGGER, config_dict
from bot.helper.telegram_helper.filters import CustomFilters
from bot.helper.telegram_helper.message_utils import sendMessage

def broadcast(update, context):
    reply_to = update.message.reply_to_message

    if not config_dict['DATABASE_URL']:
        context.bot.send_message(chat_id=update.effective_chat.id, text=f"DATABASE_URL not provided")
    else:
        conn = MongoClient(config_dict['DATABASE_URL'])
        db = conn.mltb
        users_collection = db.users
        users_count = db.users.count_documents({})
    
        chat_ids = [str(user["_id"]) for user in users_collection.find({}, {"_id": 1})]
        success = 0
        
        for chat_id in chat_ids:
            try:
                context.bot.copy_message(chat_id=chat_id, from_chat_id=update.message.chat.id, message_id=reply_to.message_id)
                success += 1
            except Exception as err:
                LOGGER.error(err)

        msg = f"<b>Broadcasting Completed</b>\n"
        msg += f"<b>Total {users_count} users in Database</b>\n"
        msg += f"<b>Sucess: </b>{success} users\n"
        msg += f"<b>Failed: </b>{users_count - success} users"
        return sendMessage(msg, context.bot, update.message) 

broadcast_handler = CommandHandler("broadcast", broadcast, filters=CustomFilters.owner_filter)
dispatcher.add_handler(broadcast_handler)