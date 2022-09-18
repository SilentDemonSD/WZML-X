from base64 import b64encode
from pyrogram import enums
from re import match as re_match, search as re_search, split as re_split
from time import sleep, time
from os import path as ospath, remove as osremove, listdir, walk
from shutil import rmtree
from threading import Thread
from subprocess import run as srun
from pathlib import PurePath
from telegram.ext import CommandHandler
from telegram import ParseMode, InlineKeyboardButton

from bot import *
from bot.helper.ext_utils.bot_utils import is_url, is_magnet, is_gdtot_link, is_mega_link, is_gdrive_link, is_unified_link, is_udrive_link, get_content_type, get_readable_time, get_user_task
from bot.helper.ext_utils.exceptions import DirectDownloadLinkException, NotSupportedExtractionArchive
from bot.helper.ext_utils.shortenurl import short_url
from bot.helper.mirror_utils.download_utils.aria2_download import add_aria2c_download
from bot.helper.mirror_utils.download_utils.gd_downloader import add_gd_download
from bot.helper.mirror_utils.download_utils.qbit_downloader import QbDownloader
from bot.helper.mirror_utils.download_utils.mega_downloader import MegaDownloader
from bot.helper.mirror_utils.download_utils.direct_link_generator import direct_link_generator
from bot.helper.mirror_utils.download_utils.telegram_downloader import TelegramDownloadHelper
from bot.helper.telegram_helper.bot_commands import BotCommands
from bot.helper.telegram_helper.filters import CustomFilters
from bot.helper.telegram_helper.message_utils import sendMessage, sendMarkup, delete_all_messages, update_all_messages, auto_delete_upload_message, auto_delete_message
from bot.helper.ext_utils.telegraph_helper import telegraph
from bot.helper.telegram_helper.button_build import ButtonMaker
from .listener import MirrorLeechListener


