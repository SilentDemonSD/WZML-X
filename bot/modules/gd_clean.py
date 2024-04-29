#!/usr/bin/env python3
from pyrogram.handlers import MessageHandler, CallbackQueryHandler
from pyrogram.filters import command, regex
from pyrogram.types import Button, CallbackQuery
from typing import Optional

from bot import bot, LOGGER, OWNER_ID, config_dict
from bot.helper.telegram_helper.message_utils import sendMessage, editMessage, auto_delete_message
from bot.helper.telegram_helper.filters import CustomFilters
from bot.helper.telegram_helper.bot_commands import BotCommands
from bot.helper.telegram_helper.button_build import ButtonMaker
from bot.helper.mirror_utils.upload_utils.gdriveTools import GoogleDriveHelper
from bot.helper.ext_utils.bot_utils import sync_to_async, new_task, is_gdrive_link, get_readable_file_size

async def driveclean(context: MessageHandler) -> None:
    args = context.args
    link: Optional[str] = args[1].strip() if len(args) > 1 else None
    if not link:
        link = f"https://drive.google.com/drive/folders/{config_dict['GDRIVE_ID']}"
    if not is_gdrive_link(link):
        return await sendMessage(context.message, 'No GDrive Link Provided')
    clean_msg = await sendMessage(context.message, '<i>Fetching ...</i>')
    gd = GoogleDriveHelper()
    name, mime_type, size, files, folders = await sync_to_async(gd.count, link)
    try:
        drive_id = GoogleDriveHelper.getIdFromUrl(link)
    except (KeyError, IndexError):
        return await editMessage(clean_msg, "Google Drive ID could not be found in the provided link")
    buttons = ButtonMaker()
    buttons.ibutton('Move to Bin', f'gdclean clear {drive_id} trash', url=f'https://drive.google.com/drive/u/0/trash')
    buttons.ibutton('Permanent Clean', f'gdclean clear {drive_id}', url='https://drive.google.com/drive/u/0/search?q=type:anyone')
    buttons.ibutton('Stop GDrive Clean', 'gdclean stop', 'footer')
    await editMessage(clean_msg, f'''⌬ <b><i>GDrive Clean/Trash :</i></b>
    
┎ <b>Name:</b> {name}
┃ <b>Size:</b> {get_readable_file_size(size)}
┖ <b>Files:</b> {files} | <b>Folders:</b> {folders}
    
<b>NOTES:</b>
<i>1. All files are permanently deleted if Permanent Del, not moved to trash.
2. Folder doesn't gets Deleted.
3. Delete files of custom folder via giving link along with cmd, but it should have delete permissions.
4. Move to Bin Moves all your files to trash but can be restored again if have permissions.</i>
    
<code>Choose the Required Action below to Clean your Drive!</code>''', buttons.build_menu(2))

async def drivecleancb(context: CallbackQueryHandler) -> None:
    query: CallbackQuery = context.query
    user_id = query.from_user.id
    data = query.data.split()
    if user_id != OWNER_ID:
        await query.answer(text="Not Owner!", show_alert=True)
        return
    if data[1] == "clear":
        await query.answer()
        await editMessage(query.message, '<i>Processing Drive Clean / Trash...</i>')
        drive = GoogleDriveHelper()
        msg = await sync_to_async(drive.driveclean, data[2], trash=len(data)==4)
        await editMessage(query.message, msg)
    elif data[1] == "stop":
        await query.answer()
        await editMessage(query.message, '⌬ <b>DriveClean Stopped!</b>')
        await auto_delete_message(query.message, query.message)

bot.add_handler(MessageHandler(driveclean, filters=command(BotCommands.GDCleanCommand) & CustomFilters.owner))
bot.add_handler(CallbackQueryHandler(drivecleancb, filters=regex(r'^gdclean')))
