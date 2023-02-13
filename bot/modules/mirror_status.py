from psutil import cpu_percent, virtual_memory, disk_usage
from time import time
from asyncio import sleep as asleep
from pyrogram import filters, Client
from pyrogram.types import Message, CallbackQuery
from pyrogram.enums import ChatMemberStatus, ChatType

from bot import bot, status_reply_dict_lock, download_dict, download_dict_lock, botStartTime, config_dict, OWNER_ID, Interval, main_loop
from bot.helper.telegram_helper.message_utils import sendMessage, deleteMessage, auto_delete_message, sendStatusMessage, update_all_messages, delete_all_messages, editMessage, editCaption
from bot.helper.ext_utils.bot_utils import get_readable_file_size, get_readable_time, turn, bot_sys_stats, setInterval, is_sudo
from bot.helper.telegram_helper.filters import CustomFilters
from bot.helper.telegram_helper.bot_commands import BotCommands


@bot.on_message(filters.command(BotCommands.StatusCommand) & (CustomFilters.authorized_chat | CustomFilters.authorized_user))
async def mirror_status(c: Client, message: Message):
    async with download_dict_lock:
        count = len(download_dict)
    if count == 0:
        currentTime = get_readable_time(time() - botStartTime)
        free = get_readable_file_size(
            disk_usage(config_dict['DOWNLOAD_DIR']).free)
        msg = 'No Active Downloads !\n___________________________'
        msg += f"\n<b>CPU:</b> {cpu_percent()}% | <b>FREE:</b> {free}" \
                   f"\n<b>RAM:</b> {virtual_memory().percent}% | <b>UPTIME:</b> {currentTime}"
        reply_message = await sendMessage(msg, c, message)
        main_loop.create_task(auto_delete_message(c, message, reply_message))
    else:
        await sendStatusMessage(message, c)
        await deleteMessage(c, message)
        async with status_reply_dict_lock:
            if Interval:
                Interval[0].cancel()
                Interval.clear()
                Interval.append(setInterval(
                    config_dict['STATUS_UPDATE_INTERVAL'], update_all_messages))


@bot.on_callback_query(filters.regex(r"^status"))
async def status_pages(c: Client, query: CallbackQuery):
    msg = query.message
    user_id = query.from_user.id
    user_name = query.from_user.first_name
    if msg.chat.type != ChatType.PRIVATE:
        chat = msg.chat
        member = await chat.get_member(user_id)
        admins = member.status in [ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER]
    elif msg.chat.type == ChatType.PRIVATE:
        if user_id == OWNER_ID or is_sudo(user_id):
            admins = True 
    data = query.data
    data = data.split()
    if data[1] == "refresh":
        if config_dict['PICS']:
            await editCaption(f"{user_name}, Refreshing Status...", msg)
        else:
            await editMessage(f"{user_name}, Refreshing Status...", msg)
        await asleep(2)
        await update_all_messages()
        await query.answer()
    if data[1] == "stats":
        stats = bot_sys_stats()
        await query.answer(text=stats, show_alert=True)
    if data[1] == "close":
        if admins:
            await delete_all_messages()
            await query.answer()
        else:
            await query.answer(text=f"{user_name}, You Don't Have Rights To Close This!", show_alert=True)
    if data[1] == "pre" or "nex":
        done = await turn(data)
    if done:
        await update_all_messages(True)
        await query.answer()
    else:
        await msg.delete()
