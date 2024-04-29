import os
import asyncio
import time
import typing
from contextlib import asynccontextmanager
from cryptography.fernet import Fernet

import aiofiles
from aiogram import Bot, types, filters, Router, FSMContext
from aiogram.fsm.context import FSMContext
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.executor import start_webhook
from aiogram.utils.exceptions import ThrottlingException, MessageCantBeEdited, MessageToDeleteNotFound

router = Router()

@router.message(filters=filters.Command("exportsession") & filters.Private)
async def gen_pyro_string(message: types.Message, state: FSMContext):
    async with state.proxy() as session_dict:
        session_dict.clear()
        sess_msg = await sendMessage(message, """⌬ <u><i><b>Pyrogram String Session Generator</b></i></u>
 
<i>Send your <code>API_ID</code> or <code>APP_ID</code>.
Get from <a href='https://my.telegram.org'>my.telegram.org</a></i>. 
<b>Timeout:</b> 120s

<i>Send /stop to Stop Process</i>""")
        session_dict['message'] = sess_msg
        await create_task(invoke(message, 'API_ID', state))
        if isStop:
            return
        async with session_dict['lock']:
            try:
                api_id = int(session_dict['API_ID'])
            except Exception:
                return await editMessage(sess_msg, "<i><code>APP_ID</code> is Invalid.</i>\n\n ⌬ <b>Process Stopped.</b>")
        await asyncio.sleep(1.5)
        await editMessage(sess_msg, """⌬ <u><i><b>Pyrogram String Session Generator</b></i></u>
 
<i>Send your <code>API_HASH</code>. Get from <a href='https://my.telegram.org'>my.telegram.org</a></i>.
<b>Timeout:</b> 120s

<i>Send /stop to Stop Process</i>""")
        await create_task(invoke(message, 'API_HASH', state))
        if isStop:
            return
        async with session_dict['lock']:
            api_hash = session_dict['API_HASH']
        if len(api_hash) <= 30:
            return await editMessage(sess_msg,  "<i><code>API_HASH</code> is Invalid.</i>\n\n ⌬ <b>Process Stopped.</b>")
        while True:
            await asyncio.sleep(1.5)
            await editMessage(sess_msg,  """⌬ <u><i><b>Pyrogram String Session Generator</b></i></u>
 
<i>Send your Telegram Account's Phone number in International Format ( Including Country Code ). <b>Example :</b> +14154566376</i>.
<b>Timeout:</b> 120s

<i>Send /stop to Stop Process</i>""")
            await create_task(invoke(message, 'PHONE_NO', state))
            if isStop:
                return
            await editMessage(sess_msg, f"⌬ <b>Verification Confirmation:</b>\n\n <i>Is {session_dict['PHONE_NO']} correct? (y/n/yes/no):</i> \n\n<b>Send y/yes (Yes) | n/no (No)</b>")
            await create_task(invoke(message, 'CONFIRM_PHN', state))
            if isStop:
                return
            async with session_dict['lock']:
                if session_dict['CONFIRM_PHN'].lower() in ['y', 'yes']:
                    break
    try:
        pyro_client = Bot(f"WZML-X-{message.from_user.id}", api_id=api_id, api_hash=api_hash)
    except Exception as e:
        await editMessage(sess_msg, f"<b>Client Error:</b> {str(e)}")
        return
    try:
        await pyro_client.send_message(message.chat.id, "Connecting...")
        await pyro_client.connect()
    except ConnectionError:
        await pyro_client.disconnect()
        await pyro_client.connect()
    try:
        user_code = await pyro_client.send_code(session_dict['PHONE_NO'])
        await asyncio.sleep(1.5)
    except ThrottlingException as e:
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
    await create_task(invoke(message, 'OTP', state))
    if isStop:
        return
    async with session_dict['lock']:
        otp = ' '.join(str(session_dict['OTP']))
    try:
        await pyro_client.sign_in(session_dict['PHONE_NO'], user_code.phone_code_hash, phone_code=otp)
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
        await create_task(invoke(message, 'TWO_STEP_PASS', state))
        if isStop:
            return
        async with session_dict['lock']:
            password = session_dict['TWO_STEP_PASS'].strip()
        try:
            await pyro_client.check_password(password)
        except Exception as e:
            return await editMessage(sess_msg, f"<b>Password Check Error:</b> {str(e)}")
    except Exception as e:
        return await editMessage(sess_msg ,f"<b>Sign In Error:</b> {str(e)}")
    try:
        session_string = await pyro_client.export_session_string()
        await pyro_client.send_message(message.chat.id, f"⌬ <b><u>Pyrogram Session Generated :</u></b>\n\n<code>{session_string}</code>\n\n<b>Via <a href='https://github.com/weebzone/WZML-X'>WZML-X</a> [ @WZML_X ]</b>", disable_web_page_preview=True)
        await pyro_client.disconnect()
        await editMessage(sess_msg, "⌬ <u><i><b>Pyrogram String Session Generator</b></i></u> \n\n➲ <b>String Session is Successfully Generated ( Saved Messages ).</b>")
    except Exception as e:
        return await editMessage(sess_msg ,f"<b>Export Session Error:</b> {str(e)}")
    try:
        await aiofiles.os.remove(f'WZML-X-{message.from_user.id}.session')
        await aiofiles.os.remove(f'WZML-X-{message.from_user.id}.session-journal')
    except Exception:
        pass

