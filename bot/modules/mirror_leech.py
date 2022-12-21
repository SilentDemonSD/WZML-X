from base64 import b64encode
from pyrogram import enums
from re import match as re_match, search as re_search, split as re_split
from time import sleep, time
from os import path as ospath, remove as osremove, listdir, walk
from shutil import rmtree
from threading import Thread
from subprocess import run as srun
from pathlib import PurePath
from telegram.ext import CommandHandler, CallbackQueryHandler
from telegram import ParseMode, InlineKeyboardButton

from bot import *
from bot.helper.ext_utils.bot_utils import *
from bot.helper.ext_utils.timegap import timegap_check
from bot.helper.ext_utils.exceptions import DirectDownloadLinkException, NotSupportedExtractionArchive
from bot.helper.ext_utils.shortenurl import short_url
from bot.helper.mirror_utils.download_utils.aria2_download import add_aria2c_download
from bot.helper.mirror_utils.download_utils.gd_downloader import add_gd_download
from bot.helper.mirror_utils.download_utils.qbit_downloader import add_qb_torrent
from bot.helper.mirror_utils.download_utils.mega_downloader import add_mega_download
from bot.helper.mirror_utils.download_utils.direct_link_generator import direct_link_generator
from bot.helper.mirror_utils.download_utils.telegram_downloader import TelegramDownloadHelper
from bot.helper.telegram_helper.bot_commands import BotCommands
from bot.helper.telegram_helper.filters import CustomFilters
from bot.helper.telegram_helper.message_utils import sendMessage, editMessage, delete_all_messages, update_all_messages, forcesub, auto_delete_upload_message, auto_delete_message, isAdmin
from bot.helper.ext_utils.telegraph_helper import telegraph
from bot.helper.telegram_helper.button_build import ButtonMaker
from .listener import MirrorLeechListener


