from pyrogram import enums
from telegram.ext import Updater, CommandHandler, CallbackQueryHandler, ConversationHandler
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from bot import LOGGER, DB_URI, OWNER_ID, PRE_DICT, LEECH_DICT, dispatcher, PAID_USERS, CAP_DICT, PAID_SERVICE, REM_DICT, SUF_DICT
from bot.helper.telegram_helper.message_utils import *
from bot.helper.telegram_helper.filters import CustomFilters
from bot.helper.telegram_helper.bot_commands import BotCommands
from bot.helper.telegram_helper.button_build import ButtonMaker
from bot.helper.ext_utils.db_handler import DbManger


def prename_set(update, context):
    user_id_ = update.message.from_user.id 
    u_men = update.message.from_user.first_name

    if PAID_SERVICE is True:
        if not (user_id_ in PAID_USERS) and user_id_ != OWNER_ID:
            sendMessage(f"Buy Paid Service to Use this Prename Feature.", context.bot, update.message)
            return
    if (BotCommands.PreNameCommand in update.message.text) and (len(update.message.text.split(' ')) == 1):
        sendMessage(f'<b>Set Prename Like👇 \n/{BotCommands.PreNameCommand} channelName</b>', context.bot, update.message)
    else:
        lm = sendMessage(f"<b>Please Wait....Processing🤖</b>", context.bot, update.message)
        pre_send = update.message.text.split(" ", maxsplit=1)
        reply_to = update.message.reply_to_message
        if len(pre_send) > 1:
            txt = pre_send[1]
        elif reply_to is not None:
            txt = reply_to.text
        else:
            txt = ""
        prefix_ = txt
        PRE_DICT[user_id_] = prefix_
        if DB_URI:
            DbManger().user_pre(user_id_, prefix_)
            LOGGER.info(f"User : {user_id_} Prename is Saved in DB")
        editMessage(f"<b>{u_men} Prename for the Leech file is Set now🚀</b>\n\n<b>Your Prename Text: </b>{txt}", lm)


def suffix_set(update, context):
    user_id_ = update.message.from_user.id 
    u_men = update.message.from_user.first_name

    if PAID_SERVICE is True:
        if not (user_id_ in PAID_USERS) and user_id_ != OWNER_ID:
            sendMessage(f"Buy Paid Service to Use this Suffix Feature.", context.bot, update.message)
            return
    if (BotCommands.SufNameCommand in update.message.text) and (len(update.message.text.split(' ')) == 1):
        sendMessage(f'<b>Set Suffix Like👇 \n/{BotCommands.SufNameCommand} channelName</b>', context.bot, update.message)
    else:
        lm = sendMessage(f"<b>Please Wait....Processing🤖</b>", context.bot, update.message)
        pre_send = update.message.text.split(" ", maxsplit=1)
        reply_to = update.message.reply_to_message
        if len(pre_send) > 1:
            txt = pre_send[1]
        elif reply_to is not None:
            txt = reply_to.text
        else:
            txt = ""
        suffix_ = txt
        SUF_DICT[user_id_] = suffix_
        if DB_URI:
            DbManger().user_suf(user_id_, suffix_)
            LOGGER.info(f"User : {user_id_} Suffix is Saved in DB")
        editMessage(f"<b>{u_men} Suffix for the Leech file is Set now🚀</b>\n\n<b>Your Suffix Text: </b>{txt}", lm)



def caption_set(update, context):
    user_id_ = update.message.from_user.id 
    u_men = update.message.from_user.first_name

    if PAID_SERVICE is True:
        if not (user_id_ in PAID_USERS) and user_id_ != OWNER_ID:
            sendMessage(f"Buy Paid Service to Use this Caption Feature.", context.bot, update.message)
            return
    if (BotCommands.CaptionCommand in update.message.text) and (len(update.message.text.split(' ')) == 1):
        sendMessage(f'<b>Set Caption Like👇 \n/{BotCommands.CaptionCommand} text</b>', context.bot, update.message)
    else:
        lm = sendMessage(f"<b>Please Wait....Processing🤖</b>", context.bot, update.message)
        pre_send = update.message.text.split(" ", maxsplit=1)
        reply_to = update.message.reply_to_message
        if len(pre_send) > 1:
            txt = pre_send[1]
        elif reply_to is not None:
            txt = reply_to.text
        else:
            txt = ""
        caption_ = txt
        CAP_DICT[user_id_] = caption_
        if DB_URI:
            DbManger().user_cap(user_id_, caption_)
            LOGGER.info(f"User : {user_id_} Caption is Saved in DB")
        editMessage(f"<b>{u_men} Caption for the Leech file is Set now🌋</b>\n\n<b>Your Caption Text: </b>{txt}", lm)


