from os import remove as osremove, path as ospath, mkdir
from sys import prefix
from threading import Thread
from PIL import Image
from telegram.ext import CommandHandler, CallbackQueryHandler

from bot import user_data, dispatcher, AS_DOCUMENT, DB_URI
from bot.helper.telegram_helper.message_utils import sendMessage, sendMarkup, editMessage, sendPhoto
from bot.helper.telegram_helper.filters import CustomFilters
from bot.helper.telegram_helper.bot_commands import BotCommands
from bot.helper.telegram_helper.button_build import ButtonMaker
from bot.helper.ext_utils.db_handler import DbManger
from bot.helper.ext_utils.bot_utils import update_user_ldata


def getleechinfo(from_user):
    user_id = from_user.id
    name = from_user.full_name
    buttons = ButtonMaker()
    thumbpath = f"Thumbnails/{user_id}.jpg"
    prefix = user_data[user_id]['prefix'] if user_id in user_data and user_data[user_id].get('prefix') else "Not Exists"
    suffix = user_data[user_id]['suffix'] if user_id in user_data and user_data[user_id].get('suffix') else "Not Exists"
    caption = user_data[user_id]['caption'] if user_id in user_data and user_data[user_id].get('caption') else "Not Exists"
    userlog = user_data[user_id]['userlog'] if user_id in user_data and user_data[user_id].get('userlog') else "Not Exists"
    remname = user_data[user_id]['remname'] if user_id in user_data and user_data[user_id].get('remname') else "Not Exists"
    cfont = user_data[user_id]['cfont'][0] if user_id in user_data and user_data[user_id].get('cfont') else "Not Exists"
    user_dict = user_data.get(user_id, False)
    if not user_dict and AS_DOCUMENT or user_dict and user_dict.get('as_doc'):
        ltype = "DOCUMENT"
        buttons.sbutton("Send As Media", f"leechset {user_id} med")
    else:
        ltype = "MEDIA"
        buttons.sbutton("Send As Document", f"leechset {user_id} doc")
        
    uplan = "Paid User" if user_id in user_data and (user_data[user_id].get('is_paid')) else "Normal User"

    if ospath.exists(thumbpath):
        thumbmsg = "Exists"
        buttons.sbutton("Delete Thumbnail", f"leechset {user_id} thumb")
        buttons.sbutton("Show Thumbnail", f"leechset {user_id} showthumb")
    else:
        thumbmsg = "Not Exists"
    if prefix != "Not Exists":
        buttons.sbutton("Delete Prename", f"leechset {user_id} prefix")
    if suffix != "Not Exists":
        buttons.sbutton("Delete Suffix", f"leechset {user_id} suffix")
    if caption != "Not Exists": 
        buttons.sbutton("Delete Caption", f"leechset {user_id} cap")
    if userlog != "Not Exists":
        buttons.sbutton("Delete UserLog", f"leechset {user_id} ulog")
    if remname != "Not Exists": 
        buttons.sbutton("Delete Remname", f"leechset {user_id} rem")
    if cfont != "Not Exists": 
        buttons.sbutton("Delete CapFont", f"leechset {user_id} cfont")

    buttons.sbutton("Close", f"leechset {user_id} close")
    button = buttons.build_menu(2)

    text = f'''<u>Leech Settings for <a href='tg://user?id={user_id}'>{name}</a></u>
    
• Leech Type : <b>{ltype}</b>
• Custom Thumbnail : <b>{thumbmsg}</b>
• Prefix : <b>{prefix}</b>
• Suffix : <b>{suffix}</b>
• Caption : <b>{caption}</b>
• CapFont : <b>{cfont}</b>
• Remname : <b>{remname}</b>
• UserLog : <b>{userlog}</b>
• User Plan : <b>{uplan}</b>'''
    return text, button

def editLeechType(message, query):
    msg, button = getleechinfo(query.from_user)
    editMessage(msg, message, button)

def leechSet(update, context):
    msg, button = getleechinfo(update.message.from_user)
    choose_msg = sendMarkup(msg, context.bot, update.message, button)
    Thread(args=(context.bot, update.message, choose_msg)).start()