def _mirror_leech(bot, message, isZip=False, extract=False, isQbit=False, isLeech=False):
    buttons = ButtonMaker()
    user_id = message.from_user.id
    msg_id = message.message_id

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
            reply_message = sendMessage(startwarn, bot, message, buttons.build_menu(2))
            Thread(target=auto_delete_message, args=(bot, message, reply_message)).start()
            return reply_message

    total_task = len(download_dict)
    USER_TASKS_LIMIT = config_dict['USER_TASKS_LIMIT']
    TOTAL_TASKS_LIMIT = config_dict['TOTAL_TASKS_LIMIT']
    if config_dict['DAILY_TASK_LIMIT'] and user_id != OWNER_ID and not is_sudo(user_id) and not is_paid(user_id) and config_dict['DAILY_TASK_LIMIT'] <= getdailytasks(user_id):
        msg = f"<b>Daily Total Task Limit : {config_dict['DAILY_TASK_LIMIT']} \nYou have exhausted all your Daily Task Limits\n#Daily_task_limit_exceed</b>"
        if config_dict['PAID_SERVICE'] is True: msg += "\n#Buy Paid Service"
        return sendMessage(msg, bot ,message)
    else: ttask = getdailytasks(user_id, increase_task=True); LOGGER.info(f"User : {user_id} Daily Tasks : {ttask}")

    if user_id != OWNER_ID and not is_sudo(user_id) and not is_paid(user_id):
        if config_dict['PAID_SERVICE'] is True:
            if TOTAL_TASKS_LIMIT == total_task:
                return sendMessage(f"<b>Bot Total Task Limit : {TOTAL_TASKS_LIMIT}\nTasks Processing : {total_task}\n#Total_limit_exceed </b>\n#Buy Paid Service", bot ,message)
            if USER_TASKS_LIMIT == get_user_task(user_id):
                return sendMessage(f"<b>Bot Total Task Limit : {USER_TASKS_LIMIT} \nYour Tasks : {get_user_task(user_id)}\n#User_limit_exceed</b>\n#Buy Paid Service", bot ,message)        
        else:
            if TOTAL_TASKS_LIMIT == total_task:
                return sendMessage(f"<b>Bot Total Task Limit : {TOTAL_TASKS_LIMIT}\nTasks Processing : {total_task}\n#total limit exceed </b>", bot ,message)
            if USER_TASKS_LIMIT == get_user_task(user_id):
                return sendMessage(f"<b>Bot Total Task Limit : {USER_TASKS_LIMIT} \nYour Tasks : {get_user_task(user_id)}\n#user limit exceed</b>", bot ,message)
        time_gap = timegap_check(message)
        if time_gap:
            return
        TIME_GAP_STORE[message.from_user.id] = time()

    mesg = message.text.split('\n')
    message_args = mesg[0].split(maxsplit=1)

    index = 1
    ratio = None
    seed_time = None
    select = False
    seed = False
    multi = 0
    link = ''
    c_index = 0
    u_index = None
    CATUSR = getUserTDs(user_id)[0] 
    if len(CATUSR) >= 1: u_index = 0
    shwbtns = True
    timeout = 60

    if len(message_args) > 1:
        args = mesg[0].split(maxsplit=4)
        for x in args:
            x = x.strip()
            if x in ['|', 'pswd:']:
                break
            elif x == 's':
               select = True
               index += 1
            elif x == 'd':
                seed = True
                index += 1
            elif x.startswith('d:'):
                seed = True
                index += 1
                dargs = x.split(':')
                ratio = dargs[1] if dargs[1] else None
                if len(dargs) == 3:
                    seed_time = dargs[2] if dargs[2] else None
            elif x.startswith('c:'):
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
        if multi == 0:
            message_args = mesg[0].split(maxsplit=index)
            if len(message_args) > index:
                link = message_args[index].strip()
                if link.startswith(("|", "pswd:")):
                    link = ''
    name = mesg[0].split('|', maxsplit=1)
    if len(name) > 1:
        if 'pswd:' in name[0]:
            name = ''
        else:
            name = name[1].split('pswd:')[0].strip()
    else:
        name = ''

    pswd = mesg[0].split(' pswd: ')
    pswd = pswd[1] if len(pswd) > 1 else None

    if message.from_user.username:
        tag = f"@{message.from_user.username}"
    else:
        tag = message.from_user.mention_html(message.from_user.first_name)

    if link != '':
        link = re_split(r"pswd:|\|", link)[0]
        link = link.strip()

    catlistener = [bot, message, isZip, extract, isQbit, isLeech, pswd, tag, select, seed]
    extras = [link, name, ratio, seed_time, c_index, u_index, time()]

    reply_to = message.reply_to_message
    if reply_to is not None:
        file_ = reply_to.document or reply_to.video or reply_to.audio or reply_to.photo or None
        if not reply_to.from_user.is_bot:
            if reply_to.from_user.username:
                tag = f"@{reply_to.from_user.username}"
            else:
                tag = reply_to.from_user.mention_html(reply_to.from_user.first_name)
        if len(link) == 0 or not is_url(link) and not is_magnet(link):
            if file_ is None:
                reply_text = reply_to.text.split(maxsplit=1)[0].strip()
                if is_url(reply_text) or is_magnet(reply_text):
                    link = reply_to.text.strip()
            elif isinstance(file_, list):
                link = file_[-1].get_file().file_path
            elif not isQbit and file_.mime_type != "application/x-bittorrent":
                extras[0] = 'tg_file'
                if ((len(CATEGORY_NAMES) > 1 and len(CATUSR) == 0) or (len(CATEGORY_NAMES) >= 1 and len(CATUSR) > 1)) and not isLeech and shwbtns:
                    btn_listener[msg_id] = [catlistener, extras, timeout]
                    text, btns = get_category_buttons('mir', timeout, msg_id, c_index, u_index, user_id)
                    engine = sendMessage(text, bot, message, btns)
                    _auto_start_dl(engine, msg_id, timeout)
                else: start_ml(extras, catlistener)
                if multi > 1:
                    sleep(4)
                    nextmsg = type('nextmsg', (object, ), {'chat_id': message.chat_id, 'message_id': message.reply_to_message.message_id + 1})
                    msg = message.text.split(maxsplit=mi+1)
                    msg[mi] = f"{multi - 1}"
                    nextmsg = sendMessage(" ".join(msg), bot, nextmsg)
                    nextmsg.from_user.id = message.from_user.id
                    sleep(4)
                    Thread(target=_mirror_leech, args=(bot, nextmsg, isZip, extract, isQbit, isLeech)).start()
                return
            else:
                link = file_.get_file().file_path

    if not is_url(link) and not is_magnet(link):
        help_msg = "<b>Send link along with command line:</b>"
        if isQbit:
            help_msg += "\n<code>/qbcmd</code> {link} pswd: xx [zip/unzip]"
            help_msg += "\n\n<b>By replying to link/file:</b>"
            help_msg += "\n<code>/qbcmd</code> pswd: xx [zip/unzip]"
            help_msg += "\n\n<b>Category selection:</b>"
            help_msg += "\n<code>/cmd</code> c:{cat_name} {link} or by replying to {file/link} where cat_name is Specified Drive name (same as specified but not case sensitive)"
            help_msg += "\n\n<b>Bittorrent selection:</b>"
            help_msg += "\n<code>/cmd</code> <b>s</b> {link} or by replying to {file/link}"
            help_msg += "\n\n<b>Qbittorrent seed</b>:"
            help_msg += "\n<code>/qbcmd</code> <b>d</b> {link} or by replying to {file/link}.\n"
            help_msg += "To specify ratio and seed time. Ex: d:0.7:10 (ratio and time) or d:0.7 "
            help_msg += "(only ratio) or d::10 (only time) where time in minutes"
            help_msg += "\n\n<b>Multi links only by replying to first link/file:</b>" 
            help_msg += "\n<code>/command</code> 10(number of links/files)"
        else:
            help_msg += "\n<code>/cmd</code> {link} |newname pswd: xx [zip/unzip]"
            help_msg += "\n\n<b>By replying to link/file:</b>"
            help_msg += "\n<code>/cmd</code> |newname pswd: xx [zip/unzip]"
            help_msg += "\n\n<b>Direct link authorization:</b>"
            help_msg += "\n<code>/cmd</code> {link} |newname pswd: xx\nusername\npassword"
            help_msg += "\n\n<b>Category selection:</b>"
            help_msg += "\n<code>/cmd</code> c:{cat_name} {link} or by replying to {file/link} where cat_name is Specified Drive name (same as specified but not case sensitive)"
            help_msg += "\n\n<b>Bittorrent selection:</b>"
            help_msg += "\n<code>/cmd</code> <b>s</b> {link} or by replying to {file/link}"
            help_msg += "\n\n<b>Bittorrent seed</b>:"
            help_msg += "\n<code>/cmd</code> <b>d</b> {link} or by replying to {file/link}.\n"
            help_msg += "To specify ratio and seed time. Ex: d:0.7:10 (ratio and time) or d:0.7 "
            help_msg += "(only ratio) or d::10 (only time) where time in minutes"
            help_msg += "\n\n<b>Multi links only by replying to first link/file:</b>"
            help_msg += "\n<code>/command</code> 10(number of links/files)"
        reply_message = sendMessage(help_msg, bot, message)
        Thread(target=auto_delete_message, args=(bot, message, reply_message)).start()
        return reply_message

    LOGGER.info(f"Link: {link}")
    LOGGER.info(shwbtns)
    if ((len(CATEGORY_NAMES) > 1 and len(CATUSR) == 0) or (len(CATEGORY_NAMES) >= 1 and len(CATUSR) > 1)) and not isLeech and shwbtns:
        btn_listener[msg_id] = [catlistener, extras, timeout]
        text, btns = get_category_buttons('mir', timeout, msg_id, c_index, u_index, user_id)
        engine = sendMessage(text, bot, message, btns)
        _auto_start_dl(engine, msg_id, timeout)
    else: start_ml(extras, catlistener)

    if multi > 1:
        sleep(4)
        nextmsg = type('nextmsg', (object, ), {'chat_id': message.chat_id, 'message_id': message.reply_to_message.message_id + 1})
        msg = message.text.split(maxsplit=mi+1)
        msg[mi] = f"{multi - 1}"
        nextmsg = sendMessage(" ".join(msg), bot, nextmsg)
        nextmsg.from_user.id = message.from_user.id
        multi -= 1
        sleep(4)
        Thread(target=_mirror_leech, args=(bot, nextmsg, isZip, extract, isQbit, isLeech)).start()

