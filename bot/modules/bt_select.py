from typing import List, Union

import os
import logging
import telegram
from telegram.ext import CommandHandler, CallbackQueryHandler
from telegram.error import TelegramError

import aria2p
from aria2p.client import Aria2Client
from aria2p.protocol.event import Event

from bot import dispatcher, download_dict, download_dict_lock, OWNER_ID, user_data, LOGGER
from bot.helper.telegram_helper.bot_commands import BotCommands
from bot.helper.telegram_helper.filters import CustomFilters
from bot.helper.telegram_helper.message_utils import sendMessage, sendStatusMessage
from bot.helper.ext_utils.bot_utils import get_download_by_gid, MirrorStatus, bt_selection_buttons

logger = logging.getLogger(__name__)

async def select_download(update: telegram.Update, context: telegram.ext.CallbackContext) -> None:
    user_id = update.effective_user.id
    args = context.args

    if len(args) == 1:
        gid = args[0]
        download_info = get_download_by_gid(gid)
    elif update.message.reply_to_message:
        reply_message = update.message.reply_to_message
        with download_dict_lock:
            if reply_message.message_id in download_dict:
                download_info = download_dict[reply_message.message_id]
            else:
                sendMessage("This is not an active task!", context.bot, update.message)
                return
    elif len(args) == 0:
        msg = (
            "Reply to an active /cmd which was used to start the qb-download or add gid along with cmd\n\n"
            "This command mainly for selection incase you decided to select files from already added torrent. "
            "But you can always use /cmd with arg `s` to select files before download start."
        )
        sendMessage(msg, context.bot, update.message)
        return
    else:
        sendMessage("Invalid number of arguments!", context.bot, update.message)
        return

    if (
        OWNER_ID != user_id
        and download_info.message.from_user.id != user_id
        and (user_id not in user_data or not user_data[user_id].get("is_sudo"))
    ):
        sendMessage("This task is not for you!", context.bot, update.message)
        return

    if download_info.status not in [
        MirrorStatus.STATUS_DOWNLOADING,
        MirrorStatus.STATUS_PAUSED,
        MirrorStatus.STATUS_QUEUED,
    ]:
        sendMessage(
            'Task should be in download or pause (incase message deleted by wrong) or queued (status incase you used torrent file)!',
            context.bot,
            update.message,
        )
        return

    if download_info.name.startswith("[METADATA]"):
        sendMessage("Try after downloading metadata finished!", context.bot, update.message)
        return

    try:
        if download_info.is_qbit:
            aria2 = Aria2Client()
            aria2.client.torrents_pause(download_info.hash)
        else:
            aria2.client.force_pause(download_info.gid)
    except aria2p.Aria2WebException as e:
        logger.error(f"Error in pause: {e}")
        sendMessage("Error in pause!", context.bot, update.message)
        return

    buttons = bt_selection_buttons(download_info.gid)
    msg = "Your download paused. Choose files then press Done Selecting button to resume downloading."
    sendMessage(msg, context.bot, update.message, buttons)

async def get_confirm_selection(update: telegram.Update, context: telegram.ext.CallbackContext) -> None:
    query = update.callback_query
    user_id = query.from_user.id
    data = query.data.split()
    download_info = get_download_by_gid(data[2])

    if not download_info:
        query.answer(text="This task has been cancelled!", show_alert=True)
        query.message.delete()
        return

    if not hasattr(download_info, "listener"):
        query.answer(
            text="Not in download state anymore! Keep this message to resume the seed if seed enabled!",
            show_alert=True,
        )
        return

    if user_id != download_info.listener.message.from_user.id:
        query.answer(text="This task is not for you!", show_alert=True)
    elif data[1] == "pin":
        query.answer(text=data[3], show_alert=True)
    elif data[1] == "done":
        query.answer()

        try:
            if download_info.is_qbit:
                aria2 = Aria2Client()
                aria2.client.torrents_resume(download_info.hash)
            else:
                aria2.client.unpause(download_info.gid)
        except aria2p.Aria2WebException as e:
            logger.error(f"Error in resume: {e}")
            query.answer(
                text="Error in resume! This mostly happens after abusing aria2. Try to use select cmd again!",
                show_alert=True,
            )
            return

        sendStatusMessage(download_info.listener.message, download_info.listener.bot)
        query.message.delete()

def main() -> None:
    select_handler = CommandHandler(BotCommands.BtSelectCommand, select_download, filters=CustomFilters.authorized_chat)
    bts_handler = CallbackQueryHandler(get_confirm_selection, pattern="btsel")

    dispatcher.add_handler(select_handler)
    dispatcher.add_handler(bts_handler)

    try:
        dispatcher.start_polling()
        logger.info("Bot started successfully!")
    except TelegramError as e:
        logger.error(f"Failed to start bot: {e}")

if __name__ == "__main__":
    main()
