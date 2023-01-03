from random import choice as rchoice, SystemRandom
from html import escape
from string import ascii_letters, digits
from threading import Thread
from time import sleep, time

from bot.helper.ext_utils.bot_utils import is_sudo, is_paid, get_user_task, get_category_buttons, get_readable_file_size, getUserTDs, \
                    new_thread, get_bot_pm, is_url, is_gdrive_link, is_gdtot_link, is_udrive_link, is_sharer_link, \
                    is_sharedrive_link, is_filepress_link, userlistype
from bot.helper.ext_utils.exceptions import DirectDownloadLinkException
from bot.helper.ext_utils.timegap import timegap_check
from bot.helper.mirror_utils.download_utils.direct_link_generator import gdtot, udrive, sharer_pw_dl, shareDrive, filepress
from bot.helper.mirror_utils.status_utils.clone_status import CloneStatus
from bot.helper.mirror_utils.upload_utils.gdriveTools import GoogleDriveHelper
from bot.helper.telegram_helper.bot_commands import BotCommands
from bot.helper.telegram_helper.button_build import ButtonMaker
from bot.helper.telegram_helper.filters import CustomFilters
from bot.helper.telegram_helper.message_utils import sendMessage, editMessage, deleteMessage, delete_all_messages, update_all_messages, sendStatusMessage, auto_delete_upload_message, sendFile, sendPhoto, forcesub, isAdmin
from bot import LOGGER, download_dict, config_dict, user_data, OWNER_ID, TIME_GAP_STORE, CATEGORY_NAMES, btn_listener, download_dict_lock, \
                    Interval, dispatcher
from telegram import ParseMode
from telegram.ext import CallbackQueryHandler, CommandHandler


def _clone(message, bot):
    user_id = message.from_user.id
    buttons = ButtonMaker()
    if not isAdmin(message):
        if message.from_user.username:
            tag = f"@{message.from_user.username}"
        else:
            tag = message.from_user.mention_html(message.from_user.first_name)
        if forcesub(bot, message, tag):
            return
            
    if get_bot_pm(user_id) and message.chat.type != 'private':
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
            message = sendMessage(startwarn, bot, message, buttons.build_menu(2))
            return

    total_task = len(download_dict)
    USER_TASKS_LIMIT = config_dict['USER_TASKS_LIMIT']
    TOTAL_TASKS_LIMIT = config_dict['TOTAL_TASKS_LIMIT']
    if user_id != OWNER_ID and not is_sudo(user_id) and not is_paid(user_id):
        if config_dict['PAID_SERVICE'] is True:
            if TOTAL_TASKS_LIMIT == total_task:
                return sendMessage(f"<b>BOT TOTAL TASK LIMIT : {TOTAL_TASKS_LIMIT}\nTASKS PROCESSING : {total_task}\n#total limit exceed </b>\n#Buy Paid Service", bot ,message)
            if USER_TASKS_LIMIT == get_user_task(user_id):
                return sendMessage(f"<b>BOT USER TASK LIMIT : {USER_TASKS_LIMIT} \nYOUR TASK : {get_user_task(user_id)}\n#user limit exceed</b>\n#Buy Paid Service", bot ,message)
        else:
            if TOTAL_TASKS_LIMIT == total_task:
                return sendMessage(f"<b>BOT TOTAL TASK LIMIT : {TOTAL_TASKS_LIMIT}\nTASKS PROCESSING : {total_task}\n#total limit exceed </b>", bot ,message)
            if USER_TASKS_LIMIT == get_user_task(user_id):
                return sendMessage(f"<b>BOT USER TASK LIMIT : {USER_TASKS_LIMIT} \nYOUR TASK : {get_user_task(user_id)}\n#user limit exceed</b>", bot ,message)
        time_gap = timegap_check(message)
        if time_gap:
            return
        TIME_GAP_STORE[message.from_user.id] = time()

    mesg = message.text
    reply_to = message.reply_to_message
    link = ''
    index = 1
    multi = 0
    c_index = 0
    u_index = None
    shwbtns = True
    msg_id = message.message_id
    CATUSR = getUserTDs(user_id)[0] 
    if len(CATUSR) >= 1: u_index = 0

    if len(mesg.split(maxsplit=1)) > 1:
        args = mesg.split(maxsplit=2)
        for x in args:
            x = x.strip()
            if x.startswith('c:'):
                index += 1
                cargs = x.split(':')
                dname = cargs[1].strip() if cargs[1] else None
                utds = getUserTDs(user_id)[0]
                if len(utds) != 0:
                    ltds = [td.lower() for td in utds]
                    if dname and dname.lower() in ltds:
                        shwbtns = False
                        u_index = ltds.index(dname.lower())
                elif len(CATEGORY_NAMES) > 1:
                    ltds = [td.lower() for td in CATEGORY_NAMES]
                    if dname and dname.lower() in ltds:
                        shwbtns = False
                        c_index = ltds.index(dname.lower())
            elif x.isdigit():
                multi = int(x)
                mi = index
                link = ''
        if multi == 0:
            message_args = mesg.split(maxsplit=index)
            if len(message_args) > index:
                link = message_args[index].strip()
        if message.from_user.username:
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

    if not (is_gdrive_link(link) or (link.strip().isdigit() and multi == 0) or is_gdtot_link(link) or is_udrive_link(link) or is_sharer_link(link) or is_sharedrive_link(link) or is_filepress_link(link)):
        return sendMessage("Send Gdrive or GDToT/HubDrive/DriveHub(ws)/KatDrive/Kolop/DriveFire/FilePress/SharerPw/ShareDrive link along with command or by replying to the link by command\n\n<b>Multi links only by replying to first link/file:</b>\n<code>/cmd</code> 10(number of links/files)", bot, message)

    timeout = 60
    listener = [bot, message, c_index, u_index, timeout, time(), tag, link]
    if ((len(CATEGORY_NAMES) > 1 and len(CATUSR) == 0) or (len(CATEGORY_NAMES) >= 1 and len(CATUSR) > 1)) and shwbtns:
        text, btns = get_category_buttons('clone', timeout, msg_id, c_index, u_index, user_id)
        btn_listener[msg_id] = listener
        engine = sendMessage(text, bot, message, btns)
        _auto_start_dl(engine, msg_id, timeout)
    else:
        start_clone(listener)

    if multi > 1:
        sleep(4)
        nextmsg = type('nextmsg', (object, ), {'chat_id': message.chat_id, 'message_id': message.reply_to_message.message_id + 1})
        cmsg = message.text.split(maxsplit=mi+1)
        cmsg[mi] = f"{multi - 1}"
        nextmsg = sendMessage(" ".join(cmsg), bot, nextmsg)
        nextmsg.from_user.id = message.from_user.id
        sleep(4)
        Thread(target=_clone, args=(nextmsg, bot)).start()