@new_thread
def _auto_start_dl(msg, msg_id, time_out):
    sleep(time_out)
    try:
        info = btn_listener[msg_id]
        del btn_listener[msg_id]
        editMessage("Timed out! Task has been Started.", msg)
        start_ml(info[1], info[0])
    except:
        pass

def start_ml(extra, s_listener):
    is_gdtot = False
    is_unified = False
    is_udrive = False
    is_sharer = False
    is_sharedrive = False
    is_filepress = False
    bot = s_listener[0]
    message = s_listener[1]
    isZip = s_listener[2]
    extract = s_listener[3]
    isQbit = s_listener[4]
    isLeech = s_listener[5]
    pswd = s_listener[6]
    tag = s_listener[7]
    select = s_listener[8]
    seed = s_listener[9]
    link = extra[0]
    name = extra[1]
    ratio = extra[2]
    seed_time = extra[3]
    c_index = int(extra[4])
    u_index = extra[5]

    listener = MirrorLeechListener(bot, message, isZip, extract, isQbit, isLeech, pswd, tag, select, seed, c_index, u_index)
    if link == 'tg_file':
        Thread(target=TelegramDownloadHelper(listener).add_download, args=(message, f'{DOWNLOAD_DIR}{listener.uid}/', name)).start()
        return
    if not is_mega_link(link) and not isQbit and not is_magnet(link) \
        and not is_gdrive_link(link) and not link.endswith('.torrent'):
        content_type = get_content_type(link)
        if content_type is None or re_match(r'text/html|text/plain', content_type):
            try:
                is_gdtot = is_gdtot_link(link)
                is_unified = is_unified_link(link)
                is_udrive = is_udrive_link(link)
                is_sharer = is_sharer_link(link)
                is_sharedrive = is_sharedrive_link(link)
                is_filepress = is_filepress_link(link)
                link = direct_link_generator(link)
                LOGGER.info(f"Generated link: {link}")
            except DirectDownloadLinkException as e:
                LOGGER.info(str(e))
                if str(e).startswith('ERROR:'):
                    return sendMessage(str(e), bot, message)
    elif isQbit and not is_magnet(link):
        if link.endswith('.torrent') or "https://api.telegram.org/file/" in link:
            content_type = None
        else:
            content_type = get_content_type(link)
        if content_type is None or re_match(r'application/x-bittorrent|application/octet-stream', content_type):
            try:
                resp = rget(link, timeout=10, headers = {'user-agent': 'Wget/1.12'})
                if resp.status_code == 200:
                    file_name = str(time()).replace(".", "") + ".torrent"
                    with open(file_name, "wb") as t:
                        t.write(resp.content)
                    link = str(file_name)
                else:
                    return sendMessage(f"{tag} ERROR: link got HTTP response: {resp.status_code}", bot, message)
            except Exception as e:
                error = str(e).replace('<', ' ').replace('>', ' ')
                if error.startswith('No connection adapters were found for'):
                    link = error.split("'")[1]
                else:
                    LOGGER.error(str(e))
                    return sendMessage(tag + " " + error, bot, message)
        else:
            msg = "Qb commands for torrents only. if you are trying to dowload torrent then report."
            return sendMessage(msg, bot, message)

    if is_gdrive_link(link):
        if not isZip and not extract and not isLeech:
            gmsg = f"Use /{BotCommands.CloneCommand[0]} to clone Google Drive file/folder\n\n"
            gmsg += f"Use /{BotCommands.ZipMirrorCommand[0]} to make zip of Google Drive folder\n\n"
            gmsg += f"Use /{BotCommands.UnzipMirrorCommand[0]} to extracts Google Drive archive file"
            sendMessage(gmsg, bot, message)
        else:
            Thread(target=add_gd_download, args=(link, f'{DOWNLOAD_DIR}{listener.uid}', listener, name, is_gdtot, is_unified, is_udrive, is_sharer, is_sharedrive, is_filepress)).start()
    elif is_mega_link(link):
        Thread(target=add_mega_download, args=(link, f'{DOWNLOAD_DIR}{listener.uid}/', listener, name)).start()
    elif isQbit and (is_magnet(link) or ospath.exists(link)):
        Thread(target=add_qb_torrent, args=(link, f'{DOWNLOAD_DIR}{listener.uid}', listener,
                                            ratio, seed_time)).start()
    else:
        mesg = message.text.split('\n')
        if len(mesg) > 1:
            ussr = mesg[1]
            if len(mesg) > 2:
                pssw = mesg[2]
            else:
                pssw = ''
            auth = f"{ussr}:{pssw}"
            auth = "Basic " + b64encode(auth.encode()).decode('ascii')
        else:
            auth = ''
        Thread(target=add_aria2c_download, args=(link, f'{DOWNLOAD_DIR}{listener.uid}', listener, name, auth, ratio, seed_time)).start()