def setLeechType(update, context):
    query = update.callback_query
    message = query.message
    user_id = query.from_user.id
    data = query.data
    data = data.split()
    if user_id != int(data[1]):
        query.answer(text="Not Yours!", show_alert=True)
    elif data[2] == "doc":
        update_user_ldata(user_id, 'as_doc', True)
        if DB_URI is not None:
            DbManger().update_user_data(user_id)
        query.answer(text="Your File Will Deliver As Document!", show_alert=True)
        editLeechType(message, query)
    elif data[2] == "med":
        update_user_ldata(user_id, 'as_doc', False)
        if DB_URI is not None:
            DbManger().update_user_data(user_id)
        query.answer(text="Your File Will Deliver As Media!", show_alert=True)
        editLeechType(message, query)

    elif data[2] == "thumb":
        path = f"Thumbnails/{user_id}.jpg"
        if ospath.lexists(path):
            osremove(path)
            update_user_ldata(user_id, 'thumb', False)
            if DB_URI is not None:
                DbManger().update_thumb(user_id)
            query.answer(text="Thumbnail Removed!", show_alert=True)
            editLeechType(message, query)
        else:
            query.answer(text="Old Settings", show_alert=True)
    elif data[2] == "showthumb":
        path = f"Thumbnails/{user_id}.jpg"
        if ospath.lexists(path):
            msg = f"Thumbnail for: {query.from_user.mention_html()} (<code>{str(user_id)}</code>)"
            delo = sendPhoto(text=msg, bot=context.bot, message=message, photo=open(path, 'rb'))
            Thread(args=(context.bot, update.message, delo)).start()
        else: query.answer(text="Send new settings command.")
    elif data[2] == "prefix":
        update_user_ldata(user_id, 'prefix', False)
        if DB_URI: 
            DbManger().update_userval(user_id, 'prefix')
        query.answer(text="Your Prefix is Successfully Deleted!", show_alert=True)
        editLeechType(message, query)
    elif data[2] == "suffix":
        update_user_ldata(user_id, 'suffix', False)
        if DB_URI: 
            DbManger().update_userval(user_id, 'suffix')
        query.answer(text="Your Suffix is Successfully Deleted!", show_alert=True)
        editLeechType(message, query)
    elif data[2] == "cap":
        update_user_ldata(user_id, 'caption', False)
        if DB_URI: 
            DbManger().update_userval(user_id, 'caption')
        query.answer(text="Your Caption is Successfully Deleted!", show_alert=True)
        editLeechType(message, query)
    elif data[2] == "rem":
        update_user_ldata(user_id, 'remname', False)
        if DB_URI: 
            DbManger().update_userval(user_id, 'remname')
        query.answer(text="Your Remname is Successfully Deleted!", show_alert=True)
        editLeechType(message, query)
    elif data[2] == "ulog":
        update_user_ldata(user_id, 'userlog', False)
        if DB_URI: 
            DbManger().update_userval(user_id, 'userlog')
        query.answer(text="Your UserLog is Successfully Deleted!", show_alert=True)
        editLeechType(message, query)
    elif data[2] == "cfont":
        update_user_ldata(user_id, 'cfont', False)
        if DB_URI: 
            DbManger().update_userval(user_id, 'cfont')
        query.answer(text="Your Caption Font is Successfully Deleted!", show_alert=True)
        editLeechType(message, query)
    else:
        query.answer()
        query.message.delete()
        query.message.reply_to_message.delete()

def setThumb(update, context):
    reply_to = update.message.reply_to_message
    if reply_to is not None and reply_to.photo:
        path = "Thumbnails/"
        if not ospath.isdir(path):
            mkdir(path)
        photo_dir = reply_to.photo[-1].get_file().download()
        user_id = update.message.from_user.id
        des_dir = ospath.join(path, f'{user_id}.jpg')
        Image.open(photo_dir).convert("RGB").save(des_dir, "JPEG")
        osremove(photo_dir)
        update_user_ldata(user_id, 'thumb', True)
        if DB_URI is not None:
            DbManger().update_thumb(user_id, des_dir)
        msg = f"Custom thumbnail saved for {update.message.from_user.mention_html(update.message.from_user.first_name)}."
        sendMessage(msg, context.bot, update.message)
    else:
        sendMessage("Reply to a photo to save custom thumbnail.", context.bot, update.message)

def sendUsersSettings(update, context):
    msg = ''.join(f'<code>{u}</code>: {d}\n' for u, d in user_data.items())
    sendMessage(msg, context.bot, update.message)

users_settings_handler = CommandHandler(BotCommands.UsersCommand, sendUsersSettings,
                                            filters=CustomFilters.owner_filter | CustomFilters.sudo_user, run_async=True)
leech_set_handler = CommandHandler(BotCommands.UserSetCommand, leechSet,
                                   filters=CustomFilters.authorized_chat | CustomFilters.authorized_user, run_async=True)
set_thumb_handler = CommandHandler(BotCommands.SetThumbCommand, setThumb,
                                   filters=CustomFilters.authorized_chat | CustomFilters.authorized_user, run_async=True)
but_set_handler = CallbackQueryHandler(setLeechType, pattern="leechset", run_async=True)

dispatcher.add_handler(leech_set_handler)
dispatcher.add_handler(but_set_handler)
dispatcher.add_handler(set_thumb_handler)
dispatcher.add_handler(users_settings_handler)
