#!/usr/bin/env python3
from math import ceil
from random import choice
from pyrogram.handlers import MessageHandler, CallbackQueryHandler
from pyrogram.filters import command, regex

from bot import LOGGER, bot, config_dict, gd_search_dict
from bot.helper.mirror_utils.upload_utils.gdriveTools import GoogleDriveHelper
from bot.helper.telegram_helper.message_utils import sendMessage, editMessage, delete_links, deleteMessage
from bot.helper.telegram_helper.filters import CustomFilters
from bot.helper.telegram_helper.bot_commands import BotCommands
from bot.helper.telegram_helper.button_build import ButtonMaker
from bot.helper.ext_utils.bot_utils import sync_to_async, new_task, get_telegraph_list, get_tg_list, checking_access, handleIndex
from bot.helper.themes import BotTheme


async def list_buttons(user_id, isRecursive=True):
    buttons = ButtonMaker()
    buttons.ibutton("Only Folders", f"list_types {user_id} folders {isRecursive}")
    buttons.ibutton("Only Files", f"list_types {user_id} files {isRecursive}")
    buttons.ibutton("Both", f"list_types {user_id} both {isRecursive}")
    buttons.ibutton(f"{'✅️' if isRecursive else ''} Recursive", f"list_types {user_id} rec {isRecursive}")
    buttons.ibutton("Cancel", f"list_types {user_id} cancel")
    return buttons.build_menu(2)


async def _list_drive(key, message, user_id, item_type, isRecursive):
    LOGGER.info(f"GDrive List: {key}")
    gdrive = GoogleDriveHelper()
    telegraph_content, contents_no, tglist = await sync_to_async(gdrive.drive_list, key, isRecursive=isRecursive, itemType=item_type, userId=user_id, msgId=message.reply_to_message.id)
    if telegraph_content:
        if tglist[0]:
            msg, button = await get_tg_list(telegraph_content, contents_no, tglist)
        else:
            try:
                button = await get_telegraph_list(telegraph_content)
            except Exception as e:
                await editMessage(message, e)
                return
            msg = BotTheme('LIST_FOUND', NO=contents_no, NAME=key)
        await editMessage(message, msg, button)
    else:
        await editMessage(message, BotTheme('LIST_NOT_FOUND', NAME=key))


@new_task
async def select_type(_, query):
    user_id = query.from_user.id
    message = query.message
    key = message.reply_to_message.text.split(maxsplit=1)[1].strip()
    data = query.data.split()
    if user_id != int(data[1]):
        return await query.answer(text="Not Yours!", show_alert=True)
    elif data[2] == 'rec':
        await query.answer()
        isRecursive = not bool(eval(data[3]))
        buttons = await list_buttons(user_id, isRecursive)
        return await editMessage(message, '<b>Choose drive list options:</b>', buttons)
    elif data[2] == 'cancel':
        await query.answer()
        return await editMessage(message, "<b>List has been canceled!</b>")
    await query.answer()
    item_type = data[2]
    isRecursive = eval(data[3])
    await editMessage(message, BotTheme('LIST_SEARCHING', NAME=key))
    await _list_drive(key, message, user_id, item_type, isRecursive)


@new_task
async def choose_list(_, query):
    user_id = query.from_user.id
    message = query.message
    data = query.data.split()
    msg_id = int(data[2])
    formList = gd_search_dict.get(msg_id)
    if formList is None:
        await deleteMessage(query.message)
        return await query.answer("List has Expired! ReSearch Again", True) 
    buttons = ButtonMaker()
    if user_id != int(data[1]):
        return await query.answer("Access Denied!", True) 
    elif data[3] == "changepg":
        await query.answer()
        udata = formList[1]
        ind = handleIndex(int(data[4]), udata)
        no = len(udata) - abs(ind+1) if ind < 0 else ind + 1 
        if len(udata) > 1:
            buttons.ibutton("⌫", f"clist {user_id} {msg_id} changepg {ind-1}") 
            buttons.ibutton(f"Pᴀɢᴇs\n{no} / {len(udata)}", f"clist {user_id} {msg_id} pagnav {ind}") 
            buttons.ibutton("⌦", f"clist {user_id} {msg_id} changepg {ind+1}") 
        else: 
            buttons.ibutton(f"Pᴀɢᴇs\n{no} / {len(udata)}", f"clist {user_id} {msg_id} pagnav {ind}") 
        buttons.ibutton("Close", f"clist {user_id} {msg_id} close", 'footer') 
        exdata = formList[0] 
        extras = f'''┎ <b>Query :</b> <i>{exdata[0]}</i>
┠ <b>Total Results :</b> <i>{exdata[1]}</i> 
┠ <b>Type :</b> <i>{(exdata[2] or "Folders & Files").capitalize()}</i> 
┖ <b>#cc :</b> {(await bot.get_users(user_id)).mention}\n\n''' 
        await editMessage(message, extras+udata[ind], buttons.build_menu(3)) 
    elif data[3] == "pagnav": 
        await query.answer() 
        for no, _ in enumerate(formList[1]): 
            buttons.ibutton(str(no+1), f'clist {user_id} {msg_id} changepg {no}') 
        buttons.ibutton("Back", f"clist {user_id} {msg_id} changepg {data[4]}", "footer") 
        buttons.ibutton("Close", f"clist {user_id} {msg_id} close", "footer")
        await editMessage(query.message, "Choose the Page Number from below :", buttons.build_menu(min(ceil(len(formList[1])/2), 7))) 
    else: 
        try: 
            del gd_search_dict[msg_id] 
        except: 
            pass 
        await query.answer() 
        await deleteMessage(query.message)
        if reply_to := query.message.reply_to_message:
            await deleteMessage(reply_to)
         

async def drive_list(_, message):
    args = message.text.split() if message.text else ['/cmd']
    if len(args) == 1:
        return await sendMessage(message, '<i>Send a search key along with command</i>')
    user_id = message.from_user.id
    msg, btn = await checking_access(user_id)
    if msg is not None:
        await sendMessage(message, msg, btn.build_menu(1))
        return
    buttons = await list_buttons(user_id)
    await sendMessage(message, '<b>Choose drive list options:</b>', buttons, 'IMAGES')


bot.add_handler(MessageHandler(drive_list, filters=command(
    BotCommands.ListCommand) & CustomFilters.authorized & ~CustomFilters.blacklisted))
bot.add_handler(CallbackQueryHandler(select_type, filters=regex("^list_types")))
bot.add_handler(CallbackQueryHandler(choose_list, filters=regex("^clist")))
