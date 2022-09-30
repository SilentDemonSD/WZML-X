import random
from random import choice
from random import SystemRandom
from re import T
from string import ascii_letters, digits
from telegram.ext import CommandHandler
from threading import Thread
from time import sleep
from pyrogram import enums

from bot.helper.mirror_utils.upload_utils.gdriveTools import GoogleDriveHelper
from bot.helper.ext_utils.timegap import timegap_check
from bot.helper.telegram_helper.message_utils import sendMessage, sendMarkup, deleteMessage, delete_all_messages, update_all_messages, sendStatusMessage, auto_delete_upload_message, auto_delete_message, sendFile, sendPhoto
from bot.helper.telegram_helper.filters import CustomFilters
from bot.helper.telegram_helper.bot_commands import BotCommands
from bot.helper.mirror_utils.status_utils.clone_status import CloneStatus
from bot import *
from bot.helper.ext_utils.bot_utils import *
from bot.helper.mirror_utils.download_utils.direct_link_generator import *
from bot.helper.ext_utils.exceptions import DirectDownloadLinkException
from telegram import ParseMode
from bot.helper.telegram_helper.button_build import ButtonMaker

def _clone(message, bot):
    if AUTO_DELETE_UPLOAD_MESSAGE_DURATION != -1:
        reply_to = message.reply_to_message
        if reply_to is not None:
            reply_to.delete()
        auto_delete_message = int(AUTO_DELETE_UPLOAD_MESSAGE_DURATION / 60)
        if message.chat.type == 'private':
            warnmsg = ''
        else:
            if EMOJI_THEME is True:
                warnmsg = f'<b>❗ This message will be deleted in <i>{auto_delete_message} minutes</i> from this group.</b>\n'
            else:
                warnmsg = f'<b>This message will be deleted in <i>{auto_delete_message} minutes</i> from this group.</b>\n'
    else:
        warnmsg = ''
    if BOT_PM and message.chat.type != 'private':
        if EMOJI_THEME is True:
            pmwarn = f"<b>😉I have sent files in PM.</b>\n"
        else:
            pmwarn = f"<b>I have sent files in PM.</b>\n"
    elif message.chat.type == 'private':
        pmwarn = ''
    else:
        pmwarn = ''
    if MIRROR_LOGS and message.chat.type != 'private':
        if EMOJI_THEME is True:
            logwarn = f"<b>⚠️ I have sent files in Mirror Log Channel. Join <a href=\"{MIRROR_LOG_URL}\">Mirror Log channel</a> </b>\n"
        else:
            logwarn = f"<b>I have sent files in Mirror Log Channel. Join <a href=\"{MIRROR_LOG_URL}\">Mirror Log channel</a> </b>\n"
    elif message.chat.type == 'private':
        logwarn = ''
    else:
        logwarn = ''
    buttons = ButtonMaker()	
    if FSUB:
        try:
            user = bot.get_chat_member(f"{FSUB_CHANNEL_ID}", message.from_user.id)
            LOGGER.info(user.status)
            if user.status not in ("member", "creator", "administrator", "supergroup"):
                if message.from_user.username:
                    uname = f'<a href="tg://user?id={message.from_user.id}">{message.from_user.username}</a>'
                else:
                    uname = f'<a href="tg://user?id={message.from_user.id}">{message.from_user.first_name}</a>'
                buttons = ButtonMaker()
                chat_u = CHANNEL_USERNAME.replace("@", "")
                buttons.buildbutton("👉🏻 CHANNEL LINK 👈🏻", f"https://t.me/{chat_u}")
                help_msg = f"Dᴇᴀʀ {uname},\nYᴏᴜ ɴᴇᴇᴅ ᴛᴏ ᴊᴏɪɴ ᴍʏ Cʜᴀɴɴᴇʟ ᴛᴏ ᴜsᴇ Bᴏᴛ \n\nCʟɪᴄᴋ ᴏɴ ᴛʜᴇ ʙᴇʟᴏᴡ Bᴜᴛᴛᴏɴ ᴛᴏ ᴊᴏɪɴ ᴍʏ Cʜᴀɴɴᴇʟ."
                reply_message = sendMarkup(help_msg, bot, message, buttons.build_menu(2))
                Thread(target=auto_delete_message, args=(bot, message, reply_message)).start()
                return reply_message
        except Exception:
            pass
            
    if BOT_PM and message.chat.type != 'private':
        try:
            msg1 = f'Added your Requested link to Download\n'
            send = bot.sendMessage(message.from_user.id, text=msg1)
            send.delete()
        except Exception as e:
            LOGGER.warning(e)
            bot_d = bot.get_me()
            b_uname = bot_d.username
            uname = f'<a href="tg://user?id={message.from_user.id}">{message.from_user.first_name}</a>'
            botstart = f"http://t.me/{b_uname}"
            buttons.buildbutton("Click Here to Start Me", f"{botstart}")
            startwarn = f"Dear {uname},\n\n<b>I found that you haven't started me in PM (Private Chat) yet.</b>\n\n" \
                        f"From now on i will give link and leeched files in PM and log channel only"
            message = sendMarkup(startwarn, bot, message, buttons.build_menu(2))
            return


    total_task = len(download_dict)
    user_id = message.from_user.id
    if user_id != OWNER_ID and user_id not in SUDO_USERS and user_id not in PAID_USERS:
        if PAID_SERVICE is True:
            if TOTAL_TASKS_LIMIT == total_task:
                return sendMessage(f"<b>Bᴏᴛ Tᴏᴛᴀʟ Tᴀsᴋ Lɪᴍɪᴛ : {TOTAL_TASKS_LIMIT}\nTᴀsᴋs Pʀᴏᴄᴇssɪɴɢ : {total_task}\n#total limit exceed </b>\n#Buy Paid Service", bot ,message)
            if USER_TASKS_LIMIT == get_user_task(user_id):
                return sendMessage(f"<b>Bᴏᴛ Usᴇʀ Tᴀsᴋ Lɪᴍɪᴛ : {USER_TASKS_LIMIT} \nYᴏᴜʀ Tᴀsᴋs : {get_user_task(user_id)}\n#user limit exceed</b>\n#Buy Paid Service", bot ,message)
        else:
            if TOTAL_TASKS_LIMIT == total_task:
                return sendMessage(f"<b>Bᴏᴛ Tᴏᴛᴀʟ Tᴀsᴋ Lɪᴍɪᴛ : {TOTAL_TASKS_LIMIT}\nTᴀsᴋs Pʀᴏᴄᴇssɪɴɢ : {total_task}\n#total limit exceed </b>", bot ,message)
            if USER_TASKS_LIMIT == get_user_task(user_id):
                return sendMessage(f"<b>Bᴏᴛ Usᴇʀ Tᴀsᴋ Lɪᴍɪᴛ : {USER_TASKS_LIMIT} \nYᴏᴜʀ Tᴀsᴋs : {get_user_task(user_id)}\n#user limit exceed</b>", bot ,message)

    if user_id != OWNER_ID and user_id not in SUDO_USERS and user_id not in PAID_USERS:
        time_gap = timegap_check(message)
        if time_gap:
            return
        TIME_GAP_STORE[message.from_user.id] = time()

    args = message.text.split()
    reply_to = message.reply_to_message
    link = ''
    multi = 0

    if len(args) > 1:
        link = args[1].strip()
        if link.strip().isdigit():
            multi = int(link)
            link = ''
        elif message.from_user.username:
            tag = f"@{message.from_user.username}"
        else:
            tag = message.from_user.mention_html(message.from_user.first_name)
    if reply_to:
        if len(link) == 0:
            link = reply_to.text.split(maxsplit=1)[0].strip()
        if reply_to.from_user.username:
            tag = f"@{reply_to.from_user.username}"
        else:
            tag = reply_to.from_user.mention_html(reply_to.from_user.first_name)
    

    is_gdtot = is_gdtot_link(link)
    is_unified = is_unified_link(link)
    is_udrive = is_udrive_link(link)
    if (is_gdtot or is_unified or is_udrive):
        try:
            msg = sendMessage(f"Processing: <code>{link}</code>", bot, message)
            LOGGER.info(f"Processing: {link}")
            if is_unified:
                link = unified(link)
            if is_gdtot:
                link = gdtot(link)
            if is_udrive:
                link = udrive(link)
            LOGGER.info(f"Processing GdToT: {link}")
            deleteMessage(bot, msg)
        except DirectDownloadLinkException as e:
            deleteMessage(bot, msg)
            return sendMessage(str(e), bot, message)
    if is_gdrive_link(link):
        gd = GoogleDriveHelper()
        res, size, name, files = gd.helper(link)
        if res != "":
            return sendMessage(res, bot, message)
        if STOP_DUPLICATE:
            LOGGER.info('Checking File/Folder if already in Drive...')
            if TELEGRAPH_STYLE is True:
                smsg, button = gd.drive_list(name, True, True)
                if smsg:
                    msg3 = "Someone already mirrored it for you !\nHere you go:"
                    return sendMarkup(msg3, bot, message, button)
            else:
                cap, f_name = gd.drive_list(name, True, True)
                if cap:
                    cap = f"File/Folder is already available in Drive. Here are the search results:\n\n{cap}"
                    sendFile(bot, message, f_name, cap)
                    return
        if CLONE_LIMIT is not None and user_id != OWNER_ID and user_id not in SUDO_USERS and user_id not in PAID_USERS:
            LOGGER.info('Checking File/Folder Size...')
            if size > CLONE_LIMIT * 1024**3:
                msg2 = f'Failed, Clone limit is {CLONE_LIMIT}GB.\nYour File/Folder size is {get_readable_file_size(size)}.'
                return sendMessage(msg2, bot, message)
        if multi > 1:
            sleep(4)
            nextmsg = type('nextmsg', (object, ), {'chat_id': message.chat_id, 'message_id': message.reply_to_message.message_id + 1})
            cmsg = message.text.split()
            cmsg[1] = f"{multi - 1}"
            nextmsg = sendMessage(" ".join(cmsg), bot, nextmsg)
            nextmsg.from_user.id = message.from_user.id
            sleep(4)
            Thread(target=_clone, args=(nextmsg, bot)).start()
        if files <= 20:
            msg = sendMessage(f"Cloning: <code>{link}</code>", bot, message)
            result, button = gd.clone(link)
            deleteMessage(bot, msg)
            if BOT_PM and FORCE_BOT_PM:
                if message.chat.type != 'private':
                    if EMOJI_THEME is True:
                        msg = f"<b>🗂️ Name: </b><{NAME_FONT}>{escape(name)}</{NAME_FONT}>\n"
                    else:
                        msg = f"<b>Name: </b><{NAME_FONT}>{escape(name)}</{NAME_FONT}>\n"
                    botpm = f"\n<b>Hey {tag}!, I have sent your cloned links in PM.</b>\n"
                    buttons = ButtonMaker()
                    b_uname = bot.get_me().username
                    botstart = f"http://t.me/{b_uname}"
                    buttons.buildbutton("View links in PM", f"{botstart}")
                    if PICS:
                        sendPhoto(msg + botpm, bot, message, random.choice(PICS), buttons.build_menu(2))
                    else:
                        sendMarkup(msg + botpm, bot, message, buttons.build_menu(2))
                else:
                    if EMOJI_THEME is True:
                        cc = f'\n<b>╰👤 #Clone_By: </b>{tag}\n\n'
                    else:
                        cc = f'\n<b>╰ #Clone_By: </b>{tag}\n\n'
                    if PICS:
                        sendPhoto(result + cc, bot, message, random.choice(PICS), button)
                    else:
                        sendMarkup(result + cc, bot, message, button)
                message.delete()
                reply_to = message.reply_to_message
                if reply_to is not None and AUTO_DELETE_UPLOAD_MESSAGE_DURATION == -1:
                    reply_to.delete()
        else:
            drive = GoogleDriveHelper(name)
            gid = ''.join(SystemRandom().choices(ascii_letters + digits, k=12))
            clone_status = CloneStatus(drive, size, message, gid)
            with download_dict_lock:
                download_dict[message.message_id] = clone_status
            sendStatusMessage(message, bot)
            result, button = drive.clone(link)
            with download_dict_lock:
                del download_dict[message.message_id]
                count = len(download_dict)
            try:
                if count == 0:
                    Interval[0].cancel()
                    del Interval[0]
                    delete_all_messages()
                    if BOT_PM and FORCE_BOT_PM:
                        if message.chat.type != 'private':
                            if EMOJI_THEME is True:
                                msg = f"<b>🗂️ Name: </b><{NAME_FONT}>{escape(name)}</{NAME_FONT}>\n"
                            else:
                                msg = f"<b>Name: </b><{NAME_FONT}>{escape(name)}</{NAME_FONT}>\n"
                            botpm = f"\n<b>Hey {tag}!, I have sent your cloned links in PM.</b>\n"
                            buttons = ButtonMaker()
                            b_uname = bot.get_me().username
                            botstart = f"http://t.me/{b_uname}"
                            buttons.buildbutton("View links in PM", f"{botstart}")
                            if PICS:
                                sendPhoto(msg + botpm, bot, message, random.choice(PICS), buttons.build_menu(2))
                            else:
                                sendMarkup(msg + botpm, bot, message, buttons.build_menu(2))
                        else:
                            if EMOJI_THEME is True:
                                cc = f'\n<b>╰👤 #Clone_By: </b>{tag}\n\n'
                            else:
                                cc = f'\n<b>╰ #Clone_By: </b>{tag}\n\n'
                            if PICS:
                                sendPhoto(result + cc, bot, message, random.choice(PICS), button)
                            else:
                                sendMarkup(result + cc, bot, message, button)       
                        message.delete()
                        reply_to = message.reply_to_message
                        if reply_to is not None and AUTO_DELETE_UPLOAD_MESSAGE_DURATION == -1:
                            reply_to.delete()
                else:
                    update_all_messages()
            except IndexError:
                pass

        mesg = message.text.split('\n')
        message_args = mesg[0].split(' ', maxsplit=1)
        user_id = message.from_user.id
        tag = f"@{message.from_user.username}"
        if EMOJI_THEME is True:
            slmsg = f"╭🗂️ Name: <{NAME_FONT}>{escape(name)}</{NAME_FONT}>\n"
            slmsg += f"├📐 Size: {size}\n"
            slmsg += f"╰👥 Added by: {tag} | <code>{user_id}</code>\n\n"
        else:
            slmsg = f"╭ Name: <{NAME_FONT}>{escape(name)}</{NAME_FONT}>\n"
            slmsg += f"├ Size: {size}\n"
            slmsg += f"╰ Added by: {tag} | <code>{user_id}</code>\n\n"
        if LINK_LOGS:
                try:
                    upper = f"‒‒‒‒‒‒‒‒‒‒‒‒‒‒‒‒‒‒‒‒‒‒‒‒‒‒‒‒‒‒‒‒\n"
                    source_link = f"<code>{message_args[1]}</code>\n"
                    lower = f"‒‒‒‒‒‒‒‒‒‒‒‒‒‒‒‒‒‒‒‒‒‒‒‒‒‒‒‒‒‒‒‒\n"
                    for link_log in LINK_LOGS:
                        bot.sendMessage(link_log, text=slmsg + upper + source_link + lower, parse_mode=ParseMode.HTML )
                except IndexError:
                    pass
                if reply_to is not None:
                    try:
                        reply_text = reply_to.text
                        if is_url(reply_text):
                            upper = f"‒‒‒‒‒‒‒‒‒‒‒‒‒‒‒‒‒‒‒‒‒‒‒‒‒‒‒‒‒‒‒‒\n"
                            source_link = f"<code>{reply_text.strip()}</code>\n"
                            lower = f"‒‒‒‒‒‒‒‒‒‒‒‒‒‒‒‒‒‒‒‒‒‒‒‒‒‒‒‒‒‒‒‒\n"
                            for link_log in LINK_LOGS:
                                bot.sendMessage(chat_id=link_log, text=slmsg + upper + source_link + lower, parse_mode=ParseMode.HTML )
                    except TypeError:
                        pass  

        if EMOJI_THEME is True:
            cc = f'\n<b>╰👤 #Clone_By: </b>{tag}\n\n'
        else:
            cc = f'\n<b>╰ #Clone_By: </b>{tag}\n\n'
        if button in ["cancelled", ""]:
            sendMessage(f"{tag} {result}", bot, message)
        else:
            LOGGER.info(f'Cloning Done: {name}')
            if FORCE_BOT_PM is False:
                if PICS:
                    msg = sendPhoto(result + cc + pmwarn + logwarn + warnmsg, bot, message, random.choice(PICS), button)
                else:
                    msg = sendMarkup(result + cc + pmwarn + logwarn + warnmsg, bot, message, button)
                Thread(target=auto_delete_upload_message, args=(bot, message, msg)).start()
        if (is_gdtot or is_unified or is_udrive):
            gd.deletefile(link)

        if MIRROR_LOGS:	
            try:	
                for chatid in MIRROR_LOGS:	
                    bot.sendMessage(chat_id=chatid, text=result + cc, reply_markup=button, parse_mode=ParseMode.HTML)	
            except Exception as e:	
                LOGGER.warning(e)	
        if BOT_PM and message.chat.type != 'private':	
            try:	
                bot.sendMessage(message.from_user.id, text=result + cc, reply_markup=button,	
                                parse_mode=ParseMode.HTML)	
            except Exception as e:	
                LOGGER.warning(e)	
                return


    else:
        sendMessage('Send Gdrive or GDToT/AppDrive/DriveApp/GDFlix/DriveBit/DrivePro/DriveAce/DriveSharer/HubDrive/DriveHub/KatDrive/Kolop/DriveFire link along with command or by replying to the link by command', bot, message)

@new_thread
def cloneNode(update, context):
    _clone(update.message, context.bot)

if CLONE_ENABLED:
    clone_handler = CommandHandler(BotCommands.CloneCommand, cloneNode, filters=CustomFilters.authorized_chat | CustomFilters.authorized_user, run_async=True)
else:
    clone_handler = CommandHandler(BotCommands.CloneCommand, cloneNode, filters=CustomFilters.owner_filter | CustomFilters.authorized_user, run_async=True)

dispatcher.add_handler(clone_handler)