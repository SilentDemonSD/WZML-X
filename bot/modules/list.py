from pyrogram import filters, Client
from pyrogram.types import Message, CallbackQuery
from bot import bot, ulist_listener, LOGGER, config_dict, user_data
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
    buttons.sbutton(
        f"Recursive {'✅️' if isRecur else ''}", f"types recur {msg_id}")
    buttons.sbutton("Cancel", f"types cancel {msg_id}")
    return buttons.build_menu(3)


@bot.on_message(filters.command(BotCommands.ListCommand) & (CustomFilters.authorized_chat | CustomFilters.authorized_user))
async def list_buttons(c: Client, message: Message):
    user_id = message.from_user.id
    msg_id = message.id
    args = message.text.split()
    if len(args) == 0:
        return await sendMessage('Send a search key along with command', c, message)
    isRecur = False
    button = common_btn(isRecur, msg_id)
    query = message.text.split(" ", maxsplit=1)[1]
    list_listener[msg_id] = [user_id, query, isRecur]
    await sendMessage('Choose Option to list.', c, message, button)


@bot.on_callback_query(filters.regex(r"^types"))
async def select_type(c: Client, query: CallbackQuery):
    user_id = query.from_user.id
    message = query.message
    data = query.data.split()
    listener_id = int(data[-1])
    try:
        listener_info = list_listener[listener_id]
    except:
        return await editMessage("Old message !!", message)
    if user_id != int(listener_info[0]):
        return await query.answer(text="Not Yours!", show_alert=True)
    elif data[1] == 'cancel':
        await query.answer()
        return await editMessage("List has been canceled!", message)
    elif data[1] == 'recur':
        await query.answer()
        listener_info[2] = not listener_info[2]
        button = common_btn(listener_info[2], listener_id)
        return await editMessage('Choose Option to list.', message, button)
    await query.answer()
    item_type = data[1]
    await editMessage(f"<b>Searching for <i>{listener_info[1]}</i></b>\n\n<b>Type</b>: {item_type.capitalize()} | <b>Recursive </b>: {listener_info[2]}",  message)
    await _list_drive(listener_info, message, item_type, c, listener_info[0])
    # Thread(target=_list_drive, args=(listener_info, message, item_type, context.bot, listener_info[0])).start()
    del list_listener[listener_id]


async def _list_drive(listener, bmsg, item_type, bot, user_id):
    query = listener[1]
    isRecur = listener[2]
    LOGGER.info(f"List Initiate : {query}")
    user_dict = user_data.get(user_id, False)
    gdrive = GoogleDriveHelper(user_id=user_id)
    msg, button = await gdrive.drive_list(
        query, isRecursive=isRecur, itemType=item_type)
    if msg:
        if (user_dict and user_dict.get("ulist_typ") == "HTML") or (not user_dict and config_dict['LIST_MODE'].lower() == "html"):
            await deleteMessage(bot, bmsg)
            await sendFile(bot, bmsg.reply_to_message, button, msg)
        else:
            await editMessage(msg, bmsg, button)
    else:
        await editMessage(f'No result found for <i>{query}</i>', bmsg)


@bot.on_callback_query(filters.regex(r"^cari"))
async def clist(c: Client, query: CallbackQuery):
    data = query.data.split()
    try:
        formList = ulist_listener[int(data[1])]
    except:
        await query.message.delete()
        return await query.answer("List Has Expired! Send Search Again", True)
    user_id = int(data[1])
    buttons = ButtonMaker()
    if query.from_user.id != user_id:
        return await query.answer("Access Denied!", True)
    elif data[2] == "changepg":
        await query.answer()
        udata = formList[1]
        ind = handleIndex(int(data[3]), udata)
        no = len(udata) - abs(ind+1) if ind < 0 else ind + 1
        if len(udata) > 1:
            buttons.sbutton("⌫", f"cari {user_id} changepg {ind-1}")
            buttons.sbutton(f"Pᴀɢᴇs\n{no} / {len(udata)}",
                            f"cari {user_id} pagnav {ind}")
            buttons.sbutton("⌦", f"cari {user_id} changepg {ind+1}")
        else:
            buttons.sbutton(f"Pᴀɢᴇs\n{no} / {len(udata)}",
                            f"cari {user_id} pagnav {ind}")
        buttons.sbutton("Close", f"cari {user_id} clo", 'footer')
        exdata = formList[0]
        usrchat = await c.get_chat(user_id)
        extras = f'''╭ <b>Query :</b> <i>{exdata[0]}</i>
├ <b>Total Results :</b> <i>{exdata[1]}</i>
├ <b>Type :</b> <i>{exdata[2].capitalize()}</i>
╰ <b>CC :</b> <a href='tg://user?id={user_id}'>{usrchat.first_name}</a>\n'''
        await editMessage(extras+udata[ind], query.message, buttons.build_menu(3))
    elif data[2] == "pagnav":
        await query.answer()
        for no, _ in enumerate(formList[1]):
            buttons.sbutton(str(no+1), f'cari {user_id} changepg {no}')
        buttons.sbutton("Back", f"cari {user_id} changepg {data[3]}", "footer")
        buttons.sbutton("Close", f"cari {user_id} clo", "footer")
        await editMessage("Choose the Page no. from below :", query.message, buttons.build_menu(7))
    else:
        try:
            del list_listener[int(data[1])]
        except:
            pass
        await query.answer()
        await query.message.delete()
        await query.message.reply_to_message.delete()