def userlog_set(update, context):
    user_id_ = update.message.from_user.id 
    u_men = update.message.from_user.first_name

    if PAID_SERVICE is True:
        if not (user_id_ in PAID_USERS) and user_id_ != OWNER_ID:
            sendMessage(f"Buy Paid Service to Use this Dump Feature.", context.bot, update.message)
            return
    if (BotCommands.UserLogCommand in update.message.text) and (len(update.message.text.split(' ')) == 1):
        sendMessage(f'Send Your Backup Channel ID alone with command like \n\n{BotCommands.UserLogCommand} -100xxxxxxx', context.bot, update.message)
    else:
        lm = sendMessage("Please wait...🤖", context.bot, update.message)          
        pre_send = update.message.text.split(" ", maxsplit=1)
        reply_to = update.message.reply_to_message
        if len(pre_send) > 1:
            txt = pre_send[1]
        elif reply_to is not None:
            txt = reply_to.text
        else:
            txt = ""
        dumpid_ = txt
        LEECH_DICT[user_id_] = dumpid_
        if DB_URI:
            DbManger().user_dump(user_id_, dumpid_)
            LOGGER.info(f"User : {user_id_} LeechLog ID Saved in DB")
        editMessage(f"<b>{u_men} your Channel ID Saved...🛸</b>", lm)


def remname_set(update, context):
    user_id_ = update.message.from_user.id 
    u_men = update.message.from_user.first_name

    if PAID_SERVICE is True:
        if not (user_id_ in PAID_USERS) and user_id_ != OWNER_ID:
            sendMessage(f"Buy Paid Service to Use this Remname Feature.", context.bot, update.message)
            return
    if (BotCommands.RemnameCommand in update.message.text) and (len(update.message.text.split(' ')) == 1):
        sendMessage(f'<b>Set Remname Like👇 \n/{BotCommands.RemnameCommand} text, seperated with | </b>', context.bot, update.message)
    else:
        lm = sendMessage(f"<b>Please Wait....Processing🤖</b>", context.bot, update.message)
        pre_send = update.message.text.split(" ", maxsplit=1)
        reply_to = update.message.reply_to_message
        if len(pre_send) > 1:
            txt = pre_send[1]
        elif reply_to is not None:
            txt = reply_to.text
        else:
            txt = ""
        remname_ = txt
        REM_DICT[user_id_] = remname_
        if DB_URI:
            DbManger().user_rem(user_id_, remname_)
            LOGGER.info(f"User : {user_id_} Remname is Saved in DB")
        editMessage(f"<b>{u_men} Remname for the Leech file is Set now🌋</b>\n\n<b>Your Remname Text: </b>{txt}", lm)



prename_set_handler = CommandHandler(BotCommands.PreNameCommand, prename_set,
                                       filters=(CustomFilters.authorized_chat | CustomFilters.authorized_user), run_async=True)
suffix_set_handler = CommandHandler(BotCommands.SufNameCommand, suffix_set,
                                       filters=(CustomFilters.authorized_chat | CustomFilters.authorized_user), run_async=True)
caption_set_handler = CommandHandler(BotCommands.CaptionCommand, caption_set,
                                       filters=(CustomFilters.authorized_chat | CustomFilters.authorized_user), run_async=True)
userlog_set_handler = CommandHandler(BotCommands.UserLogCommand, userlog_set,
                                       filters=(CustomFilters.authorized_chat | CustomFilters.authorized_user), run_async=True)
remname_set_handler = CommandHandler(BotCommands.RemnameCommand, remname_set,
                                       filters=(CustomFilters.authorized_chat | CustomFilters.authorized_user), run_async=True) 

dispatcher.add_handler(prename_set_handler)
dispatcher.add_handler(suffix_set_handler)
dispatcher.add_handler(caption_set_handler)
dispatcher.add_handler(userlog_set_handler)
dispatcher.add_handler(remname_set_handler)
