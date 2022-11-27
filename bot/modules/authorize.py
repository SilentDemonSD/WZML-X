from telegram.ext import CommandHandler
from bot import user_data, dispatcher, DATABASE_URL
from bot.helper.telegram_helper.message_utils import sendMessage
from bot.helper.telegram_helper.filters import CustomFilters
from bot.helper.telegram_helper.bot_commands import BotCommands
from bot.helper.ext_utils.db_handler import DbManger
from bot.helper.ext_utils.bot_utils import update_user_ldata, is_paid, is_sudo

def authorize(update, context):
    reply_message = update.message.reply_to_message
    if len(context.args) == 1:
        id_ = int(context.args[0])
    elif reply_message:
        id_ = reply_message.from_user.id
    else:
        id_ = update.effective_chat.id
    if id_ in user_data and user_data[id_].get('is_auth'):
        msg = 'Already Authorized!'
    else:
        update_user_ldata(id_, 'is_auth', True)
        if DATABASE_URL:
            DbManger().update_user_data(id_)
        msg = 'Authorized'
    sendMessage(msg, context.bot, update.message)

def unauthorize(update, context):
    reply_message = update.message.reply_to_message
    if len(context.args) == 1:
        id_ = int(context.args[0])
    elif reply_message:
        id_ = reply_message.from_user.id
    else:
        id_ = update.effective_chat.id
    if id_ not in user_data or user_data[id_].get('is_auth'):
        update_user_ldata(id_, 'is_auth', False)
        if DATABASE_URL:
            DbManger().update_user_data(id_)
        msg = 'Unauthorized'
    else:
        msg = 'Already Unauthorized!'
    sendMessage(msg, context.bot, update.message)

def addSudo(update, context):
    id_ = ""
    reply_message = update.message.reply_to_message
    if len(context.args) == 1:
        id_ = int(context.args[0])
    elif reply_message:
        id_ = reply_message.from_user.id
    if id_:
        if is_sudo(id_):
            msg = 'Already Sudo! 🤔'
        else:
            update_user_ldata(id_, 'is_sudo', True)
            if DATABASE_URL:
                DbManger().update_user_data(id_)
            msg = 'Promoted as Sudo 🤣'
    else:
        msg = "Give ID or Reply To message of whom you want to Promote."
    sendMessage(msg, context.bot, update.message)

def removeSudo(update, context):
    id_ = ""
    reply_message = update.message.reply_to_message
    if len(context.args) == 1:
        id_ = int(context.args[0])
    elif reply_message:
        id_ = reply_message.from_user.id
    if id_ and is_sudo(id_):
        update_user_ldata(id_, 'is_sudo', False)
        if DATABASE_URL:
            DbManger().update_user_data(id_)
        msg = 'Demoted'
    else:
        msg = "Give ID or Reply To message of whom you want to remove from Sudo"
    sendMessage(msg, context.bot, update.message)

def addleechlog(update, context):
    reply_message = update.message.reply_to_message
    if len(context.args) == 1:
        id_ = int(context.args[0])
    elif reply_message:
        id_ = reply_message.from_user.id
    else:
        id_ = update.effective_chat.id
    if 'is_leech_log' in user_data and id_ in user_data['is_leech_log']:
        msg = 'Already Authorized!'
    else:
        #update_user_ldata('is_leech_log', id_, list=True) #ToDo
        if 'is_leech_log' in user_data:
            user_data['is_leech_log'].append(id_)
        else:
            user_data['is_leech_log'] = [id_]
        if DATABASE_URL:
            DbManger().update_user_data(id_)
        msg = 'Authorized'
    sendMessage(msg, context.bot, update.message)

