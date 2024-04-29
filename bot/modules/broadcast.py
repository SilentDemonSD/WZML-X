#!/usr/bin/env python3
import asyncio
import time
from typing import List, Dict, Union, Tuple

import uuid
from pyrogram.errors import FloodWait, UserIsBlocked, InputUserDeactivated
from pyrogram.handlers import MessageHandler
from pyrogram.filters import command
from pyrogram.types import Message

from bot import bot, LOGGER, DATABASE_URL
from bot.helper.ext_utils.db_handler import DbManger
from bot.helper.telegram_helper.message_utils import sendMessage, editMessage
from bot.helper.telegram_helper.filters import CustomFilters
from bot.helper.telegram_helper.button_build import ButtonMaker
from bot.helper.telegram_helper.bot_commands import BotCommands

bc_cache: Dict[str, List[Union[Message, int]]] = {}

async def broadcast(_, message):
    if not DATABASE_URL:
        return await sendMessage(message, 'DATABASE_URL not provided!')

    command_args = message.command[1:]
    bc_id, forwarded, quietly, deleted, edited = '', False, False, False, False
    for arg in command_args:
        if not bc_id and arg not in ['-f', '-forward', '-q', '-quiet', '-d', '-delete', '-e', '-edit']:
            bc_id = arg if bc_cache.get(arg, False) else ''
            if not bc_id:
                return await sendMessage(message, "<i>Broadcast ID not found! After Restart, you can't edit or delete broadcasted messages...</i>")
        if arg in ['-f', '-forward']:
            forwarded = True
        if arg in ['-q', '-quiet']:
            quietly = True
        if arg in ['-d', '-delete'] and bc_id:
            deleted = True
        if arg in ['-e', '-edit'] and bc_id:
            edited = True

    if not bc_id:
        return await _send_help_message(message)

    await _send_broadcast(message, bc_id, forwarded, quietly, deleted, edited)

async def _send_broadcast(message, bc_id: str, forwarded: bool, quietly: bool, deleted: bool, edited: bool):
    start_time = time.time()
    status = '''⌬  <b><i>Broadcast Stats :</i></b>
┠ <b>Total Users:</b> <code>0</code>
┠ <b>Success:</b> <code>0</code>
┠ <b>Blocked Users:</b> <code>0</code>
┠ <b>Deleted Accounts:</b> <code>0</code>
┖ <b>Unsuccess Attempt:</b> <code>0</code>'''
    updater = time.time()
    bc_hash, bc_msgs = str(uuid.uuid4()), []
    pls_wait = await sendMessage(message, status)
    total_users = await DbManger().get_pm_uids_count()
    for uid in (await DbManger().get_pm_uids()):
        try:
            if forwarded:
                bc_msg = await message.reply_to_message.forward(uid, disable_notification=quietly)
            else:
                bc_msg = await message.reply_to_message.copy(uid, disable_notification=quietly)
            bc_msgs.append(bc_msg)
            await asyncio.sleep(0.5)
        except FloodWait as e:
            await asyncio.sleep(e.value)
            if forwarded:
                bc_msg = await message.reply_to_message.forward(uid, disable_notification=quietly)
            else:
                bc_msg = await message.reply_to_message.copy(uid, disable_notification=quietly)
            bc_msgs.append(bc_msg)
            await asyncio.sleep(0.5)
        except UserIsBlocked:
            await DbManger().rm_pm_user(uid)
            await asyncio.sleep(0.5)
        except InputUserDeactivated:
            await DbManger().rm_pm_user(uid)
            await asyncio.sleep(0.5)
        except Exception as e:
            LOGGER.error(e)
            await asyncio.sleep(0.5)
        if len(bc_msgs) == total_users:
            break
    bc_cache[bc_hash] = bc_msgs
    await editMessage(
        pls_wait,
        f"{status.format(**locals())}\n\n<b>Elapsed Time:</b> <code>{get_readable_time(time.time() - start_time)}</code>\n<b>Broadcast ID:</b> <code>{bc_hash}</code>",
    )

async def _delete_broadcast(message, bc_id: str):
    temp_wait = await sendMessage(message, '<i>Deleting the Broadcasted Message! Please Wait ...</i>')
    msgs = bc_cache[bc_id]
    for msg in msgs:
        try:
            await msg.delete()
            await asyncio.sleep(0.5)
            msgs.pop(msgs.index(msg))
        except Exception as e:
            LOGGER.error(e)
    await editMessage(temp_wait, f'<b>Broadcast Deleted Successfully!</b>')

async def _edit_broadcast(message, bc_id: str):
    temp_wait = await sendMessage(message, '<i>Editing the Broadcasted Message! Please Wait ...</i>')
    msgs = bc_cache[bc_id]
    for msg in msgs:
        if hasattr(msg, "forward_from"):
            return await editMessage(temp_wait, "<i>Forwarded Messages can't be Edited, Only can be Deleted !</i>")
        try:
            await msg.edit(text=message.reply_to_message.text, entities=message.reply_to_message.entities, reply_markup=message.reply_to_message.reply_markup)
            await asyncio.sleep(0.5)
        except Exception as e:
            LOGGER.error(e)
    await editMessage(temp_wait, f'<b>Broadcast Edited Successfully!</b>')

async def _send_help_message(message):
    return await sendMessage(message, '''<b>By replying to msg to Broadcast:</b>
/broadcast bc_id -d -e -f -q

<b>Forward Broadcast with Tag:</b> -f or -forward
/cmd [reply_msg] -f

<b>Quietly Broadcast msg:</b> -q or -quiet
/cmd [reply_msg] -q -f

<b>Edit Broadcast msg:</b> -e or -edit
/cmd [reply_edited_msg] broadcast_id -e

<b>Delete Broadcast msg:</b> -d or -delete
/bc broadcast_id -d

<b>Notes:</b>
1. Broadcast msgs can be only edited or deleted until restart.
2. Forwarded msgs can't be Edited''')

bot.add_handler(MessageHandler(broadcast, filters=command(BotCommands.BroadcastCommand) & CustomFilters.sudo))

def get_readable_time(seconds: float) -> str:
    result = ''
    (days, remainder) = divmod(int(seconds), 86400)
    if days > 0:
        result += f"{days}d "
    (hours, remainder) = divmod(remainder, 3600)
    if hours > 0:
        result += f"{hours}h "
    (minutes, seconds) = divmod(remainder, 60)
    if minutes > 0:
        result += f"{minutes}m "
    if seconds > 0:
        result += f"{seconds}s"
    return result or "0s"
