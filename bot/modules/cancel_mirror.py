from pyrogram import filters, Client
from pyrogram.types import Message, CallbackQuery
from time import sleep
from asyncio import run_coroutine_threadsafe
from bot import download_dict, bot, download_dict_lock, OWNER_ID, user_data, main_loop
from bot.helper.telegram_helper.bot_commands import BotCommands
from bot.helper.telegram_helper.filters import CustomFilters
from bot.helper.telegram_helper.message_utils import sendMessage, auto_delete_message
from bot.helper.ext_utils.bot_utils import getDownloadByGid, getAllDownload, MirrorStatus
from bot.helper.telegram_helper import button_build


@bot.on_message(filters.command(BotCommands.CancelMirror) & (CustomFilters.authorized_chat | CustomFilters.authorized_user))
async def cancel_mirror(c: Client, message: Message):
    user_id = message.from_user.id
    args = message.text.split()
    if len(args) > 1:
        gid = args[1]
        dl = getDownloadByGid(gid)
        if not dl:
            return await sendMessage(f"GID: <code>{gid}</code> Not Found.", c, message)
    elif message.reply_to_message:
        mirror_message = message.reply_to_message
        async with download_dict_lock:
            if mirror_message.id in download_dict:
                dl = download_dict[mirror_message.id]
            else:
                dl = None
        if not dl:
            return await sendMessage("This is not an active task!", c, message)
    elif len(args) == 0:
        msg = f"Reply to an active <code>/{BotCommands.MirrorCommand}</code> message which \
                was used to start the download or send <code>/{BotCommands.CancelMirror} GID</code> to cancel it!"
        return await sendMessage(msg, c, message)

    if OWNER_ID != user_id and dl.message.from_user.id != user_id and \
       (user_id not in user_data or not user_data[user_id].get('is_sudo')):
        return await sendMessage("This task is not for you!", c, message)

    if dl.status() == MirrorStatus.STATUS_CONVERTING:
        await sendMessage("Converting... Can't cancel this task!", c, message)
        return

    try:
        await dl.download().cancel_download()
    except:
        dl.download().cancel_download()


def cancel_all(status, loop):
    gid = ''
    while dl := run_coroutine_threadsafe(getAllDownload(status), loop).result():
        if dl.gid() != gid:
            gid = dl.gid()
            main_loop.create_task(dl.download().cancel_download())
            sleep(1)


@bot.on_message(filters.command(BotCommands.CancelAllCommand) & (CustomFilters.owner_filter | CustomFilters.sudo_user))
async def cancell_all_buttons(c: Client, message: Message):
    buttons = button_build.ButtonMaker()
    buttons.sbutton("Downloading", f"canall {MirrorStatus.STATUS_DOWNLOADING}")
    buttons.sbutton("Uploading", f"canall {MirrorStatus.STATUS_UPLOADING}")
    buttons.sbutton("Seeding", f"canall {MirrorStatus.STATUS_SEEDING}")
    buttons.sbutton("Cloning", f"canall {MirrorStatus.STATUS_CLONING}")
    buttons.sbutton("Extracting", f"canall {MirrorStatus.STATUS_EXTRACTING}")
    buttons.sbutton("Archiving", f"canall {MirrorStatus.STATUS_ARCHIVING}")
    buttons.sbutton("QueuedDl", f"canall {MirrorStatus.STATUS_QUEUEDL}")
    buttons.sbutton("QueuedUp", f"canall {MirrorStatus.STATUS_QUEUEUP}")
    buttons.sbutton("Paused", f"canall {MirrorStatus.STATUS_PAUSED}")
    buttons.sbutton("All", "canall all")
    buttons.sbutton("Close", "canall close")
    button = buttons.build_menu(2)
    can_msg = await sendMessage('Choose tasks to cancel.', c, message, button)
    main_loop.create_task(auto_delete_message(c, message, can_msg))


@bot.on_callback_query(filters.regex(r"^canall"))
async def cancel_all_update(c: Client, query: CallbackQuery):
    message = query.message
    user_id = query.from_user.id
    data = query.data
    data = data.split()
    if CustomFilters.owner_query(user_id):
        if data[1] == 'close':
            await query.answer()
            await query.message.delete()
            await query.message.reply_to_message.delete()
            return
    async with download_dict_lock:
        count = len(download_dict)
    if count == 0:
        await sendMessage("No active tasks!", c, message)
        return
    if CustomFilters.owner_query(user_id):
        await query.answer()
        # await cancel_all(data[1])
        main_loop.run_in_executor(None, cancel_all, data[1], main_loop)
    else:
        await query.answer(text="You don't have permission to use these buttons!", show_alert=True)