def _mirror_leech(bot, message, isZip=False, extract=False, isQbit=False, isLeech=False):
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
            reply_message = sendMarkup(startwarn, bot, message, buttons.build_menu(2))
            Thread(target=auto_delete_message, args=(bot, message, reply_message)).start()
            return reply_message

    total_task = len(download_dict)
    user_id = message.from_user.id
    if user_id != OWNER_ID and user_id not in SUDO_USERS:
            if TOTAL_TASKS_LIMIT == total_task:
                return sendMessage(f"<b>Bot Total Task Limit : {TOTAL_TASKS_LIMIT}\nTasks Processing : {total_task}\n#total limit exceed </b>", bot ,message)
            if USER_TASKS_LIMIT == get_user_task(user_id):
                return sendMessage(f"<b>Bot Total Task Limit : {USER_TASKS_LIMIT} \nYour Tasks : {get_user_task(user_id)}\n#user limit exceed</b>", bot ,message)

    mesg = message.text.split('\n')
    message_args = mesg[0].split(maxsplit=1)
    name_args = mesg[0].split('|', maxsplit=1)
    is_gdtot = False
    is_unified = False
    is_udrive = False
    index = 1
    ratio = None
    seed_time = None
    select = False
    seed = False
    multi = 0

    if len(message_args) > 1:
        args = mesg[0].split(maxsplit=3)
        for x in args:
            x = x.strip()
            if x == 's':
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
            elif x.isdigit():
                multi = int(x)
                mi = index
        if multi == 0:
            message_args = mesg[0].split(maxsplit=index)
            if len(message_args) > index:
                link = message_args[index].strip()
                if link.startswith(("|", "pswd:")):
                    link = ''
            else:
                link = ''
        else:
            link = ''
    else:
        link = ''

    if len(name_args) > 1:
        name = name_args[1]
        name = name.split(' pswd:')[0]
        name = name.strip()
    else:
        name = ''

    link = re_split(r"pswd:|\|", link)[0]
    link = link.strip()

    pswd_arg = mesg[0].split(' pswd: ')
    if len(pswd_arg) > 1:
        pswd = pswd_arg[1]
    else:
        pswd = None

    if message.from_user.username:
        tag = f"@{message.from_user.username}"
    else:
        tag = message.from_user.mention_html(message.from_user.first_name)

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
                listener = MirrorLeechListener(bot, message, isZip, extract, isQbit, isLeech, pswd, tag)
                Thread(target=TelegramDownloadHelper(listener).add_download, args=(message, f'{DOWNLOAD_DIR}{listener.uid}/', name)).start()
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

    LOGGER.info(link)

    if not is_mega_link(link) and not isQbit and not is_magnet(link) \
        and not is_gdrive_link(link) and not link.endswith('.torrent'):
        content_type = get_content_type(link)
        if content_type is None or re_match(r'text/html|text/plain', content_type):
            try:
                is_gdtot = is_gdtot_link(link)
                is_unified = is_unified_link(link)
                is_udrive = is_udrive_link(link)
                link = direct_link_generator(link)
                LOGGER.info(f"Generated link: {link}")
            except DirectDownloadLinkException as e:
                LOGGER.info(str(e))
                if str(e).startswith('ERROR:'):
                    return sendMessage(str(e), bot, message)

    listener = MirrorLeechListener(bot, message, isZip, extract, isQbit, isLeech, pswd, tag, select, seed)

    if is_gdrive_link(link):
        if not isZip and not extract and not isLeech:
            gmsg = f"Use /{BotCommands.CloneCommand} to clone Google Drive file/folder\n\n"
            gmsg += f"Use /{BotCommands.ZipMirrorCommand} to make zip of Google Drive folder\n\n"
            gmsg += f"Use /{BotCommands.UnzipMirrorCommand} to extracts Google Drive archive file"
            sendMessage(gmsg, bot, message)
        else:
            Thread(target=add_gd_download, args=(link, f'{DOWNLOAD_DIR}{listener.uid}', listener, is_gdtot, is_unified, is_udrive, name)).start()
    elif is_mega_link(link):
        if MEGA_KEY is not None:
            Thread(target=MegaDownloader(listener).add_download, args=(link, f'{DOWNLOAD_DIR}{listener.uid}/')).start()
        else:
            sendMessage('MEGA_API_KEY not Provided!', bot, message)
    elif isQbit:
        Thread(target=QbDownloader(listener).add_qb_torrent, args=(link, f'{DOWNLOAD_DIR}{listener.uid}',
                                                                   ratio, seed_time)).start()
    else:
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
        Thread(target=add_aria2c_download, args=(link, f'{DOWNLOAD_DIR}{listener.uid}', listener, name,
		                                         auth, ratio, seed_time)).start()

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

if MIRROR_ENABLED:

    mirror_handler = CommandHandler(BotCommands.MirrorCommand, mirror,
                                    filters=CustomFilters.authorized_chat | CustomFilters.authorized_user, run_async=True)
    unzip_mirror_handler = CommandHandler(BotCommands.UnzipMirrorCommand, unzip_mirror,
                                    filters=CustomFilters.authorized_chat | CustomFilters.authorized_user, run_async=True)
    zip_mirror_handler = CommandHandler(BotCommands.ZipMirrorCommand, zip_mirror,
                                    filters=CustomFilters.authorized_chat | CustomFilters.authorized_user, run_async=True)
    qb_mirror_handler = CommandHandler(BotCommands.QbMirrorCommand, qb_mirror,
                                    filters=CustomFilters.authorized_chat | CustomFilters.authorized_user, run_async=True)
    qb_unzip_mirror_handler = CommandHandler(BotCommands.QbUnzipMirrorCommand, qb_unzip_mirror,
                                    filters=CustomFilters.authorized_chat | CustomFilters.authorized_user, run_async=True)
    qb_zip_mirror_handler = CommandHandler(BotCommands.QbZipMirrorCommand, qb_zip_mirror,
                                    filters=CustomFilters.authorized_chat | CustomFilters.authorized_user, run_async=True)

