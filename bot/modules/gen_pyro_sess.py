#!/usr/bin/env python3
from time import time
from aiofiles.os import remove as aioremove
from asyncio import sleep, wrap_future, Lock
from functools import partial
from cryptography.fernet import Fernet

from pyrogram import Client
from pyrogram.types import ForceReply
from pyrogram.enums import ChatType
from pyrogram.filters import command, user, text, private
from pyrogram.handlers import MessageHandler
from pyrogram.errors import SessionPasswordNeeded, FloodWait, PhoneNumberInvalid, ApiIdInvalid, PhoneCodeInvalid, PhoneCodeExpired, UsernameNotOccupied, ChatAdminRequired, PeerIdInvalid

from bot import bot, LOGGER, bot_cache, bot_name
from bot.helper.telegram_helper.button_build import ButtonMaker
from bot.helper.ext_utils.bot_utils import new_thread, new_task
from bot.helper.telegram_helper.message_utils import sendMessage, editMessage, deleteMessage, sendFile, sendCustomMsg
from bot.helper.telegram_helper.filters import CustomFilters

session_dict = {}
session_lock = Lock()
isStop = False

@new_task
async def genPyroString(client, message):
    global isStop
    session_dict.clear()
    sess_msg = await sendMessage(message, """⌬ <u><i><b>Pyrogram String Session Generator</b></i></u>
 
<i>Send your <code>API_ID</code> or <code>APP_ID</code>.
Get from https://my.telegram.org</i>. 
<b>Timeout:</b> 120s

<i>Send /stop to Stop Process</i>""")
    session_dict['message'] = sess_msg
    await wrap_future(invoke(client, message, 'API_ID'))
    if isStop:
        return
    async with session_lock:
        try:
            api_id = int(session_dict['API_ID'])
        except Exception:
            return await editMessage(sess_msg, "<i><code>APP_ID</code> is Invalid.</i>\n\n ⌬ <b>Process Stopped.</b>")
    await sleep(1.5)
    await editMessage(sess_msg, """⌬ <u><i><b>Pyrogram String Session Generator</b></i></u>
 
<i>Send your <code>API_HASH</code>. Get from https://my.telegram.org</i>.
<b>Timeout:</b> 120s

<i>Send /stop to Stop Process</i>""")
    await wrap_future(invoke(client, message, 'API_HASH'))
    if isStop:
        return
    async with session_lock:
        api_hash = session_dict['API_HASH']
    if len(api_hash) <= 30:
        return await editMessage(sess_msg,  "<i><code>API_HASH</code> is Invalid.</i>\n\n ⌬ <b>Process Stopped.</b>")
    while True:
        await sleep(1.5)
        await editMessage(sess_msg,  """⌬ <u><i><b>Pyrogram String Session Generator</b></i></u>
 
<i>Send your Telegram Account's Phone number in International Format ( Including Country Code ). <b>Example :</b> +14154566376</i>.
<b>Timeout:</b> 120s

<i>Send /stop to Stop Process</i>""")
        await wrap_future(invoke(client, message, 'PHONE_NO'))
        if isStop:
            return
        await editMessage(sess_msg, f"⌬ <b>Verification Confirmation:</b>\n\n <i>Is {session_dict['PHONE_NO']} correct? (y/n/yes/no):</i> \n\n<b>Send y/yes (Yes) | n/no (No)</b>")
        await wrap_future(invoke(client, message, 'CONFIRM_PHN'))
        if isStop:
            return
        async with session_lock:
            if session_dict['CONFIRM_PHN'].lower() in ['y', 'yes']:
                break
    try:
        pyro_client = Client(f"WZML-X-{message.from_user.id}", api_id=api_id, api_hash=api_hash)
    except Exception as e:
        await editMessage(sess_msg, f"<b>Client Error:</b> {str(e)}")
        return
    try:
        await pyro_client.connect()
    except ConnectionError:
        await pyro_client.disconnect()
        await pyro_client.connect()
    try:
        user_code = await pyro_client.send_code(session_dict['PHONE_NO'])
        await sleep(1.5)
    except FloodWait as e:
        return await editMessage(sess_msg, f"<b>Floodwait of {e.value} Seconds. Retry Again</b>\n\n ⌬ <b>Process Stopped.</b>")
    except ApiIdInvalid:
        return await editMessage(sess_msg, "<b>API_ID and API_HASH are Invalid. Retry Again</b>\n\n ⌬ <b>Process Stopped.</b>")
    except PhoneNumberInvalid:
        return await editMessage(sess_msg, "<b>Phone Number is Invalid. Retry Again</b>\n\n ⌬ <b>Process Stopped.</b>")
    await sleep(1.5)
    await editMessage(sess_msg, """⌬ <u><i><b>Pyrogram String Session Generator</b></i></u>
 
<i>OTP has been sent to your Phone Number, Enter OTP in <code>1 2 3 4 5</code> format. ( Space between each Digits )</i>
<b>If any error or bot not responded, Retry Again.</b>
<b>Timeout:</b> 120s

<i>Send /stop to Stop Process</i>""")
    await wrap_future(invoke(client, message, 'OTP'))
    if isStop:
        return
    async with session_lock:
        otp = ' '.join(str(session_dict['OTP']))
    try:
        await pyro_client.sign_in(session_dict['PHONE_NO'], user_code.phone_code_hash, phone_code=otp)
    except PhoneCodeInvalid:
        return await editMessage(sess_msg, "<i>Input OTP is Invalid.</i>\n\n ⌬ <b>Process Stopped.</b>")
    except PhoneCodeExpired:
        return await editMessage(sess_msg, "<i> Input OTP has Expired.</i>\n\n ⌬ <b>Process Stopped.</b>")
    except SessionPasswordNeeded:
        await sleep(1.5)
        await editMessage(sess_msg, f"""⌬ <u><i><b>Pyrogram String Session Generator</b></i></u>
 
 <i>Account is being Protected via <b>Two-Step Verification.</b> Send your Password below.</i>
 <b>Timeout:</b> 120s
 
 <b>Password Hint</b> : {await pyro_client.get_password_hint()}
 
 <i>Send /stop to Stop Process</i>""")
        await wrap_future(invoke(client, message, 'TWO_STEP_PASS'))
        if isStop:
            return
        async with session_lock:
            password = session_dict['TWO_STEP_PASS'].strip()
        try:
            await pyro_client.check_password(password)
        except Exception as e:
            return await editMessage(sess_msg, f"<b>Password Check Error:</b> {str(e)}")
    except Exception as e:
        return await editMessage(sess_msg ,f"<b>Sign In Error:</b> {str(e)}")
    try:
        session_string = await pyro_client.export_session_string()
        await pyro_client.send_message("self", f"⌬ <b><u>Pyrogram Session Generated :</u></b>\n\n<code>{session_string}</code>\n\n<b>Via <a href='https://github.com/weebzone/WZML-X'>WZML-X</a> [ @WZML_X ]</b>", disable_web_page_preview=True)
        await pyro_client.disconnect()
        await editMessage(sess_msg, "⌬ <u><i><b>Pyrogram String Session Generator</b></i></u> \n\n➲ <b>String Session is Successfully Generated ( Saved Messages ).</b>")
    except Exception as e:
        return await editMessage(sess_msg ,f"<b>Export Session Error:</b> {str(e)}")
    try:
        await aioremove(f'WZML-X-{message.from_user.id}.session')
        await aioremove(f'WZML-X-{message.from_user.id}.session-journal')
    except Exception:
        pass
    

