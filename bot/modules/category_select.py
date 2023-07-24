#!/usr/bin/env python3
from pyrogram.filters import command, regex
from pyrogram.handlers import CallbackQueryHandler, MessageHandler

from bot import bot, bot_cache, categories_dict, download_dict, download_dict_lock
from bot.helper.ext_utils.bot_utils import MirrorStatus, arg_parser, open_category_btns, fetch_user_tds, getDownloadByGid, is_gdrive_link, new_task, sync_to_async
from bot.helper.ext_utils.help_messages import CATEGORY_HELP_MESSAGE
from bot.helper.mirror_utils.upload_utils.gdriveTools import GoogleDriveHelper
from bot.helper.telegram_helper.bot_commands import BotCommands
from bot.helper.telegram_helper.button_build import ButtonMaker
from bot.helper.telegram_helper.filters import CustomFilters
from bot.helper.telegram_helper.message_utils import editMessage, sendMessage


async def change_category(client, message):
    if not message.from_user:
        return
    user_id = message.from_user.id

    text = message.text.split('\n')
    input_list = text[0].split(' ')

    arg_base = {'link': '', 
                '-id': '',
                '-index': ''}

    args = arg_parser(input_list[1:], arg_base)

    drive_id = args['-id']
    index_link = args['-index']

    if drive_id and is_gdrive_link(drive_id):
        drive_id = GoogleDriveHelper.getIdFromUrl(drive_id)

    dl = None
    if gid := args['link']:
        dl = await getDownloadByGid(gid)
        if not dl:
            await sendMessage(message, f"GID: <code>{gid}</code> Not Found.")
            return
    if reply_to := message.reply_to_message:
        async with download_dict_lock:
            dl = download_dict.get(reply_to.id, None)
        if not dl:
            await sendMessage(message, "This is not an active task!")
            return
    if not dl:
        await sendMessage(message, CATEGORY_HELP_MESSAGE)
        return
    if not await CustomFilters.sudo(client, message) and dl.message.from_user.id != user_id:
        await sendMessage(message, "This task is not for you!")
        return
    if dl.status() not in [MirrorStatus.STATUS_DOWNLOADING, MirrorStatus.STATUS_PAUSED, MirrorStatus.STATUS_QUEUEDL]:
        await sendMessage(message, f'Task should be on {MirrorStatus.STATUS_DOWNLOADING} or {MirrorStatus.STATUS_PAUSED} or {MirrorStatus.STATUS_QUEUEDL}')
        return
    listener = dl.listener() if dl and hasattr(dl, 'listener') else None
    if listener and not listener.isLeech:
        if not index_link and not drive_id and categories_dict:
            drive_id, index_link = await open_category_btns(message)
        if not index_link and not drive_id:
            return await sendMessage(message, "Time out")
        msg = '<b>Task has been Updated Successfully!</b>'
        if drive_id:
            if not (folder_name := await sync_to_async(GoogleDriveHelper().getFolderData, drive_id)):
                return await sendMessage(message, "Google Drive id validation failed!!")
            if listener.drive_id and listener.drive_id == drive_id:
                msg += f'\n\n<b>Folder name</b> : {folder_name} Already selected'
            else:
                msg += f'\n\n<b>Folder name</b> : {folder_name}'
            listener.drive_id = drive_id
        if index_link:
            listener.index_link = index_link
            msg += f'\n\n<b>Index Link</b> : <code>{index_link}</code>'
        return await sendMessage(message, msg)
    else:
        await sendMessage(message, "Can not change Category for this task!")


@new_task
async def confirm_category(client, query):
    user_id = query.from_user.id
    data = query.data.split(maxsplit=3)
    msg_id = int(data[2])
    if msg_id not in bot_cache:
        return await editMessage(query.message, '<b>Old Task</b>')
    if user_id != int(data[1]) and not await CustomFilters.sudo(client, query):
        return await query.answer(text="This task is not for you!", show_alert=True)
    if data[3] == "sdone":
        bot_cache[msg_id][3] = True
        return
    await query.answer()
    user_tds = await fetch_user_tds(user_id)
    merged_dict = {**categories_dict, **user_tds}
    bot_cache[msg_id][0] = merged_dict[data[3].replace('_', ' ')].get('drive_id')
    bot_cache[msg_id][1] = merged_dict[data[3].replace('_', ' ')].get('index_link')
    buttons = ButtonMaker()
    if len(categories_dict) > 1:
        for _name in categories_dict.keys():
            buttons.ibutton(f'{_name}', f"scat {user_id} {data[2]} {_name.replace(' ', '_')}")
    if user_tds:
        for _name in user_tds.keys():
            buttons.ibutton(f'{_name}', f"scat {user_id} {data[2]} {_name.replace(' ', '_')}")
    buttons.ubutton('Start', f'scat {user_id} {msg_id} done', 'footer')
    await editMessage(query.message, f'<b>Select the category where you want to upload</b>\n\n<i>Upload Category:</i> <code>{data[3]}</code>', buttons.build_menu(2))


bot.add_handler(MessageHandler(change_category, filters=command(BotCommands.CategorySelect) & CustomFilters.authorized))
bot.add_handler(CallbackQueryHandler(confirm_category, filters=regex("^scat")))