from telegram.ext import CallbackQueryHandler
from bot import dispatcher

def save_message(update, context):
    """ By Junedkh ( https://github.com/junedkh/jmdkh-mltb ) """

    query = update.callback_query
    if query.data == "save":
        try:
            del query.message.reply_markup['inline_keyboard'][-1]
            query.message.copy(query.from_user.id, reply_markup=query.message.reply_markup)
            query.answer('Message Saved Successfully, Check Bot PM', show_alert=True)
        except:
            query.answer('Start the Bot in Private and Try Again', show_alert=True)

msgsave_handler = CallbackQueryHandler(save_message, pattern="save")
dispatcher.add_handler(msgsave_handler)
