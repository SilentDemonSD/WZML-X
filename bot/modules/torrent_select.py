#!/usr/bin/env python3
from typing import Coroutine, Final, List, Optional

import aiofiles.os as aiofiles
import pyrogram.filters
from pyrogram.handlers import MessageHandler, CallbackQueryHandler
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message

import bot.helper.telegram_helper.bot_commands as BotCommands
from bot.helper.telegram_helper.bot_utils import get_download_by_gid
from bot.helper.telegram_helper.message_utils import delete_message, send_message, send_status_message
from bot.helper.ext_utils.bot_utils import is_sudo_user, sync_to_async

from .mirror_status import MirrorStatus
from .aria2_manager import Aria2Manager
from .qbittorrent_manager import QBittorrentManager

bot: Final = None
bot_name: Final = None
aria2: Final = None
download_dict: Final = None
download_dict_lock: Final = None
OWNER_ID: Final = None
user_data: Final = None
LOGGER: Final = None


async def select(client: pyrogram.Client, message: Message) -> Coroutine:
    user_id = message.from_user.id
    msg = message.text.split("_", maxsplit=1)
    if len(msg) > 1:
        cmd_data = msg[1].split("@", maxsplit=1)
        if len(cmd_data) > 1 and cmd_data[1].strip() != bot_name:
            return
        gid = cmd_data[0]
        dl = await get_download_by_gid(gid)
    elif reply_to_id := message.reply_to_message_id:
        async with download_dict_lock:
            dl = download_dict.get(reply_to_id, None)
    elif len(msg) == 1:
        await send_message(
            message,
            (
                "Reply to an active /cmd which was used to start the qb-download or add gid along with cmd\n\n"
                "This command mainly for selection incase you decided to select files from already added torrent. "
                "But you can always use /cmd with arg `s` to select files before download start."
            ),
        )
        return

    if (
        OWNER_ID != user_id
        and dl.message.from_user.id != user_id
        and (user_id not in user_data or not user_data[user_id].get("is_sudo"))
    ):
        await send_message(message, "This task is not for you!")
        return

    if dl.status() not in [MirrorStatus.STATUS_DOWNLOADING, MirrorStatus.STATUS_PAUSED, MirrorStatus.STATUS_QUEUED]:
        await send_message(
            message,
            "Task should be in download or pause (incase message deleted by wrong) or queued (status incase you used torrent file)!",
        )
        return

    if dl.name().startswith("[METADATA]"):
        await send_message(message, "Try after downloading metadata finished!")
        return

    try:
        if dl.is_qbit:
            id_ = dl.hash()
            client = dl.client()
            if not dl.queued:
                await sync_to_async(client.torrents_pause, torrent_hashes=id_)
        else:
            id_ = dl.gid()
            if not dl.queued:
                await sync_to_async(aria2.pause, id_)

        dl.listener.select = True
    except Exception as e:  # noqa
        await send_message(message, "This is not a bittorrent task!")
        return

    buttons = bt_selection_buttons(id_)
    msg = "Your download paused. Choose files then press Done Selecting button to resume downloading."
    await send_message(message, msg, buttons)


async def get_confirm(client, query):
    user_id = query.from_user.id
    data = query.data.split()
    message = query.message
    dl = await get_download_by_gid(data[2])
    if dl is None:
        await query.answer("This task has been cancelled!", show_alert=True)
        await delete_message(message)
        return

    if hasattr(dl, "listener"):
        listener = dl.listener()
    else:
        await query.answer(
            "Not in download state anymore! Keep this message to resume the seed if seed enabled!",
            show_alert=True,
        )
        return

    if user_id != listener.message.from_user.id and not await is_sudo_user(client, query):
        await query.answer("This task is not for you!", show_alert=True)
    elif data[1] == "pin":
        await query.answer(data[3], show_alert=True)
    elif data[1] == "done":
        await query.answer()

        id_ = data[3]
        if len(id_) > 20:
            client = dl.client()
            tor_info = (await sync_to_async(client.torrents_info, torrent_hash=id_))[0]
            path = tor_info.content_path.rsplit("/", 1)[0]
            res = await sync_to_async(client.torrents_files, torrent_hash=id_)

            coroutines = [
                aiofiles.os_path.isfile(f"{path}/{f.name}"),
                aiofiles.os_path.isfile(f"{path}/{f.name}.!qB"),
            ]

            files_to_delete = []
            for coroutine in coroutines:
                file_exists = await coroutine
                if file_exists:
                    files_to_delete.append(f"{path}/{f.name}")
                    files_to_delete.append(f"{path}/{f.name}.!qB")

            for file_to_delete in files_to_delete:
                try:
                    await aiofiles.os_path.remove(file_to_delete)
                except:
                    pass

            if not dl.queued:
                await sync_to_async(client.torrents_resume, torrent_hashes=id_)
        else:
            res = await sync_to_async(aria2.get_files, id_)

            coroutines = [
                aiofiles.os_path.isfile(f["path"]),
                aiofiles.os_path.remove(f["path"]),
            ]

            for file in res:
                if file["selected"] == "false":
                    file_exists = await coroutines[0]
                    if file_exists:
                        await coroutines[1]

            if not dl.queued:
                try:
                    await sync_to_async(aria2.unpause, id_)
                except Exception as e:  # noqa
                    LOGGER.error(
                        f"{e} Error in resume, this mostly happens after abuse aria2. Try to use select cmd again!"
                    )

        await send_status_message(message)
        await delete_message(message)
    elif data[1] == "rm":
        await query.answer()
        await (dl.download()).cancel_download()
        await delete_message(message)


bot.add_handler(
    MessageHandler(
        select,
        filters=pyrogram.filters.regex(f"^/{BotCommands.BtSelectCommand}(_\w+)?")
        & CustomFilters.authorized
        & ~CustomFilters.blacklisted,
    )
)
bot.add_handler(CallbackQueryHandler(get_confirm, filters=pyrogram.filters.regex("^btsel")))
