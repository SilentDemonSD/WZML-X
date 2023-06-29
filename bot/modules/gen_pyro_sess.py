#!/usr/bin/env python3
from time import time
from asyncio import sleep
from functools import partial

from pyrogram import Client
from pyrogram.filters import command, user, text, private
from pyrogram.handlers import MessageHandler
from pyrogram.errors import SessionPasswordNeeded, FloodWait, PhoneNumberInvalid, ApiIdInvalid, PhoneCodeInvalid, PhoneCodeExpired, UsernameNotOccupied, ChatAdminRequired, PeerIdInvalid

from bot import bot, LOGGER
from bot.helper.ext_utils.bot_utils import new_thread
from bot.helper.telegram_helper.message_utils import sendMessage, editMessage, sendFile
from bot.helper.telegram_helper.filters import CustomFilters

session_dict = {}
isStop = False

@new_thread
async def genPyroString(client, message):
    global isStop
    sess_msg = await sendMessage(message, """⌬ <u><i><b>Pyrogram String Session Generator</b></i></u>
 
<i>Send your <code>API_ID</code> or <code>APP_ID</code>.
Get from https://my.telegram.org</i>. 
<b>Timeout:</b> 120s

<i>Send /stop to Stop Process</i>""")
    session_dict['message'] = sess_msg
    await invoke(client, message, 'API_ID')
    if isStop:
        return
    try:
        api_id = int(session_dict['API_ID'])
    except Exception:
        return await editMessage(sess_msg, "<i><code>APP_ID</code> is Invalid.</i>\n\n ⌬ <b>Process Stopped.</b>")
    await sleep(0.5)
    await editMessage(sess_msg,  """⌬ <u><i><b>Pyrogram String Session Generator</b></i></u>
 
<i>Send your <code>API_HASH</code>. Get from https://my.telegram.org</i>.
<b>Timeout:</b> 120s

<i>Send /stop to Stop Process</i>""")
    await invoke(client, message, 'API_HASH')
    if isStop:
        return
    api_hash = session_dict['API_HASH']
    if len(api_hash) <= 30:
        return await editMessage(sess_msg,  "<i><code>API_HASH</code> is Invalid.</i>\n\n ⌬ <b>Process Stopped.</b>")
    await sleep(0.5)
    await editMessage(sess_msg,  """⌬ <u><i><b>Pyrogram String Session Generator</b></i></u>
 
<i>Send your Telegram Account's Phone number in International Format ( Including Country Code ). <b>Example :</b> +14154566376</i>.
<b>Timeout:</b> 120s

<i>Send /stop to Stop Process</i>""")
    while True:
        await invoke(client, message, 'PHONE_NO')
        if isStop:
            return
        await editMessage(sess_msg, f"⌬ <b>Verification Confirmation:</b>\n\n <i>Is {session_dict['PHONE_NO']} correct? (y/n/yes/no): \n\nSend <code>y / yes</code> (Yes) | <code>n / no</code> (No)</i>")
        await invoke(client, message, 'CONFIRM_PHN')
        if isStop:
            return
        if session_dict['CONFIRM_PHN'].lower() in ['y', 'yes']:
            break
    try:
        pyro_client = Client(f"WZML-X-{message.from_user.id}", api_id=api_id, api_hash=api_hash)
    except Exception as e:
        await editMessage(sess_msg, f"<b>ERROR:</b> {str(e)}")
        return
    try:
        await pyro_client.connect()
    except ConnectionError:
        await pyro_client.disconnect()
        await pyro_client.connect()
    try:
        user_code = await pyro_client.send_code(session_dict['PHONE_NO'])
        await sleep(0.5)
    except FloodWait as e:
        return await editMessage(sess_msg, f"<b>Floodwait of {e.value} Seconds. Retry Again</b>\n\n ⌬ <b>Process Stopped.</b>")
    except ApiIdInvalid:
        return await editMessage(sess_msg, "<b>API_ID and API_HASH are Invalid. Retry Again</b>\n\n ⌬ <b>Process Stopped.</b>")
    except PhoneNumberInvalid:
        return await editMessage(sess_msg, "<b>Phone Number is Invalid. Retry Again</b>\n\n ⌬ <b>Process Stopped.</b>")
    await sleep(0.5)
    await editMessage(sess_msg, """⌬ <u><i><b>Pyrogram String Session Generator</b></i></u>
 
<i>OTP has been sent to your Phone Number, Enter OTP in <code>1 2 3 4 5</code> format. ( Space between each Digits )</i>
<b>If any error or bot not responded, Retry Again.</b>
<b>Timeout:</b> 120s

<i>Send /stop to Stop Process</i>""")
    await invoke(client, message, 'OTP')
    if isStop:
        return
    try:
        await pyro_client.sign_in(session_dict['PHONE_NO'], user_code.phone_code_hash, phone_code=' '.join(str(session_dict['OTP'])))
    except PhoneCodeInvalid:
        return await editMessage(sess_msg, "<i>Input OTP is Invalid.</i>\n\n ⌬ <b>Process Stopped.</b>")
    except PhoneCodeExpired:
        return await editMessage(sess_msg, "<i> Input OTP has Expired.</i>\n\n ⌬ <b>Process Stopped.</b>")
    except SessionPasswordNeeded:
        await editMessage(sess_msg, """⌬ <u><i><b>Pyrogram String Session Generator</b></i></u>
 
 <i>Account is being Protected via <b>Two-Step Verification.</b> Send your Password below.</i>
 <b>Timeout:</b> 120s
 
 <i>Send /stop to Stop Process</i>""")
        await invoke(client, message, 'TWO_STEP_PASS')
        if isStop:
            return
        try:
            await pyro_client.check_password(session_dict['TWO_STEP_PASS'])
        except Exception as e:
            return await editMessage(sess_msg, f"<b>ERROR:</b> {str(e)}")
    except Exception as e:
        return await editMessage(sess_msg ,f"<b>ERROR:</b> {str(e)}")
    try:
        session_string = await pyro_client.export_session_string()
        await pyro_client.send_message("self", f"⌬ <b>Pyrogram Session Generated</b>\n\n<code>{session_string}</code>")
        await pyro_client.disconnect()
        await editMessage(sess_msg, "<b>String Session is Successfully Generated. Check Saved Message to get your Session</b>")
    except Exception as e:
        return await editMessage(sess_msg ,f"<b>ERROR:</b> {str(e)}")

async def set_details(_, message, newkey):
    global isStop
    user_id = message.from_user.id
    session_dict[user_id] = False
    value = message.text
    await message.delete()
    if value.lower() == '/stop':
        isStop = True
        return await editMessage(session_dict['message'], '⌬ <b>Process Stopped</b>')
    session_dict[newkey] = value
        
async def invoke(client, message, key):
    global isStop
    user_id = message.from_user.id
    session_dict[user_id] = True
    start_time = time()
    handler = client.add_handler(MessageHandler(partial(set_details, newkey=key), filters=user(user_id) & text & private), group=-1)
    while session_dict[user_id]:
        await sleep(0.5)
        if time() - start_time > 120:
            session_dict[user_id] = False
            await editMessage(message, "⌬ <b>Process Stopped</b>")
            isStop = True
    client.remove_handler(*handler)
    
bot.add_handler(MessageHandler(genPyroString, filters=command('exportsession') & private & CustomFilters.owner))