import asyncio
import os
from typing import Any
from cryptography.fernet import Fernet

import pyrogram
from pyrogram.errors import FloodWait, ApiIdInvalid, PhoneNumberInvalid, PhoneCodeInvalid, PhoneCodeExpired, SessionPasswordNeeded, ChatAdminRequired
from pyrogram.raw.functions.auth import ImportSessionPhoneNumber, ExportSession
from pyrogram.raw.types import InputPhoneContact

from bot import bot, LOGGER, bot_cache, bot_name, user_data
from bot.helper.telegram_helper.button_build import ButtonMaker
from bot.helper.ext_utils.bot_utils import new_thread, new_task
from bot.helper.telegram_helper.message_utils import sendMessage, editMessage, deleteMessage, sendFile, sendCustomMsg
from bot.helper.telegram_helper.filters import CustomFilters

session_dict: dict[str, str | None] = {}
session_lock = asyncio.Lock()
isStop = False

@new_task
async def genPyroString(client: pyrogram.Client, message: pyrogram.types.Message):
    global isStop
    session_dict.clear()
    sess_msg = await sendMessage(message, """⌬ <u><i><b>Pyrogram String Session Generator</b></i></u>
 
<i>Send your <code>API_ID</code> or <code>APP_ID</code>.
Get from https://my.telegram.org</i>. 
<b>Timeout:</b> 120s

<i>Send /stop to Stop Process</i>""")
    session_dict['message'] = sess_msg
    await asyncio.gather(
        invoke(client, message, 'API_ID'),
        invoke(client, message, 'API_HASH'),
        invoke(client, message, 'PHONE_NO'),
        invoke(client, message, 'CONFIRM_PHN'),
    )
    if isStop:
        return
    try:
        api_id = int(session_dict['API_ID'])
    except Exception:
        return await editMessage(sess_msg, "<i><code>APP_ID</code> is Invalid.</i>\n\n ⌬ <b>Process Stopped.</b>")
    if len(session_dict['API_HASH']) <= 30:
        return await editMessage(sess_msg,  "<i><code>API_HASH</code> is Invalid.</i>\n\n ⌬ <b>Process Stopped.</b>")
    phone_number = session_dict['PHONE_NO']
    confirm_phn = session_dict['CONFIRM_PHN'].lower() in ['y', 'yes']
    if not confirm_phn:
        return await editMessage(sess_msg,  "<i>Phone number confirmation failed.</i>\n\n ⌬ <b>Process Stopped.</b>")
    try:
        pyro_client = pyrogram.Client(api_id=api_id, api_hash=session_dict['API_HASH'])
    except Exception as e:
        return await editMessage(sess_msg, f"<b>Client Error:</b> {str(e)}")
    try:
        await pyro_client.connect()
    except ConnectionError:
        await pyro_client.disconnect()
        await pyro_client.connect()
    try:
        user_code = await pyro_client.send_code(phone_number)
        await asyncio.sleep(1.5)
    except FloodWait as e:
        return await editMessage(sess_msg, f"<b>Floodwait of {e.value} Seconds. Retry Again</b>\n\n ⌬ <b>Process Stopped.</b>")
    except ApiIdInvalid:
        return await editMessage(sess_msg, "<b>API_ID and API_HASH are Invalid. Retry Again</b>\n\n ⌬ <b>Process Stopped.</b>")
    except PhoneNumberInvalid:
        return await editMessage(sess_msg, "<b>Phone Number is Invalid. Retry Again</b>\n\n ⌬ <b>Process Stopped.</b>")
    await asyncio.sleep(1.5)
    await editMessage(sess_msg, """⌬ <u><i><b>Pyrogram String Session Generator</b></i></u>
 
<i>OTP has been sent to your Phone Number, Enter OTP in <code>1 2 3 4 5</code> format. ( Space between each Digits )</i>
<b>If any error or bot not responded, Retry Again.</b>
<b>Timeout:</b> 120s

<i>Send /stop to Stop Process</i>""")
    await invoke(client, message, 'OTP')
    if isStop:
        return
    otp = ' '.join(str(session_dict['OTP']))
    try:
        await pyro_client.sign_in(phone_number, user_code.phone_code_hash, phone_code=otp)
    except PhoneCodeInvalid:
        return await editMessage(sess_msg, "<i>Input OTP is Invalid.</i>\n\n ⌬ <b>Process Stopped.</b>")
    except PhoneCodeExpired:
        return await editMessage(sess_msg, "<i> Input OTP has Expired.</i>\n\n ⌬ <b>Process Stopped.</b>")
    except SessionPasswordNeeded:
        await asyncio.sleep(1.5)
        await editMessage(sess_msg, f"""⌬ <u><i><b>Pyrogram String Session Generator</b></i></u>
 
 <i>Account is being Protected via <b>Two-Step Verification.</b> Send your Password below.</i>
 <b>Timeout:</b> 120s
 
 <b>Password Hint</b> : {await pyro_client.get_password_hint()}
 
 <i>Send /stop to Stop Process</i>""")
        await invoke(client, message, 'TWO_STEP_PASS')
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
        session_string = await pyro_client.invoke(ExportSession())
        await pyro_client.disconnect()
        await editMessage(sess_msg, "⌬ <u><i><b>Pyrogram String Session Generator</b></i></u> \n\n➲ <b>String Session is Successfully Generated ( Saved Messages ).</b>")
    except Exception as e:
        return await editMessage(sess_msg ,f"<b>Export Session Error:</b> {str(e)}")
    try:
        os.remove(f'WZML-X-{message.from_user.id}.session')
        os.remove(f'WZML-X-{message.from_user.id}.session-journal')
    except Exception:
        pass

