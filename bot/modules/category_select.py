from time import time

from .. import bot_cache, categories_dict, task_dict, task_dict_lock, user_data
from ..core.config_manager import Config
from ..helper.ext_utils.bot_utils import (
    arg_parser,
    fetch_drive_cat,
    new_task,
    sync_to_async,
)
from ..helper.ext_utils.links_utils import is_gdrive_link
from ..helper.ext_utils.status_utils import (
    MirrorStatus,
    get_readable_time,
    get_task_by_gid,
)
from ..helper.mirror_leech_utils.gdrive_utils.helper import GoogleDriveHelper
from pyrogram.enums import ButtonStyle
from ..helper.telegram_helper.button_build import ButtonMaker
from ..helper.telegram_helper.filters import CustomFilters
from ..helper.telegram_helper.message_utils import (
    edit_message,
    open_category_btns,
    send_message,
)


async def change_category(client, message):
    if not message.from_user:
        return
    user_id = message.from_user.id

    text = message.text.split("\n")
    input_list = text[0].split(" ")

    arg_base = {"link": "", "-id": "", "-index": ""}
    arg_parser(input_list[1:], arg_base)

    drive_id = arg_base["-id"]
    index_link = arg_base["-index"]

    if drive_id and is_gdrive_link(drive_id):
        drive_id = GoogleDriveHelper().get_id_from_url(drive_id)

    dl = None
    if gid := arg_base["link"]:
        dl = await get_task_by_gid(gid)
        if not dl:
            await send_message(message, f"GID: <code>{gid}</code> Not Found.")
            return
    if reply_to := message.reply_to_message:
        async with task_dict_lock:
            dl = task_dict.get(reply_to.id, None)
        if not dl:
            await send_message(message, "This is not an active task!")
            return
    if not dl:
        await send_message(message, "Provide a task GID or reply to an active task.")
        return
    if (
        not await CustomFilters.sudo("", message)
        and dl.listener.message.from_user.id != user_id
    ):
        await send_message(message, "This task is not for you!")
        return
    if dl.status() not in [
        MirrorStatus.STATUS_DOWNLOAD,
        MirrorStatus.STATUS_PAUSED,
        MirrorStatus.STATUS_QUEUEDL,
    ]:
        await send_message(
            message,
            f"Task should be on {MirrorStatus.STATUS_DOWNLOAD} or "
            f"{MirrorStatus.STATUS_PAUSED} or {MirrorStatus.STATUS_QUEUEDL}",
        )
        return
    listener = dl.listener if hasattr(dl, "listener") else None
    if listener and not listener.is_leech:
        if not index_link and not drive_id:
            drive_id, index_link, is_cancelled = await open_category_btns(message)
            if is_cancelled:
                listener.is_cancelled = True
                return
        if not index_link and not drive_id:
            return await send_message(message, "Time out")
        msg = "<b>Task has been Updated Successfully!</b>"
        if drive_id:
            if not (
                folder_meta := await sync_to_async(
                    GoogleDriveHelper().get_file_metadata, drive_id
                )
            ):
                return await send_message(
                    message, "Google Drive id validation failed!!"
                )
            if listener.drive_id and listener.drive_id == drive_id:
                msg += (
                    f"\n\n<b>Folder name</b> : {folder_meta['name']} Already selected"
                )
            else:
                msg += f"\n\n<b>Folder name</b> : {folder_meta['name']}"
            listener.drive_id = drive_id
        if index_link:
            listener.index_link = index_link
            msg += f"\n\n<b>Index Link</b> : <code>{index_link}</code>"
        return await send_message(message, msg)
    else:
        await send_message(message, "Can not change Category for this task!")


@new_task
async def confirm_category(client, query):
    user_id = query.from_user.id
    data = query.data.split(maxsplit=3)
    msg_id = int(data[2])
    if msg_id not in bot_cache:
        return await edit_message(query.message, "<b>Old Task</b>")
    elif user_id != int(data[1]) and not await CustomFilters.sudo("", query):
        return await query.answer(text="This task is not for you!", show_alert=True)
    elif data[3] == "sdone":
        bot_cache[msg_id][2] = True
        return
    elif data[3] == "scancel":
        bot_cache[msg_id][3] = True
        return
    await query.answer()
    dcats = fetch_drive_cat(user_id)
    default_id = user_data.get(user_id, {}).get("GDRIVE_ID") or Config.GDRIVE_ID
    default_index = user_data.get(user_id, {}).get("INDEX_URL") or Config.INDEX_URL
    merged_dict = {
        "Default": {"drive_id": default_id, "index_link": default_index},
        **dcats,
        **categories_dict,
    }
    cat_name = data[3].replace("_", " ")
    bot_cache[msg_id][0] = merged_dict[cat_name].get("drive_id")
    bot_cache[msg_id][1] = merged_dict[cat_name].get("index_link")
    buttons = ButtonMaker()
    for _name in merged_dict:
        buttons.data_button(
            f"{'✓️' if cat_name == _name else ''} {_name}",
            f"scat {user_id} {msg_id} {_name.replace(' ', '_')}",
        )
    buttons.data_button(
        "Cancel", f"scat {user_id} {msg_id} scancel", "footer", style=ButtonStyle.DANGER
    )
    buttons.data_button(
        f"Done ({get_readable_time(60 - (time() - bot_cache[msg_id][4]))})",
        f"scat {user_id} {msg_id} sdone",
        "footer",
        style=ButtonStyle.SUCCESS,
    )
    await edit_message(
        query.message,
        f"<b>Select the category where you want to upload</b>\n\n"
        f"<i><b>Upload Category:</b></i> <code>{cat_name}</code>\n\n"
        f"<b>Timeout:</b> 60 sec",
        buttons.build_menu(3),
    )


@new_task
async def confirm_dump_chat(client, query):
    user_id = query.from_user.id
    data = query.data.split(maxsplit=3)
    msg_id = int(data[2])
    cache_key = f"sdump_{msg_id}"
    if cache_key not in bot_cache:
        return await edit_message(query.message, "<b>Old Task</b>")
    elif user_id != int(data[1]) and not await CustomFilters.sudo("", query):
        return await query.answer(text="This task is not for you!", show_alert=True)
    elif data[3] == "sdone":
        bot_cache[cache_key][1] = True
        return
    elif data[3] == "scancel":
        bot_cache[cache_key][2] = True
        return
    dump_chats = Config.LEECH_DUMP_CHATS or {}
    dump_names = list(dump_chats)
    try:
        dump_name = dump_names[int(data[3])]
    except (ValueError, IndexError):
        return await query.answer(text="Unknown dump chat!", show_alert=True)
    await query.answer()
    bot_cache[cache_key][0] = dump_chats[dump_name]
    buttons = ButtonMaker()
    for i, name in enumerate(dump_names):
        buttons.data_button(
            f"{'✓️' if dump_name == name else ''} {name}",
            f"sdump {user_id} {msg_id} {i}",
        )
    buttons.data_button(
        "Cancel",
        f"sdump {user_id} {msg_id} scancel",
        "footer",
        style=ButtonStyle.DANGER,
    )
    buttons.data_button(
        f"Done ({get_readable_time(60 - (time() - bot_cache[cache_key][3]))})",
        f"sdump {user_id} {msg_id} sdone",
        "footer",
        style=ButtonStyle.SUCCESS,
    )
    await edit_message(
        query.message,
        f"<b>Select the dump chat for this task</b>\n\n"
        f"<i><b>Dump Chat:</b></i> <code>{dump_name}</code>\n\n"
        f"<b>Timeout:</b> 60 sec",
        buttons.build_menu(3),
    )
