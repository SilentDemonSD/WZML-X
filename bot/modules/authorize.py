#!/usr/bin/env python3
from pyrogram.handlers import MessageHandler
from pyrogram.filters import command, regex

from bot import user_data, DATABASE_URL, bot, LOGGER
from bot.helper.telegram_helper.message_utils import sendMessage
from bot.helper.telegram_helper.filters import CustomFilters
from bot.helper.telegram_helper.bot_commands import BotCommands
from bot.helper.ext_utils.db_handler import DbManger
from bot.helper.ext_utils.bot_utils import update_user_ldata


async def authorize(client, message):
    msg = message.text.split()
    tid_ = ""
    if len(msg) > 1:
        nid_ = msg[1].split(':')
        id_ = int(nid_[0])
        if len(nid_) > 1:
            tid_ = int(nid_[1])
    elif (reply_to := message.reply_to_message) and (reply_to.text is None and reply_to.caption is None):
        id_ = message.chat.id
        tid_ = message.reply_to_message_id
    elif reply_to:
        id_ = reply_to.from_user.id
    else:
        id_ = message.chat.id
    if id_ in user_data and user_data[id_].get('is_auth'):
        msg = 'Already Authorized!'
        if tid_:
            if tid_ not in (tids_ := user_data[id_].get('topic_ids', [])):
                tids_.append(tid_)
                update_user_ldata(id_, 'topic_ids', tids_)
                if DATABASE_URL:
                    await DbManger().update_user_data(id_)
                msg = 'Topic Authorized!'
            else:
                msg = 'Topic Already Authorized!'
    else:
        update_user_ldata(id_, 'is_auth', True)
        if tid_:
            update_user_ldata(id_, 'topic_ids', [tid_])
            msg = 'Topic Authorized!'
        else:
            msg = 'Authorized'
        if DATABASE_URL:
            await DbManger().update_user_data(id_)
    await sendMessage(message, msg)


async def unauthorize(client, message):
    msg = message.text.split()
    tid_ = ""
    if len(msg) > 1:
        nid_ = msg[1].split(':')
        id_ = int(nid_[0])
        if len(nid_) > 1:
            tid_ = int(nid_[1])
    elif (reply_to := message.reply_to_message) and (reply_to.text is None and reply_to.caption is None):
        id_ = message.chat.id
        tid_ = message.reply_to_message_id
    elif reply_to := message.reply_to_message:
        id_ = reply_to.from_user.id
    else:
        id_ = message.chat.id
    tids_ = []
    if tid_ and id_ in user_data and tid_ in (tids_ := user_data[id_].get('topic_ids', [])):
        tids_.remove(tid_)
        update_user_ldata(id_, 'topic_ids', tids_)
    if id_ not in user_data or user_data[id_].get('is_auth'):
        if not tids_:
            update_user_ldata(id_, 'is_auth', False)
        if DATABASE_URL:
            await DbManger().update_user_data(id_)
        msg = 'Unauthorized'
    else:
        msg = 'Already Unauthorized!'
    await sendMessage(message, msg)


async def addSudo(client, message):
    id_ = ""
    msg = message.text.split()
    if len(msg) > 1:
        id_ = int(msg[1].strip())
    elif reply_to := message.reply_to_message:
        id_ = reply_to.from_user.id
    if id_:
        if id_ in user_data and user_data[id_].get('is_sudo'):
            msg = 'Already Sudo!'
        else:
            update_user_ldata(id_, 'is_sudo', True)
            if DATABASE_URL:
                await DbManger().update_user_data(id_)
            msg = 'Promoted as Sudo'
    else:
        msg = "<i>Give User's ID or Reply to User's message of whom you want to Promote as Sudo</i>"
    await sendMessage(message, msg)


async def removeSudo(client, message):
    id_ = ""
    msg = message.text.split()
    if len(msg) > 1:
        id_ = int(msg[1].strip())
    elif reply_to := message.reply_to_message:
        id_ = reply_to.from_user.id
    if id_:
        if id_ in user_data and not user_data[id_].get('is_sudo'):
            msg = 'Not a Sudo User, Already Demoted'
        else:
            update_user_ldata(id_, 'is_sudo', False)
            if DATABASE_URL:
                await DbManger().update_user_data(id_)
            msg = 'Demoted'
    else:
        msg = "<i>Give User's ID or Reply to User's message of whom you want to Demote</i>"
    await sendMessage(message, msg)


async def addBlackList(_, message):
    id_ = ""
    msg = message.text.split()
    if len(msg) > 1:
        id_ = int(msg[1].strip())
    elif reply_to := message.reply_to_message:
        id_ = reply_to.from_user.id
    if id_:
        if id_ in user_data and user_data[id_].get('is_blacklist'):
            msg = 'User Already BlackListed!'
        else:
            update_user_ldata(id_, 'is_blacklist', True)
            if DATABASE_URL:
                await DbManger().update_user_data(id_)
            msg = 'User BlackListed'
    else:
        msg = "Give ID or Reply To message of whom you want to blacklist."
    await sendMessage(message, msg)


async def rmBlackList(_, message):
    id_ = ""
    msg = message.text.split()
    if len(msg) > 1:
        id_ = int(msg[1].strip())
    elif reply_to := message.reply_to_message:
        id_ = reply_to.from_user.id
    if id_:
        if id_ in user_data and not user_data[id_].get('is_blacklist'):
            msg = '<i>User Already Freed</i>'
        else:
            update_user_ldata(id_, 'is_blacklist', False)
            if DATABASE_URL:
                await DbManger().update_user_data(id_)
            msg = '<i>User Set Free as Bird!</i>'
    else:
        msg = "Give ID or Reply To message of whom you want to remove from blacklisted"
    await sendMessage(message, msg)
    
    
async def black_listed(_, message):
    await sendMessage(message, "<i>BlackListed Detected, Restricted from Bot</i>")
    
    
bot.add_handler(MessageHandler(authorize, filters=command(
    BotCommands.AuthorizeCommand) & CustomFilters.sudo))
bot.add_handler(MessageHandler(unauthorize, filters=command(
    BotCommands.UnAuthorizeCommand) & CustomFilters.sudo))
bot.add_handler(MessageHandler(addSudo, filters=command(
    BotCommands.AddSudoCommand) & CustomFilters.sudo))
bot.add_handler(MessageHandler(removeSudo, filters=command(
    BotCommands.RmSudoCommand) & CustomFilters.sudo))
bot.add_handler(MessageHandler(addBlackList, filters=command(
    BotCommands.AddBlackListCommand) & CustomFilters.sudo))
bot.add_handler(MessageHandler(rmBlackList, filters=command(
    BotCommands.RmBlackListCommand) & CustomFilters.sudo))
bot.add_handler(MessageHandler(black_listed, filters=regex(r'^/')
    & CustomFilters.authorized & CustomFilters.blacklisted))
    