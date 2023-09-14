#!/usr/bin/env python3
from time import time
from uuid import uuid4
from asyncio import sleep
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

bc_cache = {}

@new_task
async def broadcast(_, message):
    bc_id, forwarded, quietly, deleted, edited = '', False, False, False, False
    if not DATABASE_URL:
        return await sendMessage(message, 'DATABASE_URL not provided!')
    rply = message.reply_to_message
    if len(message.command) > 1:
        if not message.command[1].startswith('-'):
            bc_id = message.command[1] if bc_cache.get(message.command[1], False) else ''
            if not bc_id:
                return await sendMessage(message, "<i>Broadcast ID not found! After Restart, you can't edit or delete broadcasted messages...</i>")
        for arg in message.command:
            if arg in ['-f', '-forward'] and rply:
                forwarded = True
            if arg in ['-q', '-quiet'] and rply:
                quietly = True
            elif arg in ['-d', '-delete'] and bc_id:
                deleted = True
            elif arg in ['-e', '-edit'] and bc_id and rply:
                edited = True
    if not bc_id and not rply:
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
    t, s, b, d, u = 0, 0, 0, 0, 0
    if deleted:
        temp_wait = await sendMessage(message, '<i>Deleting the Broadcasted Message! Please Wait ...</i>')
        for msg in (msgs:=bc_cache[bc_id]):
            try:
                await msg.delete()
                await sleep(0.5)
                msgs.pop(msgs.index(msg))
                s += 1
            except:
                u += 1
            t += 1
        return await editMessage(temp_wait, f'''⌬  <b><i>Broadcast Deleted Stats :</i></b>
┠ <b>Total Users:</b> <code>{t}</code>
┠ <b>Success:</b> <code>{s}</code>
┖ <b>Unsuccess Attempt:</b> <code>{u}</code>

<b>Broadcast ID:</b> <code>{bc_id}</code>''')
    elif edited:
        temp_wait = await sendMessage(message, '<i>Editing the Broadcasted Message! Please Wait ...</i>')
        for msg in bc_cache[bc_id]:
            if hasattr(msg, "forward_from"):
                return await editMessage(temp_wait, "<i>Forwarded Messages can't be Edited, Only can be Deleted !</i>")
            try:
                await msg.edit(text=rply.text, entities=rply.entities, reply_markup=rply.reply_markup)
                await sleep(0.5)
                s += 1
            except FloodWait as e:
                await sleep(e.value)
                await msg.edit(text=rply.text, entities=rply.entities, reply_markup=rply.reply_markup)
            except Exception:
                u += 1
            t += 1
        return await editMessage(temp_wait, f'''⌬  <b><i>Broadcast Edited Stats :</i></b>
┠ <b>Total Users:</b> <code>{t}</code>
┠ <b>Success:</b> <code>{s}</code>
┖ <b>Unsuccess Attempt:</b> <code>{u}</code>

<b>Broadcast ID:</b> <code>{bc_id}</code>''')
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
                bc_msg = await rply.forward(uid, disable_notification=quietly)
            else:
                bc_msg = await rply.copy(uid, disable_notification=quietly)
            s += 1
        except FloodWait as e:
            await sleep(e.value)
            if forwarded:
                bc_msg = await rply.forward(uid, disable_notification=quietly)
            else:
                bc_msg = await rply.copy(uid, disable_notification=quietly)
            s += 1
        except UserIsBlocked:
            await DbManger().rm_pm_user(uid)
            b += 1
        except InputUserDeactivated:
            await DbManger().rm_pm_user(uid)
            d += 1
        except Exception:
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
        
        
bot.add_handler(MessageHandler(broadcast, filters=command(BotCommands.BroadcastCommand) & CustomFilters.sudo))