def rmleechlog(update, context):
    reply_message = update.message.reply_to_message
    if len(context.args) == 1:
        id_ = int(context.args[0])
    elif reply_message:
        id_ = reply_message.from_user.id
    else:
        id_ = update.effective_chat.id
    if 'is_leech_log' in user_data and id_ in user_data['is_leech_log']:
        #update_user_ldata(id_, 'is_leech_log', False)
        user_data['is_leech_log'].remove(id_)
        if DATABASE_URL:
            DbManger().update_user_data(id_)
        msg = 'Unauthorized'
    else:
        msg = 'Already Unauthorized!'
    sendMessage(msg, context.bot, update.message)

def addPaid(update, context):
    id_, ex_date = "", ""
    reply_message = update.message.reply_to_message
    if len(context.args) == 2:
        id_ = int(context.args[0])
        ex_date = context.args[1]
    elif len(context.args) == 1 and reply_message:
        ex_date = context.args[0]
        id_ = reply_message.from_user.id
    elif reply_message:
        id_ = reply_message.from_user.id
        ex_date = False
    elif len(context.args) == 1:
        id_ = int(context.args[0])
        ex_date = False
    if id_:
        if is_paid(id_) and ex_date and user_data[id_].get('expiry_date') and (ex_date == user_data[id_].get('expiry_date')):
            msg = 'Already a Paid User!'
        else:
            update_user_ldata(id_, 'is_paid', True)
            update_user_ldata(id_, 'expiry_date', ex_date)
            if DATABASE_URL:
                DbManger().update_user_data(id_)
            msg = 'Promoted as Paid User'
    else:
        msg = "Give ID and Expiry Date or Reply To message of whom you want to Promote as Paid User"
    sendMessage(msg, context.bot, update.message)

def removePaid(update, context):
    id_ = ""
    reply_message = update.message.reply_to_message
    if len(context.args) == 1:
        id_ = int(context.args[0])
    elif reply_message:
        id_ = reply_message.from_user.id
    if id_ and is_paid(id_):
        update_user_ldata(id_, 'is_paid', False)
        update_user_ldata(id_, 'expiry_date', False)
        if DATABASE_URL:
            DbManger().update_user_data(id_)
        msg = 'Demoted'
    else:
        msg = "Give ID or Reply To message of whom you want to remove from Paid User"
    sendMessage(msg, context.bot, update.message)



authorize_handler = CommandHandler(BotCommands.AuthorizeCommand, authorize,
                                   filters=CustomFilters.owner_filter | CustomFilters.sudo_user, run_async=True)
unauthorize_handler = CommandHandler(BotCommands.UnAuthorizeCommand, unauthorize,
                                   filters=CustomFilters.owner_filter | CustomFilters.sudo_user, run_async=True)
addsudo_handler = CommandHandler(BotCommands.AddSudoCommand, addSudo,
                                   filters=CustomFilters.owner_filter, run_async=True)
removesudo_handler = CommandHandler(BotCommands.RmSudoCommand, removeSudo,
                                   filters=CustomFilters.owner_filter, run_async=True)


addleechlog_handler = CommandHandler(BotCommands.AddleechlogCommand, addleechlog,
                                    filters=CustomFilters.owner_filter | CustomFilters.sudo_user, run_async=True)
rmleechlog_handler = CommandHandler(BotCommands.RmleechlogCommand, rmleechlog,
                                    filters=CustomFilters.owner_filter | CustomFilters.sudo_user, run_async=True)
addpaid_handler = CommandHandler(BotCommands.AddPaidCommand, addPaid,
                                    filters=CustomFilters.owner_filter, run_async=True)
removepaid_handler = CommandHandler(BotCommands.RmPaidCommand, removePaid,
                                    filters=CustomFilters.owner_filter, run_async=True)


dispatcher.add_handler(authorize_handler)
dispatcher.add_handler(unauthorize_handler)
dispatcher.add_handler(addsudo_handler)
dispatcher.add_handler(removesudo_handler)
dispatcher.add_handler(addleechlog_handler)
dispatcher.add_handler(rmleechlog_handler)
dispatcher.add_handler(addpaid_handler)
dispatcher.add_handler(removepaid_handler)
