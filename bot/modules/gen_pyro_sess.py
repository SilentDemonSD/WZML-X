#!/usr/bin/env python3
from time import time
from asyncio import sleep
from functools import partial

from pyrogram.filters import command, private, user, text
from pyrogram.handlers import MessageHandler
from pyrogram.errors import SessionPasswordNeeded, FloodWait, PhoneNumberInvalid, ApiIdInvalid, PhoneCodeInvalid, PhoneCodeExpired, UsernameNotOccupied, ChatAdminRequired, PeerIdInvalid

from bot import bot
from bot.helper.telegram_helper.message_utils import sendMessage, editMessage, sendFile
from bot.helper.telegram_helper.filters import CustomFilters

API_TEXT = """Pyrogram's String Session Generator Bot. I will generate String Session 
Now send your `API_ID` same as `APP_ID` to Start Generating Session.

Get `APP_ID` from https://my.telegram.org or @UseTGzKBot."""

HASH_TEXT = "Now send your `API_HASH`.\n\nGet `API_HASH` from https://my.telegram.org Or @UseTGzKBot.\n\nPress /cancel to Cancel Task."

PHONE_NUMBER_TEXT = (
    "Now send your Telegram account's Phone number in International Format. \n"
    "Including Country code. Example: **+14154566376**\n\n"
    "Press /cancel to Cancel Task."
)
session_dict = {}

is_stopped = False

async def genPyroString(client, message):
    global is_stopped
    sess_msg = await sendMessage(message, API_TEXT)
    await event_handler(client, message, 'API_ID')
    if is_stopped:
        return
    try:
        client_api = int(session_dict['API_ID'])
    except Exception:
        await editMessage(sess_msg, "`APP_ID` is Invalid.\nPress / to Start again.")
        return
    await editMessage(sess_msg, HASH_TEXT)
    await event_handler(client, message, 'API_HASH')
    if is_stopped:
        return
    api_hash = session_dict['API_HASH']
    if not len(api_hash) >= 30:
        await editMessage(sess_msg, "`API_HASH` is Invalid.\nPress / to Start again.")
        return
    await editMessage(sess_msg, PHONE_NUMBER_TEXT)
    while True:
        await event_handler(client, message, 'PHONE_NO')
        if is_stopped:
            return
        await editMessage(sess_msg, "Is {session_dict['PHONE_NO']}  correct? (y/n):` \n\nSend: `y` (If Yes)\nSend: `n` (If No)")
        await event_handler(client, message, 'CONFIRM_PHN')
        if is_stopped:
            return
        if session_dict['CONFIRM_PHN'].lower() == 'y':
            break
    try:
        pyro_client = Client("Pyro-WZML-X", api_id=api_id, api_hash=api_hash)
    except Exception as e:
        await editMessage(sess_msg ,f"**ERROR:** `{str(e)}`\nPress /start to Start again.")
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
        await editMessage(sess_msg, f"Floodwait of {e.value} Seconds")
        return
    except ApiIdInvalid:
        await editMessage(sess_msg, "APP ID and API Hash are Invalid.\n\nPress /start to Start again.")
        return
    except PhoneNumberInvalid:
        await editMessage(sess_msg, "Your Phone Number is Invalid.\n\nPress /start to Start again.")
        return
    await editMessage(sess_msg, ("An OTP is sent to your phone number, "
                      "Please enter OTP in `1 2 3 4 5` format. __(Space between each numbers!)__ \n\n"
                      "If Bot not sending OTP then try /restart and Start Task again with /start command to Bot.\n"
                      "Press /cancel to Cancel."))
    await event_handler(client, message, 'OTP')
    if is_stopped:
        return
    try:
        await pyro_client.sign_in(session_dict['PHONE_NO'], user_code.phone_code_hash, phone_code=' '.join(str(session_dict['OTP'])))
    except PhoneCodeInvalid:
        await editMessage(sess_msg, "Invalid Code.\n\nPress /start to Start again.")
        return
    except PhoneCodeExpired:
        await editMessage(sess_msg, "Code is Expired.\n\nPress /start to Start again.")
        return
    except SessionPasswordNeeded:
        await editMessage(sess_msg, "Your account have Two-Step Verification.\nPlease enter your Password.\n\nPress /cancel to Cancel.")
        await event_handler(client, message, 'TWO_STEP_PASS')
        if is_stopped:
            return
        try:
            await pyro_client.check_password(session_dict['TWO_STEP_PASS'])
        except Exception as e:
            await editMessage(sess_msg, f"**ERROR:** `{str(e)}`")
            return
    except Exception as e:
        await editMessage(sess_msg ,f"**ERROR:** `{str(e)}`")
        return
    try:
        session_string = await pyro_client.export_session_string()
        await pyro_client.send_message("me", f"***Pyrogram V2 Session***\n\n```{session_string}```")
        await pyro_client.disconnect()
        text = "String Session is Successfully Generated."
        await editMessage(sess_msg, text)
    except Exception as e:
        await editMessage(sess_msg ,f"**ERROR:** `{str(e)}`")
        return
    
async def event_handler(client, message, key):
    global is_stopped
    user_id = message.from_user.id
    session_dict[user_id] = True
    start_time = time()
    
    async def set_details(client, message, newkey):
        global is_stopped
        user_id = message.from_user.id
        session_dict[user_id] = False
        value = message.text
        await message.delete()
        if value == '/stop':
            is_stopped = True
            await sendMessage(message, 'Process Canceled')
            return
        session_dict[newkey] = value
    
    pfunc = partial(set_details, newkey=key)
    handler = client.add_handler(MessageHandler(
        pfunc, filters=user(user_id) & text & private), group=-1)
    while session_dict[user_id]:
        await sleep(0.5)
        if time() - start_time > 120:
            session_dict[user_id] = False
            is_stopped = True
    client.remove_handler(*handler)
    
bot.add_handler(MessageHandler(genPyroString, filters=command('exportsession') & CustomFilters.owner))