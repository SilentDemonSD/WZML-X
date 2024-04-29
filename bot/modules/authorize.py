import logging
from typing import Optional

from telegram.ext import CommandHandler
from bot import user_data, dispatcher, DATABASE_URL
from bot.helper.telegram_helper.message_utils import sendMessage
from bot.helper.telegram_helper.filters import CustomFilters
from bot.helper.telegram_helper.bot_commands import BotCommands
from bot.helper.ext_utils.db_handler import DbManger
from bot.helper.ext_utils.bot_utils import is_paid, is_sudo, update_user_ldata
import logging

def authorize(update, context):
    """Authorizes a user.

    Args:
        update (telegram.Update): The update object containing the message.
        context (telegram.ext.CallbackContext): The context object containing the dispatcher, update and user data.

    Returns:
        None
    """
    reply_message = update.message.reply_to_message
    user_id: Optional[int] = None
    if len(context.args) == 1:
        user_id = context.args[0]
    elif reply_message:
        user_id = reply_message.from_user.id
    else:
        user_id = update.effective_chat.id

    if user_id in user_data and user_data[user_id].get('is_auth'):
        msg = 'Already Authorized 🔰'
    else:
        try:
            update_user_ldata(user_id, 'is_auth', True)
            if DATABASE_URL:
                DbManger().update_user_data(user_id)
            msg = 'Successfully Authorized 🔰'
        except Exception as e:
            logging.error(e)
            msg = 'An error occurred while authorizing the user.'

    sendMessage(msg, context.bot, update.message)

def unauthorize(update, context):
    """Unauthorizes a user.

    Args:
        update (telegram.Update): The update object containing the message.
        context (telegram.ext.CallbackContext): The context object containing the dispatcher, update and user data.

    Returns:
        None
    """
    reply_message = update.message.reply_to_message
    user_id: Optional[int] = None
    if len(context.args) == 1:
        user_id = context.args[0]
    elif reply_message:
        user_id = reply_message.from_user.id
    else:
        user_id = update.effective_chat.id

    if user_id not in user_data or not user_data[user_id].get('is_auth'):
        msg = 'Unauthorized 🚫'
    else:
        try:
            update_user_ldata(user_id, 'is_auth', False)
            if DATABASE_URL:
                DbManger().update_user_data(user_id)
            msg = 'Successfully Unauthorized 🚫'
        except Exception as e:
            logging.error(e)
            msg = 'An error occurred while unauthorizing the user.'

    sendMessage(msg, context.bot, update.message)

def addSudo(update, context):
    """Adds sudo access to a user.

    Args:
        update (telegram.Update): The update object containing the message.
        context (telegram.ext.CallbackContext): The context object containing the dispatcher, update and user data.

    Returns:
        None
    """
    reply_message = update.message.reply_to_message
    user_id: Optional[int] = None
    if len(context.args) == 1:
        user_id = context.args[0]
    elif reply_message:
        user_id = reply_message.from_user.id

    if user_id and is_sudo(user_id):
        msg = 'Already Sudo 🔰'
    else:
        try:
            update_user_ldata(user_id, 'is_sudo', True)
            if DATABASE_URL:
                DbManger().update_user_data(user_id)
            msg = 'Promoted as Sudo 🔰'
        except Exception as e:
            logging.error(e)
            msg = 'An error occurred while promoting the user as sudo.'

    if not user_id:
        msg = "Give ID or Reply To message of whom you want to Promote."

    sendMessage(msg, context.bot, update.message)

def removeSudo(update, context):
    """Removes sudo access from a user.

    Args:
        update (telegram.Update): The update object containing the message.
        context (telegram.ext.CallbackContext): The context object containing the dispatcher, update and user data.

    Returns:
        None
    """
    reply_message = update.message.reply_to_message
    user_id: Optional[int] = None
    if len(context.args) == 1:
        user_id = context.args[0]
    elif reply_message:
        user_id = reply_message.from_user.id

    if user_id and is_sudo(user_id):
        try:
            update_user_ldata(user_id, 'is_sudo', False)
            if DATABASE_URL:
                DbManger().update_user_data(user_id)
            msg = 'Demoted 🚫'
        except Exception as e:
            logging.error(e)
            msg = 'An error occurred while demoting the user.'
    else:
        msg = "Give ID or Reply To message of whom you want to remove from Sudo"

    sendMessage(msg, context.bot, update.message)

