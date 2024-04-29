#!/usr/bin/env python3
from typing import List, Dict, Union, Tuple
from time import time, sleep
from uuid import uuid4
from asyncio import sleep as async_sleep
from pyrogram.handlers import MessageHandler
from pyrogram.filters import command
from pyrogram.errors import FloodWait, UserIsBlocked, InputUserDeactivated

from bot import bot, LOGGER, DATABASE_URL
from bot.helper.ext_utils.db_handler import DbManger
from bot.helper.telegram_helper.message_utils import sendMessage, editMessage
from bot.helper.telegram_helper.filters import CustomFilters
from bot.helper.telegram_helper.bot_commands import BotCommands
from bot.helper.telegram_helper.button_build import ButtonMaker
from bot.helper.ext_utils.bot_utils import new_task, get_readable_time

bc_cache: Dict[str, List[Union[str, int]]] = {}

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

    t, s, b, d, u = 0, 0, 0, 0, 0
    if deleted:
        await _delete_broadcast(message, bc_id, t, s, u)
    elif edited:
        await _edit_broadcast(message, bc_id, t, s, u)
    else:
        await _send_broadcast(message, bc_id, forwarded, quietly, t, s, b, d, u)

async def _delete_broadcast(message, bc_id: str, t: int, s: int, u: int):
    temp_wait = await sendMessage(message, '<i>Deleting the Broadcasted Message! Please Wait ...</i>')
    msgs = bc_cache[bc_id]
    for msg in msgs:
        try:
            await msg.delete()
            await async_sleep(0.5)
            msgs.pop(msgs.index(msg))
            s += 1
        except Exception as e:
            LOGGER.error(e)
            u += 1
        t += 1
    await editMessage(temp_wait, f'''⌬  <b><i>Broadcast Deleted Stats :</i></b>
┠ <b>Total Users:</b> <code>{t}</code>
┠ <b>Success:</b> <code>{s}</code>
┖ <b>Unsuccess Attempt:</b> <code>{u}</code>

<b>Broadcast ID:</b> <code>{bc_id}</code>''')

async def _edit_broadcast(message, bc_id: str, t: int, s: int, u: int):
    temp_wait = await sendMessage(message, '<i>Editing the Broadcasted Message! Please Wait ...</i>')
    msgs = bc_cache[bc_id]
    for msg in msgs:
        if hasattr(msg, "forward_from"):
            return await editMessage(temp_wait, "<i>Forwarded Messages can't be Edited, Only can be Deleted !</i>")
        try:
            await msg.edit(text=message.reply_to_message.text, entities=message.reply_to_message.entities, reply_markup=message.reply_to_message.reply_markup)
            await async_sleep(0.5)
            s += 1
        except FloodWait as e:
            await async_sleep(e.value)
            await msg.edit(text=message.reply_to_message.text, entities=message.reply_to_message.entities, reply_markup=message.reply_to_message.reply_markup)
        except Exception:
            LOGGER.error(e)
            u += 1
        t += 1
    await editMessage(temp_wait, f'''⌬  <b><i>Broadcast Edited Stats :</i></b>
┠ <b>Total Users:</b> <code>{t}</code>
┠ <b>Success:</b> <code>{s}</code>
┖ <b>Unsuccess Attempt:</b> <code>{u}</code>

<b>Broadcast ID:</b> <code>{bc_id}</code>''')

async def _send_broadcast(message, bc_id: str, forwarded: bool, quietly: bool, t: int, s: int, b: int, d: int, u: int):
    start_time = time()
    status = '''⌬  <b><i>Broadcast Stats :</i></b>
┠ <b>Total Users:</b> <code>{t}</code>
┠ <b>Success:</b> <code>{s}</code>
┠ <b>Blocked Users:</b> <code>{b}</code>
┠ <b>Deleted Accounts:</b> <code>{d}</code>
┖ <b>Unsuccess Attempt:</b> <code>{u}</code>'''
    updater = time()
    bc_hash, bc_msgs = str(uuid4()), []
    pls_wait = await sendMessage(message, status.format(**locals()))
    for uid in (await DbManger().get_pm_uids()):
        try:
            if forwarded:
                bc_msg = await message.reply_to_message.forward(uid, disable_notification=quietly)
            else:
                bc_msg = await message.reply_to_message.copy(uid, disable_notification=quietly)
            s += 1
        except FloodWait as e:
            await async_sleep(e.value)
            if forwarded:
                bc_msg = await message.reply_to_message.forward(uid, disable_notification=quietly)
            else:
                bc_msg = await message.reply_to_message.copy(uid, disable_notification=quietly)
            s += 1
        except UserIsBlocked:
            await DbManger().rm_pm_user(uid)
            b += 1
        except InputUserDeactivated:
            await DbManger().rm_pm_user(uid)
            d += 1
        except Exception as e:
            LOGGER.error(e)
            u += 1
        if bc_msg:
            bc_msgs.append(bc_msg)
        t += 1
        if (time() - updater) > 10:
            await editMessage(pls_wait, status.format(**locals()))
            updater = time()
    bc_cache[bc_hash] = bc_msgs
    await editMessage(
        pls_wait,
        f"{status.format(**locals())}\n\n<b>Elapsed Time:</b> <code>{get_readable_time(time() - start_time)}</code>\n<b>Broadcast ID:</b> <code>{bc_hash}</code>",
    )

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