async def set_details(_, message, newkey):
    global isStop
    value = message.text
    await deleteMessage(message)
    async with session_lock:
        session_dict[newkey] = value
    if value.lower() == '/stop':
        isStop = True
        return await editMessage(session_dict['message'], '⌬ <b>Process Stopped</b>')


@new_thread
async def invoke(client, message, key):
    global isStop
    user_id = message.from_user.id
    start_time = time()
    handler = client.add_handler(MessageHandler(partial(set_details, newkey=key), filters=user(user_id) & text & private), group=-1)
    while not bool(session_dict.get(key)):
        await sleep(0.5)
        if time() - start_time > 120:
            await editMessage(message, "⌬ <b>Process Stopped</b>")
            isStop = True
            break
    client.remove_handler(*handler)


@new_thread
async def get_decrypt_key(client, message):
    user_id = message.from_user.id
    msg_id = message.id
    grp_prompt = None
    if message.chat.type != ChatType.PRIVATE:
        btn = ButtonMaker()
        btn.ubutton("🔑 Unlock Session", f"https://t.me/{bot_name}")
        grp_prompt = await sendMessage(message, "<i>User Session (Pyrogram V2 Session) Access of your Account is needed for Message to Access, it can't be Accessed by Bot and Session</i>", btn.build_menu(1))
    prompt = await sendCustomMsg(user_id, "<b><u>DECRYPTION:</u></b>\n<i>• This Value is not stored anywhere, so you need to provide it everytime...\n\n</i><b><i>Send your Decrypt Key 🔑 ..</i></b>\n\n<b>Timeout:</b> 60s")
    
    bot_cache[msg_id] = [True, '', False]
    async def set_details(_, message):
        await deleteMessage(message)
        bot_cache[msg_id] = [False, message.text, False]
    
    start_time = time()
    handler = client.add_handler(MessageHandler(set_details, filters=user(user_id) & text & private), group=-1)
    while bot_cache[msg_id][0]:
        await sleep(0.5)
        if time() - start_time > 60:
            bot_cache[msg_id][0] = False
            await editMessage(prompt, "<b>Decryption Key TimeOut.. Try Again</b>")
            bot_cache[msg_id][2] = True
    client.remove_handler(*handler)
    
    _, key, is_cancelled = bot_cache[msg_id]
    if is_cancelled:
        await editMessage(prompt, "<b>Decrypt Key Invoke Cancelled</b>")
        if grp_prompt:
            await editMessage(grp_prompt, "<b>Task Cancelled!</b>")
    elif key:
        await editMessage(prompt, "<b>✅️ Decrypt Key Accepted!</b>")
        if grp_prompt:
            await deleteMessage(grp_prompt)
    del bot_cache[msg_id]
    return Fernet(key), is_cancelled


bot.add_handler(MessageHandler(genPyroString, filters=command('exportsession') & private & CustomFilters.sudo))
