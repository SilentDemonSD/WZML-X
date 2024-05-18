#!/usr/bin/env python3
from asyncio import sleep
from time import time

from psutil import cpu_percent, disk_usage, virtual_memory
from pyrogram.filters import command, regex
from pyrogram.handlers import CallbackQueryHandler, MessageHandler

from bot import (
    Intervals,
    bot,
    bot_cache,
    botStartTime,
    config_dict,
    status_dict,
    task_dict,
    task_dict_lock,
)
from bot.helper.ext_utils.bot_utils import (
    get_readable_file_size,
    get_readable_time,
    new_task,
    sync_to_async,
)
from bot.helper.ext_utils.status_utils import MirrorStatus, speed_string_to_bytes
from bot.helper.tele_swi_helper.bot_commands import BotCommands
from bot.helper.tele_swi_helper.button_build import ButtonMaker
from bot.helper.tele_swi_helper.filters import CustomFilters
from bot.helper.tele_swi_helper.message_utils import (
    auto_delete_message,
    delete_status,
    deleteMessage,
    editMessage,
    sendMessage,
    sendStatusMessage,
    update_status_message,
    user_info,
)
from bot.helper.themes import BotTheme


@new_task
async def mirror_status(_, message):
    async with task_dict_lock:
        count = len(task_dict)
    if count == 0:
        currentTime = get_readable_time(time() - botStartTime)
        free = get_readable_file_size(disk_usage(config_dict["DOWNLOAD_DIR"]).free)
        msg = BotTheme(
            "NO_ACTIVE_DL",
            cpu=cpu_percent(),
            free=free,
            free_p=round(100 - disk_usage(config_dict["DOWNLOAD_DIR"]).percent, 1),
            ram=virtual_memory().percent,
            uptime=currentTime,
        )
        reply_message = await sendMessage(message, msg)
        await auto_delete_message(message, reply_message)
    else:
        text = message.text.split()
        if len(text) > 1:
            user_id = message.from_user.id if text[1] == "me" else int(text[1])
        else:
            user_id = 0
            sid = message.chat.id
            if obj := Intervals["status"].get(sid):
                obj.cancel()
                del Intervals["status"][sid]
        await sendStatusMessage(message, user_id)
        await deleteMessage(message)


@new_task
async def status_pages(_, query):
    user_id = query.from_user.id
    data = query.data.split()
    key = int(data[1])
    if data[1] == "ref":
        bot_cache.setdefault("status_refresh", {})
        if (
            user_id in (refresh_status := bot_cache["status_refresh"])
            and (curr := (time() - refresh_status[user_id])) < 7
        ):
            return await query.answer(
                f"Already Refreshed! Try after {get_readable_time(7 - curr)}",
                show_alert=True,
            )
        else:
            refresh_status[user_id] = time()
        await editMessage(
            query.message,
            f"{(await user_info(user_id)).mention(style='html')}, <i>Refreshing Status...</i>",
        )
        await sleep(1.5)
        await update_status_message(key, force=True)
    elif data[2] in ["nex", "pre"]:
        async with task_dict_lock:
            if data[2] == "nex":
                status_dict[key]["page_no"] += status_dict[key]["page_step"]
            else:
                status_dict[key]["page_no"] -= status_dict[key]["page_step"]
        await update_status_message(key, force=True)
    elif data[2] == "ps":
        async with task_dict_lock:
            status_dict[key]["page_step"] = int(data[3])
    elif data[2] == "st":
        async with task_dict_lock:
            status_dict[key]["status"] = data[3]
        await update_status_message(key, force=True)
    elif data[1] == "close":
        await delete_status()
    elif data[2] == "ov":
        message = query.message
        tasks = {
            "Download": 0,
            "Upload": 0,
            "Seed": 0,
            "Archive": 0,
            "Extract": 0,
            "Split": 0,
            "QueueDl": 0,
            "QueueUp": 0,
            "Clone": 0,
            "CheckUp": 0,
            "Pause": 0,
            "SamVid": 0,
            "ConvertMedia": 0,
        }
        dl_speed = 0
        up_speed = 0
        seed_speed = 0
        async with task_dict_lock:
            for download in task_dict.values():
                match await sync_to_async(download.status):
                    case MirrorStatus.STATUS_DOWNLOADING:
                        tasks["Download"] += 1
                        dl_speed += speed_string_to_bytes(download.speed())
                    case MirrorStatus.STATUS_UPLOADING:
                        tasks["Upload"] += 1
                        up_speed += speed_string_to_bytes(download.speed())
                    case MirrorStatus.STATUS_SEEDING:
                        tasks["Seed"] += 1
                        seed_speed += speed_string_to_bytes(download.seed_speed())
                    case MirrorStatus.STATUS_ARCHIVING:
                        tasks["Archive"] += 1
                    case MirrorStatus.STATUS_EXTRACTING:
                        tasks["Extract"] += 1
                    case MirrorStatus.STATUS_SPLITTING:
                        tasks["Split"] += 1
                    case MirrorStatus.STATUS_QUEUEDL:
                        tasks["QueueDl"] += 1
                    case MirrorStatus.STATUS_QUEUEUP:
                        tasks["QueueUp"] += 1
                    case MirrorStatus.STATUS_CLONING:
                        tasks["Clone"] += 1
                    case MirrorStatus.STATUS_CHECKING:
                        tasks["CheckUp"] += 1
                    case MirrorStatus.STATUS_PAUSED:
                        tasks["Pause"] += 1
                    case MirrorStatus.STATUS_SAMVID:
                        tasks["SamVid"] += 1
                    case MirrorStatus.STATUS_CONVERTING:
                        tasks["ConvertMedia"] += 1
                    case _:
                        tasks["Download"] += 1
                        dl_speed += speed_string_to_bytes(download.speed())

        msg = f"""<b>DL:</b> {tasks['Download']} | <b>UP:</b> {tasks['Upload']} | <b>SD:</b> {tasks['Seed']} | <b>AR:</b> {tasks['Archive']}
<b>EX:</b> {tasks['Extract']} | <b>SP:</b> {tasks['Split']} | <b>QD:</b> {tasks['QueueDl']} | <b>QU:</b> {tasks['QueueUp']}
<b>CL:</b> {tasks['Clone']} | <b>CK:</b> {tasks['CheckUp']} | <b>PA:</b> {tasks['Pause']} | <b>SV:</b> {tasks['SamVid']}
<b>CM:</b> {tasks['ConvertMedia']}

<b>ODLS:</b> {get_readable_file_size(dl_speed)}/s
<b>OULS:</b> {get_readable_file_size(up_speed)}/s
<b>OSDS:</b> {get_readable_file_size(seed_speed)}/s
"""
        button = ButtonMaker()
        button.ibutton("Back", f"status {data[1]} ref")
        await editMessage(message, msg, button.build_menu())
    await query.answer()


bot.add_handler(
    MessageHandler(
        mirror_status,
        filters=command(BotCommands.StatusCommand)
        & CustomFilters.authorized
        & ~CustomFilters.blacklisted,
    )
)
bot.add_handler(CallbackQueryHandler(status_pages, filters=regex("^status")))