@new_thread
def mir_confirm(update, context):
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
    listener = listenerInfo[0]
    extra = listenerInfo[1]
    if user_id != listener[1].from_user.id and not CustomFilters.owner_query(user_id):
        return query.answer("You are not the owner of this download!", show_alert=True)
    elif data[1] == 'scat':
        c_index = int(data[3])
        u_index = None
        if extra[4] == c_index:
            return query.answer(f"{CATEGORY_NAMES[c_index]} is already selected!", show_alert=True)
        query.answer()
        extra[4] = c_index
        extra[5] = u_index
    elif data[1] == 'ucat':
        u_index = int(data[3])
        c_index = 0
        if extra[5] == u_index:
            return query.answer(f"{getUserTDs(listener[1].from_user.id)[0][u_index]} is already selected!", show_alert=True)
        query.answer()
        extra[4] = c_index
        extra[5] = u_index
    elif data[1] == 'cancel':
        query.answer()
        del btn_listener[msg_id]
        return editMessage(f"<b>Download has been cancelled!</b>", message)
    elif data[1] == 'start':
        query.answer()
        message.delete()
        del btn_listener[msg_id]
        return start_ml(extra, listener)
    timeout = listenerInfo[2] - (time() - extra[6])
    text, btns = get_category_buttons('mir', timeout, msg_id, extra[4], extra[5], listener[1].from_user.id)
    editMessage(text, message, btns)