@asynccontextmanager
async def invoke(message: types.Message, key: str, state: FSMContext):
    global isStop
    user_id = message.from_user.id
    start_time = time()
    handler = message.bot.add_handler(types.MessageHandler(types.Text(lambda m: m.from_user.id == user_id)), group=-1)
    async with state.proxy() as session_dict:
        while not bool(session_dict.get(key)):
            await asyncio.sleep(0.5)
            if time() - start_time > 120:
                await editMessage(message, "⌬ <b>Process Stopped</b>")
                isStop = True
                break
    message.bot.remove_handler(handler)
    yield

@router.message(filters=filters.Command("decrypt") & filters.Private)
async def decrypt_message(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    msg_id = message.id
    grp_prompt = None
    if message.chat.type != types.ChatType.PRIVATE:
        btn = InlineKeyboardMarkup().add(InlineKeyboardButton("🔑 Unlock Session", url=f"https://t.me/{bot_name}"))
        grp_prompt = await sendMessage(message, "<i>User Session (Pyrogram V2 Session) Access of your Account is needed for Message to Access, it can't be Accessed by Bot and Session</i>", reply_markup=btn)
    prompt = await sendCustomMsg(user_id, "<b><u>DECRYPTION:</u></b>\n<i>• This Value is not stored anywhere, so you need to provide it everytime...\n\n</i><b><i>Send your Decrypt Key 🔑 ..</i></b>\n\n<b>Timeout:</b> 60s")
    
    bot_cache[msg_id] = [True, '', False]
    async def set_details(_, message: types.Message):
        await deleteMessage(message)
        bot_cache[msg_id] = [False, message.text, False]
    
    start_time = time()
    handler = message.bot.add_handler(types.MessageHandler(types.Text(lambda m: m.from_user.id == user_id)), group=-1)
    while bot_cache[msg_id][0]:
        await asyncio.sleep(0.5)
        if time() - start_time > 60:
            bot_cache[msg_id][0] = False
            await editMessage(prompt, "<b>Decryption Key TimeOut.. Try Again</b>")
            bot_cache[msg_id][2] = True
    message.bot.remove_handler(handler)
    
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
    fernet = Fernet(key.encode())
    return fernet, is_cancelled

@router.message(filters=filters.Command("start") & filters.Private)
async def start_command(message: types.Message):
    await sendMessage(message, "Hello, World!")

async def main():
    await bot.delete_webhook(drop_pending_updates=True)
    await bot.set_my_commands([
        types.BotCommand("start", "Start the bot", scope=types.BotCommandScopeDefault()),
        types.BotCommand("exportsession", "Generate Pyrogram Session", scope=types.BotCommandScopeDefault()),
        types.BotCommand("decrypt", "Decrypt message", scope=types.BotCommandScopeDefault())
    ])
    await start_webhook(bot, "0.0.0.0", port=int(os.environ.get("PORT", "80")), url_path="")

if __name__ == "__main__":
    bot = Bot(token=os.environ["BOT_TOKEN"])
    bot_cache = {}
    asyncio.run(main())
