from threading import Thread
from telegram.ext import CommandHandler, CallbackQueryHandler

from bot import bot, ulist_listener, LOGGER, dispatcher, config_dict, user_data
from bot.helper.mirror_utils.upload_utils.gdriveTools import GoogleDriveHelper
from bot.helper.ext_utils.bot_utils import handleIndex
from bot.helper.telegram_helper.message_utils import sendMessage, editMessage, sendMessage, sendFile, deleteMessage
from bot.helper.telegram_helper.filters import CustomFilters
from bot.helper.telegram_helper.bot_commands import BotCommands
from bot.helper.telegram_helper.button_build import ButtonMaker

list_listener = {}

def common_btn(isRecur, msg_id):
    buttons = ButtonMaker()
    buttons.sbutton("Folders", f"types folders {msg_id}")
    buttons.sbutton("Files", f"types files {msg_id}")
    buttons.sbutton("Both", f"types both {msg_id}")
    buttons.sbutton(f"Recursive {'✅️' if isRecur else ''}", f"types recur {msg_id}")
    buttons.sbutton("Cancel", f"types cancel {msg_id}")
    return buttons.build_menu(3)

def list_buttons(update, context):
    message = update.message
    user_id = message.from_user.id
    msg_id = message.message_id
    if len(context.args) == 0:
        return sendMessage('Send a search key along with command', context.bot, update.message)
    isRecur = False
    button = common_btn(isRecur, msg_id)
    query = message.text.split(" ", maxsplit=1)[1]
    list_listener[msg_id] = [user_id, query, isRecur]
    sendMessage('Choose Option to list.', context.bot, update.message, button)

def select_type(update, context):
    query = update.callback_query
    user_id = query.from_user.id
    message = query.message
    data = query.data.split()
    listener_id = int(data[-1])
    try:
        listener_info = list_listener[listener_id]
    except:
        return editMessage("Old message !!", message)
    if user_id != int(listener_info[0]):
        return query.answer(text="Not Yours!", show_alert=True)
    elif data[1] == 'cancel':
        query.answer()
        return editMessage("List has been canceled!", message)
    elif data[1] == 'recur':
        query.answer()
        listener_info[2] = not listener_info[2]
        button = common_btn(listener_info[2], listener_id)
        return editMessage('Choose Option to list.', message, button)
    query.answer()
    item_type = data[1]
    editMessage(f"<b>Searching for <i>{listener_info[1]}</i></b>\n\n<b>Type</b>: {item_type.capitalize()} | <b>Recursive </b>: {listener_info[2]}",  message)
    Thread(target=_list_drive, args=(listener_info, message, item_type, context.bot, listener_info[0])).start()
    del list_listener[listener_id]

def _list_drive(listener, bmsg, item_type, bot, user_id):
    query = listener[1]
    isRecur = listener[2]
    LOGGER.info(f"List Initiate : {query}")
    user_dict = user_data.get(user_id, False)
    gdrive = GoogleDriveHelper(user_id=user_id)
    msg, button = gdrive.drive_list(query, isRecursive=isRecur, itemType=item_type)
    if msg:
        if (user_dict and user_dict.get("ulist_typ") == "HTML") or (not user_dict and config_dict['LIST_MODE'].lower() == "html"):
            deleteMessage(bot, bmsg)
            sendFile(bot, bmsg.reply_to_message, button, msg)
        else:
            editMessage(msg, bmsg, button)    
    else:
        editMessage(f'No result found for <i>{query}</i>', bmsg)

def clist(update, context):
    query = update.callback_query
    data = query.data.split()
    try:
        formList = ulist_listener[int(data[1])]
    except:
        query.message.delete()
        return query.answer("List Has Expired! Send Search Again", True)
    user_id = int(data[1])
    buttons = ButtonMaker()
    if query.from_user.id != user_id:
        return query.answer("Access Denied!", True)
    elif data[2] == "changepg":
        query.answer()
        udata = formList[1]
        ind = handleIndex(int(data[3]), udata)
        no = len(udata) - abs(ind+1) if ind < 0 else ind + 1
        if len(udata) > 1:
            buttons.sbutton("⌫", f"cari {user_id} changepg {ind-1}")
            buttons.sbutton(f"Pᴀɢᴇs\n{no} / {len(udata)}", f"cari {user_id} pagnav {ind}")
            buttons.sbutton("⌦", f"cari {user_id} changepg {ind+1}")
        else:
            buttons.sbutton(f"Pᴀɢᴇs\n{no} / {len(udata)}", f"cari {user_id} pagnav {ind}")
        buttons.sbutton("Close", f"cari {user_id} clo", 'footer')
        exdata = formList[0]
        extras = f'''╭ <b>Query :</b> <i>{exdata[0]}</i>
├ <b>Total Results :</b> <i>{exdata[1]}</i>
├ <b>Type :</b> <i>{exdata[2].capitalize()}</i>
╰ <b>CC :</b> <a href='tg://user?id={user_id}'>{bot.get_chat(user_id).first_name}</a>\n'''
        editMessage(extras+udata[ind], query.message, buttons.build_menu(3))
    elif data[2] == "pagnav":
        query.answer()
        for no, _ in enumerate(formList[1]):
            buttons.sbutton(str(no+1), f'cari {user_id} changepg {no}')
        buttons.sbutton("Back", f"cari {user_id} changepg {data[3]}", "footer")
        buttons.sbutton("Close", f"cari {user_id} clo", "footer")
        editMessage("Choose the Page no. from below :", query.message, buttons.build_menu(7))
    else:
        try:
            del list_listener[int(data[1])]
        except: pass
        query.answer()
        query.message.delete()
        query.message.reply_to_message.delete()

dispatcher.add_handler(CommandHandler(BotCommands.ListCommand, list_buttons,
                              filters=CustomFilters.authorized_chat | CustomFilters.authorized_user))
dispatcher.add_handler(CallbackQueryHandler(select_type, pattern="types"))
dispatcher.add_handler(CallbackQueryHandler(clist, pattern="cari"))