def addPaid(update, context):
    """Adds paid access to a user.

    Args:
        update (telegram.Update): The update object containing the message.
        context (telegram.ext.CallbackContext): The context object containing the dispatcher, update and user data.

    Returns:
        None
    """
    reply_message = update.message.reply_to_message
    user_id: Optional[int] = None
    expiry_date: Optional[str] = None
    if len(context.args) == 2:
        user_id = context.args[0]
        expiry_date = context.args[1]
    elif len(context.args) == 1 and reply_message:
        expiry_date = context.args[0]
        user_id = reply_message.from_user.id
    elif reply_message:
        user_id = reply_message.from_user.id
        expiry_date = False
    elif len(context.args) == 1:
        user_id = int(context.args[0])
        expiry_date = False

    if user_id:
        is_paid_user = is_paid(user_id)
        if is_paid_user and expiry_date and user_data[user_id].get('expiry_date') and (expiry_date == user_data[user_id].get('expiry_date')):
            msg = 'Already a Paid User!'
        else:
            try:
                update_user_ldata(user_id, 'is_paid', True)
                update_user_ldata(user_id, 'expiry_date', expiry_date)
                if DATABASE_URL:
                    DbManger().update_user_data(user_id)
                msg = 'Promoted as Paid User'
            except Exception as e:
                logging.error(e)
                msg = 'An error occurred while promoting the user as paid.'
    else:
        msg = "Give ID and Expiry Date or Reply To message of whom you want to Promote as Paid User"

    sendMessage(msg, context.bot, update.message)

def removePaid(update, context):
    """Removes paid access from a user.

    Args:
        update (telegram.Update): The update object containing the message.
        context (telegram.ext.CallbackContext): The context object containing the dispatcher, update and user data.

    Returns:
        None
    """
    reply_message = update.message.reply_to_message
    user_id: Optional[int] = None
    if len(context.args) == 1:
        user_id = int(context.args[0])
    elif reply_message:
        user_id = reply_message.from_user.id

    if user_id and is_paid(user_id):
        try:
            update_user_ldata(user_id, 'is_paid', False)
            update_user_ldata(user_id, 'expiry_date', False)
            if DATABASE_URL:
                DbManger().update_user_data(user_id)
            msg = 'Demoted'
        except Exception as e:
            logging.error(e)
            msg = 'An error occurred while demoting the user.'
    else:
        msg = "Give ID or Reply To message of whom you want to remove from Paid User"

    sendMessage(msg, context.bot, update.message)

authorize_handler = CommandHandler(BotCommands.AuthorizeCommand, authorize,
                                   filters=CustomFilters.owner_filter | CustomFilters.sudo_user)
unauthorize_handler = CommandHandler(BotCommands.UnAuthorizeCommand, unauthorize,
                                   filters=CustomFilters.owner_filter | CustomFilters.sudo_user)
addsudo_handler = CommandHandler(BotCommands.AddSudoCommand, addSudo,
                                   filters=CustomFilters.owner_filter)
removesudo_handler = CommandHandler(BotCommands.RmSudoCommand, removeSudo,
                                   filters=CustomFilters.owner_filter)
addpaid_handler = CommandHandler(BotCommands.AddPaidCommand, addPaid,
                                    filters=CustomFilters.owner_filter)
removepaid_handler = CommandHandler(BotCommands.RmPaidCommand, removePaid,
                                    filters=CustomFilters.owner_filter)

dispatcher.add_handler(authorize_handler)
dispatcher.add_handler(unauthorize_handler)
dispatcher.add_handler(addsudo_handler)
dispatcher.add_handler(removesudo_handler)
dispatcher.add_handler(addpaid_handler)
dispatcher.add_handler(removepaid_handler)