def mirror(update, context):
    _mirror_leech(context.bot, update.message)

def unzip_mirror(update, context):
    _mirror_leech(context.bot, update.message, extract=True)

def zip_mirror(update, context):
    _mirror_leech(context.bot, update.message, True)

def qb_mirror(update, context):
    _mirror_leech(context.bot, update.message, isQbit=True)

def qb_unzip_mirror(update, context):
    _mirror_leech(context.bot, update.message, extract=True, isQbit=True)

def qb_zip_mirror(update, context):
    _mirror_leech(context.bot, update.message, True, isQbit=True)

def leech(update, context):
    _mirror_leech(context.bot, update.message, isLeech=True)

def unzip_leech(update, context):
    _mirror_leech(context.bot, update.message, extract=True, isLeech=True)

def zip_leech(update, context):
    _mirror_leech(context.bot, update.message, True, isLeech=True)

def qb_leech(update, context):
    _mirror_leech(context.bot, update.message, isQbit=True, isLeech=True)

def qb_unzip_leech(update, context):
    _mirror_leech(context.bot, update.message, extract=True, isQbit=True, isLeech=True)

def qb_zip_leech(update, context):
    _mirror_leech(context.bot, update.message, True, isQbit=True, isLeech=True)

authfilter = CustomFilters.authorized_chat if config_dict['MIRROR_ENABLED'] is True else CustomFilters.owner_filter
mirror_handler = CommandHandler(BotCommands.MirrorCommand, mirror,
                                    filters=authfilter | CustomFilters.authorized_user)