@new_thread
def _auto_start_dl(msg, msg_id, time_out):
    sleep(time_out)
    try:
        info = btn_listener[msg_id]
        del btn_listener[msg_id]
        editMessage("Timed out! Task has been started.", msg)
        start_clone(info)
    except:
        pass

@new_thread
def start_clone(listelem):
    bot = listelem[0]
    message = listelem[1]
    c_index = listelem[2]
    u_index = listelem[3]
    tag = listelem[6]
    link = listelem[7]
    user_id = message.from_user.id
    BOT_PM_X = get_bot_pm(user_id)
    reply_to = message.reply_to_message

    is_gdtot = is_gdtot_link(link)
    is_udrive = is_udrive_link(link)
    is_sharer = is_sharer_link(link)
    is_sharedrive = is_sharedrive_link(link)
    is_filepress = is_filepress_link(link)
    if (is_gdtot or is_udrive or is_sharer or is_sharedrive or is_filepress):
        try:
            LOGGER.info(f"Processing: {link}")
            if is_gdtot:
                msg = sendMessage(f"GDTOT LINK DETECTED !", bot, message)
                link = gdtot(link)
            elif is_udrive:
                msg = sendMessage(f"UDRIVE LINK DETECTED !", bot, message)
                link = udrive(link)
            elif is_sharer:
                msg = sendMessage(f"SHARER LINK DETECTED !", bot, message)
                link = sharer_pw_dl(link)
            elif is_sharedrive:
                msg = sendMessage(f"SHAREDRIVE LINK DETECTED !", bot, message)
                link = shareDrive(link)
            elif is_filepress:
                msg = sendMessage(f"FILEPRESS LINK DETECTED !", bot, message)
                link = filepress(link)
            LOGGER.info(f"Generated GDrive Link: {link}")
            deleteMessage(bot, msg)
        except DirectDownloadLinkException as e:
            deleteMessage(bot, msg)
            return sendMessage(str(e), bot, message)

    gd = GoogleDriveHelper(user_id=user_id)
    res, size, name, files = gd.helper(link)
    user_dict = user_data.get(user_id, False)
    IS_USRTD = user_dict.get('is_usertd') if user_dict and user_dict.get('is_usertd') else False
    if res != "":
        return sendMessage(res, bot, message)
    if config_dict['STOP_DUPLICATE'] and IS_USRTD == False:
        LOGGER.info('Checking File/Folder if already in Drive...')
        smsg, button = gd.drive_list(name, True, True)
        if smsg:
            tegr, html, tgdi = userlistype(user_id)
            if tegr:
                return sendMessage("Someone already mirrored it for you !\nHere you go:", bot, message, button)
            elif html:
                return sendFile(bot, message, button, f"File/Folder is already available in Drive. Here are the search results:\n\n{smsg}")
            else: return sendMessage(smsg, bot, message, button)

    CLONE_LIMIT = config_dict['CLONE_LIMIT']
    if CLONE_LIMIT != '' and user_id != OWNER_ID and not is_sudo(user_id) and not is_paid(user_id):
        LOGGER.info('Checking File/Folder Size...')
        if size > (CLONE_LIMIT * 1024**3):
            msg2 = f'Failed, Clone limit is {CLONE_LIMIT}GB.\nYour File/Folder size is {get_readable_file_size(size)}.'
            return sendMessage(msg2, bot, message)

    if files <= 20:
        msg = sendMessage(f"Cloning: <code>{link}</code>", bot, message)
        result, button = gd.clone(link, u_index, c_index)
        deleteMessage(bot, msg)
        if BOT_PM_X:
            if message.chat.type != 'private':
                if config_dict['EMOJI_THEME']:
                    msg = f"<b>🗂️ Name: </b><{config_dict['NAME_FONT']}>{escape(name)}</{config_dict['NAME_FONT']}>\n"
                else:
                    msg = f"<b>Name: </b><{config_dict['NAME_FONT']}>{escape(name)}</{config_dict['NAME_FONT']}>\n"
                botpm = f"\n<b>Hey {tag}!, I have sent your cloned links in PM.</b>\n"
                buttons = ButtonMaker()
                b_uname = bot.get_me().username
                botstart = f"http://t.me/{b_uname}"
                buttons.buildbutton("View links in PM", f"{botstart}")
                if config_dict['PICS']:
                    sendPhoto(msg + botpm, bot, message, rchoice(config_dict['PICS']), buttons.build_menu(2))
                else:
                    sendMessage(msg + botpm, bot, message, buttons.build_menu(2))
            else:
                if config_dict['EMOJI_THEME']:
                    cc = f'\n<b>╰👤 #Clone_By: </b>{tag}\n\n'
                else:
                    cc = f'\n<b>╰ #Clone_By: </b>{tag}\n\n'
                if config_dict['PICS']:
                    sendPhoto(result + cc, bot, message, rchoice(config_dict['PICS']), button)
                else:
                    sendMessage(result + cc, bot, message, button)
            message.delete()
            if reply_to is not None and config_dict['AUTO_DELETE_UPLOAD_MESSAGE_DURATION'] == -1:
                reply_to.delete()
    else:
        drive = GoogleDriveHelper(name, user_id=user_id)
        gid = ''.join(SystemRandom().choices(ascii_letters + digits, k=12))
        clone_status = CloneStatus(drive, size, message, gid)
        with download_dict_lock:
            download_dict[message.message_id] = clone_status
        sendStatusMessage(message, bot)
        result, button = drive.clone(link, u_index, c_index)
        with download_dict_lock:
            del download_dict[message.message_id]
            count = len(download_dict)
        try:
            if count == 0:
                Interval[0].cancel()
                del Interval[0]
                delete_all_messages()
                if BOT_PM_X:
                    if message.chat.type != 'private':
                        if config_dict['EMOJI_THEME']:
                            msg = f"<b>🗂️ Name: </b><{config_dict['NAME_FONT']}>{escape(name)}</{config_dict['NAME_FONT']}>\n"
                        else:
                            msg = f"<b>Name: </b><{config_dict['NAME_FONT']}>{escape(name)}</{config_dict['NAME_FONT']}>\n"
                        botpm = f"\n<b>Hey {tag}!, I have sent your cloned links in PM.</b>\n"
                        buttons = ButtonMaker()
                        b_uname = bot.get_me().username
                        botstart = f"http://t.me/{b_uname}"
                        buttons.buildbutton("View links in PM", f"{botstart}")
                        if config_dict['PICS']:
                            sendPhoto(msg + botpm, bot, message, rchoice(config_dict['PICS']), buttons.build_menu(2))
                        else:
                            sendMessage(msg + botpm, bot, message, buttons.build_menu(2))
                    else:
                        if config_dict['EMOJI_THEME']:
                            cc = f'\n<b>╰👤 #Clone_By: </b>{tag}\n\n'
                        else:
                            cc = f'\n<b>╰ #Clone_By: </b>{tag}\n\n'
                        if config_dict['PICS']:
                            sendPhoto(result + cc, bot, message, rchoice(config_dict['PICS']), button)
                        else:
                            sendMessage(result + cc, bot, message, button.build_menu(2))       
                    message.delete()
                    if reply_to is not None and config_dict['AUTO_DELETE_UPLOAD_MESSAGE_DURATION'] == -1:
                        reply_to.delete()
            else:
                update_all_messages()
        except IndexError:
            pass

    mesg = message.text.split('\n')
    message_args = mesg[0].split(' ', maxsplit=1)
    user_id = message.from_user.id
    tag = f"@{message.from_user.username}"
    if config_dict['EMOJI_THEME']:
        slmsg = f"╭🗂️ Name: <{config_dict['NAME_FONT']}>{escape(name)}</{config_dict['NAME_FONT']}>\n"
        slmsg += f"├📐 Size: {get_readable_file_size(size)}\n"
        slmsg += f"╰👥 Added by: {tag} | <code>{user_id}</code>\n\n"
    else:
        slmsg = f"╭ Name: <{config_dict['NAME_FONT']}>{escape(name)}</{config_dict['NAME_FONT']}>\n"
        slmsg += f"├ Size: {get_readable_file_size(size)}\n"
        slmsg += f"╰ Added by: {tag} | <code>{user_id}</code>\n\n"
    if 'link_logs' in user_data:
        try:
            upper = f"‒‒‒‒‒‒‒‒‒‒‒‒‒‒‒‒‒‒‒‒‒‒‒‒‒‒‒‒‒‒‒‒\n"
            source_link = f"<code>{message_args[1]}</code>\n"
            lower = f"‒‒‒‒‒‒‒‒‒‒‒‒‒‒‒‒‒‒‒‒‒‒‒‒‒‒‒‒‒‒‒‒\n"
            for link_log in user_data['link_logs']:
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
                    for link_log in user_data['link_logs']:
                        bot.sendMessage(chat_id=link_log, text=slmsg + upper + source_link + lower, parse_mode=ParseMode.HTML )
            except TypeError:
                pass  

    if config_dict['EMOJI_THEME']:
        cc = f'\n<b>╰👤 #Clone_By: </b>{tag}\n\n'
    else:
        cc = f'\n<b>╰ #Clone_By: </b>{tag}\n\n'
    if button.build_menu(2) in ["cancelled", ""]:
        sendMessage(f"{tag} {result}", bot, message)
    else:
        LOGGER.info(f'Cloning Done: {name}')
    if BOT_PM_X and message.chat.type != 'private':
        if config_dict['EMOJI_THEME']:
            pmwarn = f"<b>😉I have sent files in PM.</b>\n"
        else:
            pmwarn = f"<b>I have sent files in PM.</b>\n"
    else:
        pmwarn = ''
    if 'mirror_logs' in user_data and message.chat.type != 'private':
        if config_dict['EMOJI_THEME']:
            logwarn = f"<b>⚠️ I have sent files in Mirror Log Channel. Join <a href=\"{config_dict['MIRROR_LOG_URL']}\">Mirror Log channel</a> </b>\n"
        else:
            logwarn = f"<b>I have sent files in Mirror Log Channel. Join <a href=\"{config_dict['MIRROR_LOG_URL']}\">Mirror Log channel</a> </b>\n"
    else:
        logwarn = ''

    AUTO_DELETE_UPLOAD_MESSAGE_DURATION = config_dict["AUTO_DELETE_UPLOAD_MESSAGE_DURATION"]
    if AUTO_DELETE_UPLOAD_MESSAGE_DURATION != -1:
        if reply_to is not None:
            reply_to.delete()
        auto_delete_message = int(AUTO_DELETE_UPLOAD_MESSAGE_DURATION / 60)
        if message.chat.type == 'private':
            warnmsg = ''
        else:
            if config_dict['EMOJI_THEME']:
                warnmsg = f'<b>❗ This message will be deleted in <i>{auto_delete_message} minutes</i> from this group.</b>\n'
            else:
                warnmsg = f'<b>This message will be deleted in <i>{auto_delete_message} minutes</i> from this group.</b>\n'
    else:
        warnmsg = ''

    if config_dict['SAME_ACC_COOKIES']:
        if (is_gdtot or is_udrive or is_sharer or is_sharedrive):
            gd.deletefile(link)

    if BOT_PM_X and 'mirror_logs' in user_data:
        try:
            bot.sendMessage(message.from_user.id, text=result + cc, reply_markup=button.build_menu(2),
                            parse_mode=ParseMode.HTML)
            for chatid in user_data['mirror_logs']:
                if config_dict['SAVE_MSG']:
                    button.sbutton('Save This Message', 'save', 'footer')
                bot.sendMessage(chat_id=chatid, text=result + cc, reply_markup=button.build_menu(2), parse_mode=ParseMode.HTML)
        except Exception as e:
            LOGGER.warning(e)
    elif BOT_PM_X and not 'mirror_logs' in user_data:
        try:
            bot.sendMessage(message.from_user.id, text=result + cc, reply_markup=button.build_menu(2),
                            parse_mode=ParseMode.HTML)
        except Exception as e:
            LOGGER.warning(e)
    elif not BOT_PM_X and 'mirror_logs' in user_data:
        try:
            if config_dict['SAVE_MSG']:
                button.sbutton('Save This Message', 'save', 'footer')
            for chatid in user_data['mirror_logs']:
                bot.sendMessage(chat_id=chatid, text=result + cc, reply_markup=button.build_menu(2), parse_mode=ParseMode.HTML)
            if config_dict['PICS']:
                msg = sendPhoto(result + cc + pmwarn + logwarn + warnmsg, bot, message, rchoice(config_dict['PICS']), button.build_menu(2))
            else:
                msg = sendMessage(result + cc + pmwarn + logwarn + warnmsg, bot, message, button.build_menu(2))
            Thread(target=auto_delete_upload_message, args=(bot, message, msg)).start()
        except Exception as e:
            LOGGER.warning(e)
    elif not BOT_PM_X and not 'mirror_logs' in user_data:
        try:
            if config_dict['SAVE_MSG'] and message.chat.type != 'private':
                button.sbutton('Save This Message', 'save', 'footer')
            if config_dict['PICS']:
                msg = sendPhoto(result + cc + pmwarn + logwarn + warnmsg, bot, message, rchoice(config_dict['PICS']), button.build_menu(2))
            else:
                msg = sendMessage(result + cc + pmwarn + logwarn + warnmsg, bot, message, button.build_menu(2))
            Thread(target=auto_delete_upload_message, args=(bot, message, msg)).start()
        except Exception as e:
            LOGGER.warning(e)

