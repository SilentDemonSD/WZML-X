#!/usr/bin/env python3
from pyrogram.handlers import MessageHandler, CallbackQueryHandler
from pyrogram.filters import command, regex

from bot import bot, LOGGER, OWNER_ID, config_dict
from bot.helper.telegram_helper.message_utils import sendMessage, editMessage, auto_delete_message
from bot.helper.telegram_helper.filters import CustomFilters
from bot.helper.telegram_helper.bot_commands import BotCommands
from bot.helper.telegram_helper.button_build import ButtonMaker
from bot.helper.mirror_utils.upload_utils.gdriveTools import GoogleDriveHelper
from bot.helper.ext_utils.bot_utils import sync_to_async, new_task, is_gdrive_link


@new_task
async def driveclean(_, message):
    args = message.text.split()
    if len(args) > 1:
        link = args[1].strip()
    elif reply_to := message.reply_to_message:
        link = reply_to.text.split(maxsplit=1)[0].strip()
    else:
        link = f"https://drive.google.com/drive/folders/{config_dict['GDRIVE_ID']}"
    if not is_gdrive_link(link):
        return await sendMessage(message, 'No GDrive Link Provided')
    gd = GoogleDriveHelper()
    name, mime_type, size, files, folders = await sync_to_async(gd.count, link)
    try:
        drive_id = await sync_to_async(gd.__getIdFromUrl, link)
    except (KeyError, IndexError):
        return await sendMessage(message, "Google Drive ID could not be found in the provided link")
    buttons = ButtonMaker()
    buttons.ibutton('Move to Trash', f'gdclean clear {drive_id} trash')
    buttons.ibutton('Permanent Del', f'gdclean clear {drive_id}')
    buttons.ibutton('Stop Clean', 'gdclean stop', 'footer')
    reply_message = await sendMessage(message, f"⌬ <b><i>GDrive Clean :</i></b>\n\nName : {name}\nSize: {size}\nFiles: {files} | Folders : {folders}\n\n<code>Choose the Required Action below to Clean your Drive!</code>\n\n<b>NOTE:</b>\n<i>1) All files are permanently deleted if Permanent Del, not moved to trash.\n2) Folder doesn't gets Deleted.\n3) Delete files of custom folder via giving link along with cmd, but it should have delete permissions.\n4) Move to Trash Moves all your files to trash but can be restored again if have permissions.</i>", buttons.build_menu(2))

@new_task
async def drivecleancb(_, query):
    message = query.message
    user_id = query.from_user.id
    data = query.data.split()
    if user_id != OWNER_ID:
        await query.answer(text="Not Owner!", show_alert=True)
        return
    if data[1] == "clear":
        await query.answer()
        await editMessage(message, '<i>Processing Drive Clean...</i>')
        drive = GoogleDriveHelper()
        msg = await sync_to_async(drive.driveclean, data[2], trash=len(data)==4)
        await editMessage(message, msg)
    elif data[1] == "stop":
        await query.answer()
        await editMessage(message, '⌬ <b>DriveClean Stopped!</b>')
        await auto_delete_message(message, message)
        

bot.add_handler(MessageHandler(driveclean, filters=command(BotCommands.GDCleanCommand) & CustomFilters.owner))
bot.add_handler(CallbackQueryHandler(drivecleancb, filters=regex(r'^gdclean')))