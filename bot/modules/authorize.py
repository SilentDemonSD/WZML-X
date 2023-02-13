from pyrogram import filters, Client
from pyrogram.types import Message

from bot import user_data, bot, DATABASE_URL
from bot.helper.telegram_helper.message_utils import sendMessage
from bot.helper.telegram_helper.filters import CustomFilters
from bot.helper.telegram_helper.bot_commands import BotCommands
from bot.helper.ext_utils.db_handler import DbManger
from bot.helper.ext_utils.bot_utils import update_user_ldata, is_paid, is_sudo


@bot.on_message(filters.command(BotCommands.AuthorizeCommand) & (CustomFilters.owner_filter | CustomFilters.sudo_user))
async def authorize(c: Client, m: Message):
    reply_message = m.reply_to_message
    if len(m.command) == 2:
        id_ = int(m.command[1])
    elif reply_message:
        id_ = reply_message.from_user.id
    else:
        id_ = m.chat.id
    if id_ in user_data and user_data[id_].get('is_auth'):
        msg = 'Already Authorized!'
    else:
        update_user_ldata(id_, 'is_auth', True)
        if DATABASE_URL:
            DbManger().update_user_data(id_)
        msg = 'Authorized'
    await sendMessage(msg, c, m)


@bot.on_message(filters.command(BotCommands.UnAuthorizeCommand) & (CustomFilters.owner_filter | CustomFilters.sudo_user))
async def unauthorize(c: Client, m: Message):
    reply_message = m.reply_to_message
    if len(m.command) == 2:
        id_ = int(m.command[1])
    elif reply_message:
        id_ = reply_message.from_user.id
    else:
        id_ = m.chat.id
    if id_ not in user_data or user_data[id_].get('is_auth'):
        update_user_ldata(id_, 'is_auth', False)
        if DATABASE_URL:
            DbManger().update_user_data(id_)
        msg = 'Unauthorized'
    else:
        msg = 'Already Unauthorized!'
    await sendMessage(msg, c, m)


@bot.on_message(filters.command(BotCommands.AddSudoCommand) & CustomFilters.owner_filter)
async def addSudo(c: Client, m: Message):
    id_ = ""
    reply_message = m.reply_to_message
    if len(m.command) == 2:
        id_ = int(m.command[1])
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
    await sendMessage(msg, c, m)


@bot.on_message(filters.command(BotCommands.RmSudoCommand) & CustomFilters.owner_filter)
async def removeSudo(c: Client, m: Message):
    id_ = ""
    reply_message = m.reply_to_message
    if len(m.command) == 2:
        id_ = int(m.command[1])
    elif reply_message:
        id_ = reply_message.from_user.id
    if id_ and is_sudo(id_):
        update_user_ldata(id_, 'is_sudo', False)
        if DATABASE_URL:
            DbManger().update_user_data(id_)
        msg = 'Demoted'
    else:
        msg = "Give ID or Reply To message of whom you want to remove from Sudo"
    await sendMessage(msg, c, m)


@bot.on_message(filters.command(BotCommands.AddPaidCommand) & (CustomFilters.owner_filter | CustomFilters.sudo_user))
async def addPaid(c: Client, m: Message):
    id_, ex_date = "", ""
    reply_message = m.reply_to_message
    if len(m.command) == 3:
        id_ = int(m.command[1])
        ex_date = m.command[2]
    elif len(m.command) == 2 and reply_message:
        ex_date = m.command[1]
        id_ = reply_message.from_user.id
    elif reply_message:
        id_ = reply_message.from_user.id
        ex_date = False
    elif len(m.command) == 2:
        id_ = int(m.command[1])
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
    await sendMessage(msg, c, m)


@bot.on_message(filters.command(BotCommands.RmPaidCommand) & (CustomFilters.owner_filter | CustomFilters.sudo_user))
async def removePaid(c: Client, m: Message):
    id_ = ""
    reply_message = m.reply_to_message
    if len(m.command) == 2:
        id_ = int(m.command[1])
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
    await sendMessage(msg, c, m)