@new_thread
def confirm_clone(update, context):
    query = update.callback_query
    user_id = query.from_user.id
    message = query.message
    data = query.data
    data = data.split()
    msg_id = int(data[2])
    try:
        listenerInfo = btn_listener[msg_id]
    except KeyError:
        return editMessage(f"<b>Download has been cancelled or already started!</b>", message)
    if user_id != listenerInfo[1].from_user.id:
        return query.answer("You are not the owner of this task!", show_alert=True)
    elif data[1] == 'scat':
        c_index = int(data[3])
        u_index = None
        if listenerInfo[2] == c_index:
            return query.answer(f"{CATEGORY_NAMES[c_index]} is selected already!", show_alert=True)
        query.answer()
        listenerInfo[2] = c_index
        listenerInfo[3] = u_index
    elif data[1] == 'ucat':
        u_index = int(data[3])
        c_index = 0
        if listenerInfo[3] == u_index:
            return query.answer(f"{getUserTDs(listenerInfo[1].from_user.id)[0][u_index]} is already selected!", show_alert=True)
        query.answer()
        listenerInfo[2] = c_index
        listenerInfo[3] = u_index
    elif data[1] == 'cancel':
        query.answer()
        del btn_listener[msg_id]
        return editMessage(f"<b>Download has been cancelled!</b>", message)
    elif data[1] == 'start':
        query.answer()
        del btn_listener[msg_id]
        message.delete()
        return start_clone(listenerInfo)
    timeout = listenerInfo[4] - (time() - listenerInfo[5])
    text, btns = get_category_buttons('clone', timeout, msg_id, listenerInfo[2], listenerInfo[3], listenerInfo[1].from_user.id)
    editMessage(text, message, btns)

@new_thread
def cloneNode(update, context):
    _clone(update.message, context.bot)


authfilter = CustomFilters.authorized_chat if config_dict['CLONE_ENABLED'] is True else CustomFilters.owner_filter
clone_handler = CommandHandler(BotCommands.CloneCommand, cloneNode,
                                    filters=authfilter | CustomFilters.authorized_user)
clone_confirm_handler = CallbackQueryHandler(confirm_clone, pattern="clone")
dispatcher.add_handler(clone_confirm_handler)
dispatcher.add_handler(clone_handler)