else:
    mirror_handler = CommandHandler(BotCommands.MirrorCommand, mirror,
                                    filters=CustomFilters.owner_filter | CustomFilters.authorized_user, run_async=True)
    unzip_mirror_handler = CommandHandler(BotCommands.UnzipMirrorCommand, unzip_mirror,
                                    filters=CustomFilters.owner_filter | CustomFilters.authorized_user, run_async=True)
    zip_mirror_handler = CommandHandler(BotCommands.ZipMirrorCommand, zip_mirror,
                                    filters=CustomFilters.owner_filter | CustomFilters.authorized_user, run_async=True)
    qb_mirror_handler = CommandHandler(BotCommands.QbMirrorCommand, qb_mirror,
                                    filters=CustomFilters.owner_filter | CustomFilters.authorized_user, run_async=True)
    qb_unzip_mirror_handler = CommandHandler(BotCommands.QbUnzipMirrorCommand, qb_unzip_mirror,
                                    filters=CustomFilters.owner_filter | CustomFilters.authorized_user, run_async=True)
    qb_zip_mirror_handler = CommandHandler(BotCommands.QbZipMirrorCommand, qb_zip_mirror,
                                    filters=CustomFilters.owner_filter | CustomFilters.authorized_user, run_async=True)

if LEECH_ENABLED:
    leech_handler = CommandHandler(BotCommands.LeechCommand, leech,
                                    filters=CustomFilters.authorized_chat | CustomFilters.authorized_user, run_async=True)
    unzip_leech_handler = CommandHandler(BotCommands.UnzipLeechCommand, unzip_leech,
                                    filters=CustomFilters.authorized_chat | CustomFilters.authorized_user, run_async=True)
    zip_leech_handler = CommandHandler(BotCommands.ZipLeechCommand, zip_leech,
                                    filters=CustomFilters.authorized_chat | CustomFilters.authorized_user, run_async=True)
    qb_leech_handler = CommandHandler(BotCommands.QbLeechCommand, qb_leech,
                                    filters=CustomFilters.authorized_chat | CustomFilters.authorized_user, run_async=True)
    qb_unzip_leech_handler = CommandHandler(BotCommands.QbUnzipLeechCommand, qb_unzip_leech,
                                    filters=CustomFilters.authorized_chat | CustomFilters.authorized_user, run_async=True)
    qb_zip_leech_handler = CommandHandler(BotCommands.QbZipLeechCommand, qb_zip_leech,
                                    filters=CustomFilters.authorized_chat | CustomFilters.authorized_user, run_async=True)

else:
    leech_handler = CommandHandler(BotCommands.LeechCommand, leech,
                                    filters=CustomFilters.owner_filter | CustomFilters.authorized_user, run_async=True)
    unzip_leech_handler = CommandHandler(BotCommands.UnzipLeechCommand, unzip_leech,
                                    filters=CustomFilters.owner_filter | CustomFilters.authorized_user, run_async=True)
    zip_leech_handler = CommandHandler(BotCommands.ZipLeechCommand, zip_leech,
                                    filters=CustomFilters.owner_filter | CustomFilters.authorized_user, run_async=True)
    qb_leech_handler = CommandHandler(BotCommands.QbLeechCommand, qb_leech,
                                    filters=CustomFilters.owner_filter | CustomFilters.authorized_user, run_async=True)
    qb_unzip_leech_handler = CommandHandler(BotCommands.QbUnzipLeechCommand, qb_unzip_leech,
                                    filters=CustomFilters.owner_filter | CustomFilters.authorized_user, run_async=True)
    qb_zip_leech_handler = CommandHandler(BotCommands.QbZipLeechCommand, qb_zip_leech,
                                    filters=CustomFilters.owner_filter | CustomFilters.authorized_user, run_async=True)

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