async def set_details(_: pyrogram.Client, message: pyrogram.types.Message, newkey: str):
    global isStop
    value = message.text
    await deleteMessage(message)
    async with session_lock:
        session_dict[newkey] = value
    if value.lower() == '/stop':
        isStop = True
        return await editMessage(session_dict['message'], '⌬ <b>Process Stopped</b>')

@new_thread
async def invoke(client: pyrogram.Client, message: pyrogram.types.Message, key: str):
    user_id = message.from_user.id
    start_time = time()
    handler = client.add_handler(MessageHandler(partial(set_details, newkey=key), filters=user(user_id) & text & private), group=-1)
    while not bool(session_dict.get(key)):
        await asyncio.sleep(0.5)
        if time() - start_time > 120:
            await editMessage(message, "⌬ <b>Process Stopped</b>")
            isStop = True
            break
    client.remove_handler(*handler)

@new_thread
async def get_decrypt_key(client: pyrogram.Client, message: pyrogram.Message):
    user_id = message.from_user.id
    msg_id = message.id
    user_dict = user_data.get(user_id, {})
    stored_key = user_dict.get('usess_key')
    
    if stored_key is not None and stored_key != '':
        return Fernet(stored_key), False
    grp_prompt = None
    if message.chat.type != ChatType.PRIVATE:
        btn = ButtonMaker()
        btn.ubutton("🔑 Unlock Session", f"https://t.me/{bot_name}")
        grp_prompt = await sendMessage(message, "<i>User Session (Pyrogram V2 Session) Access of your Account is needed for Message to Access, it can't be Accessed by Bot and Session</i>", btn.build_menu(1))
    prompt = await sendCustomMsg(user_id, "<b><u>DECRYPTION:</u></b>\n<i>• This Value is not stored anywhere, so you need to provide it everytime...\n\n</i><b><i>Send your Decrypt Key 🔑 ..</i></b>\n\n<b>Timeout:</b> 60s")
    
    bot_cache[msg_id] = [True, '', False]
    async def set_details(_: pyrogram.Client, message: pyrogram.types.Message):
        await deleteMessage(message)
        bot_cache[msg_id] = [False, message.text, False]
    
    start_time = time()
    handler = client.add_handler(MessageHandler(set_details, filters=user(user_id) & text & private), group=-1)
    while bot_cache[msg_id][0]:
        await asyncio.sleep(0.5)
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