unzip_mirror_handler = CommandHandler(BotCommands.UnzipMirrorCommand, unzip_mirror,
                                    filters=authfilter | CustomFilters.authorized_user)
zip_mirror_handler = CommandHandler(BotCommands.ZipMirrorCommand, zip_mirror,
                                    filters=authfilter | CustomFilters.authorized_user)

authfilter = CustomFilters.authorized_chat if config_dict['QB_MIRROR_ENABLED'] is True else CustomFilters.owner_filter
qb_mirror_handler = CommandHandler(BotCommands.QbMirrorCommand, qb_mirror,
                                    filters=authfilter | CustomFilters.authorized_user)
qb_unzip_mirror_handler = CommandHandler(BotCommands.QbUnzipMirrorCommand, qb_unzip_mirror,
                                    filters=authfilter | CustomFilters.authorized_user)
qb_zip_mirror_handler = CommandHandler(BotCommands.QbZipMirrorCommand, qb_zip_mirror,
                                    filters=authfilter | CustomFilters.authorized_user)

authfilter = CustomFilters.authorized_chat if config_dict['LEECH_ENABLED'] is True else CustomFilters.owner_filter
leech_handler = CommandHandler(BotCommands.LeechCommand, leech,
                                    filters=authfilter | CustomFilters.authorized_user)
unzip_leech_handler = CommandHandler(BotCommands.UnzipLeechCommand, unzip_leech,
                                    filters=authfilter | CustomFilters.authorized_user)
zip_leech_handler = CommandHandler(BotCommands.ZipLeechCommand, zip_leech,
                                    filters=authfilter | CustomFilters.authorized_user)
qb_leech_handler = CommandHandler(BotCommands.QbLeechCommand, qb_leech,
                                    filters=authfilter | CustomFilters.authorized_user)
qb_unzip_leech_handler = CommandHandler(BotCommands.QbUnzipLeechCommand, qb_unzip_leech,
                                    filters=authfilter | CustomFilters.authorized_user)
qb_zip_leech_handler = CommandHandler(BotCommands.QbZipLeechCommand, qb_zip_leech,
                                    filters=authfilter | CustomFilters.authorized_user)
mir_handler = CallbackQueryHandler(mir_confirm, pattern="mir")

dispatcher.add_handler(mirror_handler)
dispatcher.add_handler(unzip_mirror_handler)
dispatcher.add_handler(zip_mirror_handler)
dispatcher.add_handler(qb_mirror_handler)
dispatcher.add_handler(qb_unzip_mirror_handler)
dispatcher.add_handler(qb_zip_mirror_handler)
dispatcher.add_handler(leech_handler)
dispatcher.add_handler(unzip_leech_handler)
dispatcher.add_handler(zip_leech_handler)
dispatcher.add_handler(qb_leech_handler)
dispatcher.add_handler(qb_unzip_leech_handler)
dispatcher.add_handler(qb_zip_leech_handler)
dispatcher.add_handler(mir_handler)
