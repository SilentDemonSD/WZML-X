from pyrogram import filters, Client
from pyrogram.types import Message, CallbackQuery

from os import remove, path as ospath

from bot import aria2, download_dict, bot, download_dict_lock, OWNER_ID, user_data, LOGGER
from bot.helper.telegram_helper.bot_commands import BotCommands
from bot.helper.telegram_helper.filters import CustomFilters
from bot.helper.telegram_helper.message_utils import sendMessage, sendStatusMessage
from bot.helper.ext_utils.bot_utils import getDownloadByGid, MirrorStatus, bt_selection_buttons

@bot.on_message(filters.command(BotCommands.BtSelectCommand) & (CustomFilters.authorized_chat | CustomFilters.authorized_user))
async def select(c: Client, message: Message):
    user_id = message.from_user.id
    args = message.text.split()
    if len(args) > 1:
        gid = args[1]
        dl = getDownloadByGid(gid)
        if not dl:
            await sendMessage(f"GID: <code>{gid}</code> Not Found.", c, message)
            return
    elif message.reply_to_message:
        mirror_message = message.reply_to_message
        async with download_dict_lock:
            if mirror_message.id in download_dict:
                dl = download_dict[mirror_message.id]
            else:
                dl = None
        if not dl:
            await sendMessage("This is not an active task!", c, message)
            return
    elif len(args) == 0:
        msg = "Reply to an active /cmd which was used to start the qb-download or add gid along with cmd\n\n"
        msg += "This command mainly for selection incase you decided to select files from already added torrent. "
        msg += "But you can always use /cmd with arg `s` to select files before download start."
        await sendMessage(msg, c, message)
        return

    if OWNER_ID != user_id and dl.message.from_user.id != user_id and \
       (user_id not in user_data or not user_data[user_id].get('is_sudo')):
        await sendMessage("This task is not for you!", c, message)
        return
    if dl.status() not in [MirrorStatus.STATUS_DOWNLOADING, MirrorStatus.STATUS_PAUSED, MirrorStatus.STATUS_QUEUEDL]:
        await sendMessage('Task should be in download or pause (incase message deleted by wrong) or queued (status incase you used torrent file)!', c, message)
        return
    if dl.name().startswith('[METADATA]'):
        await sendMessage('Try after downloading metadata finished!', c, message)
        return

    try:
        listener = dl.listener()
        if listener.isQbit:
            id_ = dl.hash()
            client = dl.client()
            client.torrents_pause(torrent_hashes=id_)
        else:
            id_ = dl.gid()
            try:
                aria2.client.force_pause(id_)
            except Exception as e:
                LOGGER.error(f"{e} Error in pause, this mostly happens after abuse aria2")
        listener.select = True
    except:
        await sendMessage("This is not a bittorrent task!", c, message)
        return

    SBUTTONS = bt_selection_buttons(id_)
    msg = "Your download paused. Choose files then press Done Selecting button to resume downloading."
    await sendMessage(msg, c, message, SBUTTONS)

@bot.on_callback_query(filters.regex(r"^btsel"))
async def get_confirm(c: Client, query: CallbackQuery):
    user_id = query.from_user.id
    data = query.data
    data = data.split()
    dl = getDownloadByGid(data[2])
    if not dl:
        await query.answer(text="This task has been cancelled!", show_alert=True)
        await query.message.delete()
        return
    if hasattr(dl, 'listener'):
        listener = dl.listener()
    else:
        await query.answer(text="Not in download state anymore! Keep this message to resume the seed if seed enabled!", show_alert=True)
        return
    if user_id != listener.message.from_user.id:
        await query.answer(text="This task is not for you!", show_alert=True)
    elif data[1] == "pin":
        await query.answer(text=data[3], show_alert=True)
    elif data[1] == "done":
        await query.answer()
        id_ = data[3]
        if len(id_) > 20:
            client = dl.client()
            tor_info = client.torrents_info(torrent_hash=id_)[0]
            path = tor_info.content_path.rsplit('/', 1)[0]
            res = client.torrents_files(torrent_hash=id_)
            for f in res:
                if f.priority == 0:
                    f_paths = [f"{path}/{f.name}", f"{path}/{f.name}.!qB"]
                    for f_path in f_paths:
                       if ospath.exists(f_path):
                           try:
                               remove(f_path)
                           except:
                               pass
            client.torrents_resume(torrent_hashes=id_)
        else:
            res = aria2.client.get_files(id_)
            for f in res:
                if f['selected'] == 'false' and ospath.exists(f['path']):
                    try:
                        remove(f['path'])
                    except:
                        pass
            try:
                aria2.client.unpause(id_)
            except Exception as e:
                LOGGER.error(f"{e} Error in resume, this mostly happens after abuse aria2. Try to use select cmd again!")
        await sendStatusMessage(listener.message, listener.bot)
        await query.message.delete()
