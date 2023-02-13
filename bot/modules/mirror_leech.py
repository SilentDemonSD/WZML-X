from base64 import b64encode
from requests import get as rget
from re import match as re_match, split as re_split
from time import time
from os import path as ospath

from asyncio import sleep as asleep
from pyrogram import filters, Client
from pyrogram.types import Message, CallbackQuery
from pyrogram.enums import ChatType

from bot.helper.ext_utils.bot_utils import get_bot_pm, is_paid, is_sudo, getdailytasks, get_user_task, getUserTDs, is_url, \
    is_magnet, get_category_buttons, is_mega_link, is_gdrive_link, get_content_type, is_gdtot_link, \
    is_udrive_link, is_sharer_link, is_sharedrive_link, is_filepress_link, is_unified_link
from bot.helper.ext_utils.exceptions import DirectDownloadLinkException
from bot.helper.ext_utils.timegap import timegap_check
from bot.helper.mirror_utils.download_utils.aria2_download import add_aria2c_download
from bot.helper.mirror_utils.download_utils.gd_downloader import add_gd_download
from bot.helper.mirror_utils.download_utils.qbit_downloader import add_qb_torrent
from bot.helper.mirror_utils.download_utils.mega_downloader import add_mega_download
from bot.helper.mirror_utils.download_utils.direct_link_generator import direct_link_generator
from bot.helper.mirror_utils.download_utils.telegram_downloader import TelegramDownloadHelper
from bot.helper.telegram_helper.bot_commands import BotCommands
from bot.helper.telegram_helper.filters import CustomFilters
from bot.helper.telegram_helper.message_utils import sendMessage, editMessage, forcesub, auto_delete_message, isAdmin
from bot.helper.telegram_helper.button_build import ButtonMaker
from bot import LOGGER, download_dict, config_dict, OWNER_ID, TIME_GAP_STORE, CATEGORY_NAMES, btn_listener, DOWNLOAD_DIR, bot, main_loop
from .listener import MirrorLeechListener


async def _mirror_leech(c: Client, message: Message, isZip=False, extract=False, isQbit=False, isLeech=False):
    buttons = ButtonMaker()
    user_id = message.from_user.id
    msg_id = message.id
    BOT_PM_X = get_bot_pm(user_id)
    if not await isAdmin(message):
        if message.from_user.username:
            tag = f"@{message.from_user.username}"
        else:
            tag = message.from_user.mention(message.from_user.first_name, style='html')
        if await forcesub(c, message, tag):
            return
    if BOT_PM_X and message.chat.type == message.chat.type.SUPERGROUP:
        PM = await sendMessage("Added your Requested link to Download\n", c, message, chat_id=user_id)
        if PM:
            await PM.delete()
            PM = True
        else:
            return
    else:
        PM = None

    if message.chat.type != ChatType.PRIVATE and user_id != OWNER_ID and not is_sudo(user_id):
        if not config_dict['MIRROR_ENABLED'] and not isLeech and not isQbit:
            reply_message = await sendMessage('Mirror is Disabled', c, message)
            return reply_message
        elif not config_dict['LEECH_ENABLED'] and isLeech and not isQbit:
            reply_message = await sendMessage('LEECH is Disabled', c, message)
            return reply_message
        elif not config_dict['QB_MIRROR_ENABLED'] and isQbit and not isLeech:
            reply_message = await sendMessage('QbMirror is Disabled', c, message)
            return reply_message
        elif not config_dict['QB_LEECH_ENABLED'] and isQbit and isLeech:
            reply_message = await sendMessage('QbLeech is Disabled', c, message)
            return reply_message

    total_task = len(download_dict)
    USER_TASKS_LIMIT = config_dict['USER_TASKS_LIMIT']
    TOTAL_TASKS_LIMIT = config_dict['TOTAL_TASKS_LIMIT']
    if config_dict['DAILY_TASK_LIMIT'] and user_id != OWNER_ID and not is_sudo(user_id) and not is_paid(user_id) and config_dict['DAILY_TASK_LIMIT'] <= getdailytasks(user_id):
        msg = f"<b>Daily Total Task Limit : {config_dict['DAILY_TASK_LIMIT']} \nYou have exhausted all your Daily Task Limits\n#Daily_task_limit_exceed</b>"
        if config_dict['PAID_SERVICE'] is True:
            msg += "\n#Buy Paid Service"
        return await sendMessage(msg, c, message)
    else:
        ttask = getdailytasks(user_id, increase_task=True)
        LOGGER.info(f"User : {user_id} Daily Tasks : {ttask}")

    if user_id != OWNER_ID and not is_sudo(user_id) and not is_paid(user_id):
        if config_dict['PAID_SERVICE'] is True:
            if TOTAL_TASKS_LIMIT == total_task:
                return await sendMessage(f"<b>Bot Total Task Limit : {TOTAL_TASKS_LIMIT}\nTasks Processing : {total_task}\n#Total_limit_exceed </b>\n#Buy Paid Service", c, message)
            if USER_TASKS_LIMIT == get_user_task(user_id):
                return await sendMessage(f"<b>Bot Total Task Limit : {USER_TASKS_LIMIT} \nYour Tasks : {get_user_task(user_id)}\n#User_limit_exceed</b>\n#Buy Paid Service", c, message)
        else:
            if TOTAL_TASKS_LIMIT == total_task:
                return await sendMessage(f"<b>Bot Total Task Limit : {TOTAL_TASKS_LIMIT}\nTasks Processing : {total_task}\n#total limit exceed </b>", c, message)
            if USER_TASKS_LIMIT == get_user_task(user_id):
                return await sendMessage(f"<b>Bot Total Task Limit : {USER_TASKS_LIMIT} \nYour Tasks : {get_user_task(user_id)}\n#user limit exceed</b>", c, message)
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
    if len(CATUSR) >= 1:
        u_index = 0
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
        tag = message.from_user.mention(message.from_user.first_name, style='html')

    if link != '':
        link = re_split(r"pswd:|\|", link)[0]
        link = link.strip()

    catlistener = [c, message, isZip, extract,
                   isQbit, isLeech, pswd, tag, select, seed]
    extras = [link, name, ratio, seed_time, c_index, u_index, time()]

    reply_to = message.reply_to_message
    if reply_to is not None:
        file_ = reply_to.document or reply_to.video or reply_to.audio or reply_to.photo or None
        if not reply_to.from_user.is_bot:
            if reply_to.from_user.username:
                tag = f"@{reply_to.from_user.username}"
            else:
                tag = reply_to.from_user.mention(
                    reply_to.from_user.first_name, style='html')
        if len(link) == 0 or not is_url(link) and not is_magnet(link):
            if file_ is None:
                reply_text = reply_to.text.split(maxsplit=1)[0].strip()
                if is_url(reply_text) or is_magnet(reply_text):
                    link = reply_to.text.strip()
            elif isinstance(file_, list):
                link = await c.download_media(file_[-1])
            elif not isQbit and file_.mime_type != "application/x-bittorrent":
                extras[0] = 'tg_file'
                if ((len(CATEGORY_NAMES) > 1 and len(CATUSR) == 0) or (len(CATEGORY_NAMES) >= 1 and len(CATUSR) > 1)) and not isLeech and shwbtns:
                    btn_listener[msg_id] = [catlistener, extras, timeout]
                    text, btns = get_category_buttons(
                        'mir', timeout, msg_id, c_index, u_index, user_id)
                    engine = await sendMessage(text, bot, message, btns)
                    await _auto_start_dl(engine, msg_id, timeout)
                else:
                    await start_ml(extras, catlistener)
                if multi > 1:
                    await asleep(4)
                    nextmsg = type('nextmsg', (object, ), {
                                   'chat_id': message.chat.id, 'message_id': message.reply_to_message.id + 1})
                    msg = message.text.split(maxsplit=mi+1)
                    msg[mi] = f"{multi - 1}"
                    nextmsg = await sendMessage(" ".join(msg), c, nextmsg)
                    nextmsg.from_user.id = message.from_user.id
                    await asleep(4)
                    await _mirror_leech(c, nextmsg, isZip, extract, isQbit, isLeech)
                return
            else:
                link = await c.download_media(file_)
                

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
        reply_message = await sendMessage(help_msg, c, message)
        main_loop.create_task(auto_delete_message(c, message, reply_message))
        return reply_message

    LOGGER.info(f"Link: {link}")
    extras[0] = link
    if ((len(CATEGORY_NAMES) > 1 and len(CATUSR) == 0) or (len(CATEGORY_NAMES) >= 1 and len(CATUSR) > 1)) and not isLeech and shwbtns:
        btn_listener[msg_id] = [catlistener, extras, timeout]
        text, btns = get_category_buttons(
            'mir', timeout, msg_id, c_index, u_index, user_id)
        engine = await sendMessage(text, c, message, btns)
        await main_loop.create_task(_auto_start_dl(engine, msg_id, timeout))
    else:
        await main_loop.create_task(start_ml(extras, catlistener))

    if multi > 1:
        await asleep(4)
        nextmsg = type('nextmsg', (object, ), {
                       'chat_id': message.chat.id, 'message_id': message.reply_to_message.id + 1})
        msg = message.text.split(maxsplit=mi+1)
        msg[mi] = f"{multi - 1}"
        nextmsg = await sendMessage(" ".join(msg), c, nextmsg)
        nextmsg.from_user.id = message.from_user.id
        multi -= 1
        await asleep(4)
        await main_loop.create_task(_mirror_leech(c, nextmsg, isZip, extract, isQbit, isLeech))


async def _auto_start_dl(msg, msg_id, time_out):
    await asleep(time_out)
    try:
        info = btn_listener[msg_id]
        del btn_listener[msg_id]
        await editMessage("Timed out! Task has been Started.", msg)
        await start_ml(info[1], info[0])
    except:
        pass


async def start_ml(extra, s_listener):
    is_gdtot = False
    is_udrive = False
    is_sharer = False
    is_sharedrive = False
    is_filepress = False
    is_unified = False
    c = s_listener[0]
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

    listener = MirrorLeechListener(
        c, message, isZip, extract, isQbit, isLeech, pswd, tag, select, seed, c_index, u_index)
    if link == 'tg_file':
        await main_loop.create_task(TelegramDownloadHelper(listener).add_download(message, f'{DOWNLOAD_DIR}{listener.uid}/', name))
        return
    if not is_mega_link(link) and not isQbit and not is_magnet(link) \
            and not is_gdrive_link(link) and not link.endswith('.torrent'):
        content_type = get_content_type(link)
        if content_type is None or re_match(r'text/html|text/plain', content_type):
            try:
                is_gdtot = is_gdtot_link(link)
                is_udrive = is_udrive_link(link)
                is_sharer = is_sharer_link(link)
                is_sharedrive = is_sharedrive_link(link)
                is_filepress = is_filepress_link(link)
                is_unified = is_unified_link(link)
                link = await direct_link_generator(link)
                LOGGER.info(f"Generated link: {link}")
            except DirectDownloadLinkException as e:
                LOGGER.info(str(e))
                if str(e).startswith('ERROR:'):
                    return await sendMessage(str(e), c, message)
    elif isQbit and not is_magnet(link) and not ospath.exists(link):
        if link.endswith('.torrent') or "https://api.telegram.org/file/" in link:
            content_type = None
        else:
            content_type = get_content_type(link)
        if content_type is None or re_match(r'application/x-bittorrent|application/octet-stream', content_type):
            try:
                resp = rget(link, timeout=10, headers={
                            'user-agent': 'Wget/1.12'})
                if resp.status_code == 200:
                    file_name = str(time()).replace(".", "") + ".torrent"
                    with open(file_name, "wb") as t:
                        t.write(resp.content)
                    link = str(file_name)
                else:
                    return await sendMessage(f"{tag} ERROR: link got HTTP response: {resp.status_code}", c, message)
            except Exception as e:
                error = str(e).replace('<', ' ').replace('>', ' ')
                if error.startswith('No connection adapters were found for'):
                    link = error.split("'")[1]
                else:
                    LOGGER.error(str(e))
                    return await sendMessage(tag + " " + error, c, message)
        else:
            msg = "Qb commands for torrents only. if you are trying to dowload torrent then report."
            return await sendMessage(msg, c, message)

    if is_gdrive_link(link):
        if not isZip and not extract and not isLeech:
            gmsg = f"Use /{BotCommands.CloneCommand[0]} to clone Google Drive file/folder\n\n"
            gmsg += f"Use /{BotCommands.ZipMirrorCommand[0]} to make zip of Google Drive folder\n\n"
            gmsg += f"Use /{BotCommands.UnzipMirrorCommand[0]} to extracts Google Drive archive file"
            await sendMessage(gmsg, c, message)
        else:
            await main_loop.create_task(add_gd_download(link, f'{DOWNLOAD_DIR}{listener.uid}', listener, name, is_gdtot, is_udrive, is_sharer, is_sharedrive, is_filepress, is_unified))
    elif is_mega_link(link):
        await main_loop.create_task(add_mega_download(link, path=f'{DOWNLOAD_DIR}{listener.uid}/', listener=listener, name=name))
    elif isQbit and (is_magnet(link) or ospath.exists(link)):
        await main_loop.create_task(add_qb_torrent(link, f'{DOWNLOAD_DIR}{listener.uid}', listener, ratio, seed_time))
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

        await main_loop.create_task(add_aria2c_download(link, f'{DOWNLOAD_DIR}{listener.uid}', listener, name, auth, ratio, seed_time))

@bot.on_callback_query(filters.regex(r"^mir"))
async def mir_confirm(c: Client, query: CallbackQuery):
    user_id = query.from_user.id
    message = query.message
    data = query.data
    data = data.split()
    msg_id = int(data[2])
    try:
        listenerInfo = btn_listener[msg_id]
    except KeyError:
        await editMessage(f"<b>Download has been cancelled or already started!</b>", message)
        return
    listener = listenerInfo[0]
    extra = listenerInfo[1]
    if user_id != listener[1].from_user.id and not CustomFilters.owner_query(user_id):
        await query.answer("You are not the owner of this download!", show_alert=True)
        return
    elif data[1] == 'scat':
        c_index = int(data[3])
        u_index = None
        if extra[4] == c_index:
            await query.answer(f"{CATEGORY_NAMES[c_index]} is already selected!", show_alert=True)
            return
        await query.answer()
        extra[4] = c_index
        extra[5] = u_index
    elif data[1] == 'ucat':
        u_index = int(data[3])
        c_index = 0
        if extra[5] == u_index:
            await query.answer(f"{getUserTDs(listener[1].from_user.id)[0][u_index]} is already selected!", show_alert=True)
            return
        await query.answer()
        extra[4] = c_index
        extra[5] = u_index
    elif data[1] == 'cancel':
        await query.answer()
        del btn_listener[msg_id]
        await editMessage(f"<b>Download has been cancelled!</b>", message)
        return
    elif data[1] == 'start':
        await query.answer()
        await message.delete()
        del btn_listener[msg_id]
        return await start_ml(extra, listener)
    timeout = listenerInfo[2] - (time() - extra[6])
    text, btns = get_category_buttons(
        'mir', timeout, msg_id, extra[4], extra[5], listener[1].from_user.id)
    await editMessage(text, message, btns)


@bot.on_message(filters.command(BotCommands.MirrorCommand) & (CustomFilters.authorized_chat | CustomFilters.authorized_user))
async def mirror(client: Client, message: Message):
    await _mirror_leech(client, message)


@bot.on_message(filters.command(BotCommands.UnzipMirrorCommand) & (CustomFilters.authorized_chat | CustomFilters.authorized_user))
async def unzip_mirror(client: Client, message: Message):
    await _mirror_leech(client, message, extract=True)


@bot.on_message(filters.command(BotCommands.ZipMirrorCommand) & (CustomFilters.authorized_chat | CustomFilters.authorized_user))
async def zip_mirror(client: Client, message: Message):
    await _mirror_leech(client, message, True)


@bot.on_message(filters.command(BotCommands.QbMirrorCommand) & (CustomFilters.authorized_chat | CustomFilters.authorized_user))
async def qb_mirror(client: Client, message: Message):
    await _mirror_leech(client, message, isQbit=True)


@bot.on_message(filters.command(BotCommands.QbUnzipMirrorCommand) & (CustomFilters.authorized_chat | CustomFilters.authorized_user))
async def qb_unzip_mirror(client: Client, message: Message):
    await _mirror_leech(client, message, extract=True, isQbit=True)


@bot.on_message(filters.command(BotCommands.QbZipMirrorCommand) & (CustomFilters.authorized_chat | CustomFilters.authorized_user))
async def qb_zip_mirror(client: Client, message: Message):
    await _mirror_leech(client, message, True, isQbit=True)


@bot.on_message(filters.command(BotCommands.LeechCommand) & (CustomFilters.authorized_chat | CustomFilters.authorized_user))
async def leech(client: Client, message: Message):
    await _mirror_leech(client, message, isLeech=True)


@bot.on_message(filters.command(BotCommands.UnzipLeechCommand) & (CustomFilters.authorized_chat | CustomFilters.authorized_user))
async def unzip_leech(client: Client, message: Message):
    await _mirror_leech(client, message, extract=True, isLeech=True)


@bot.on_message(filters.command(BotCommands.ZipLeechCommand) & (CustomFilters.authorized_chat | CustomFilters.authorized_user))
async def zip_leech(client: Client, message: Message):
    await _mirror_leech(client, message, True, isLeech=True)


@bot.on_message(filters.command(BotCommands.QbLeechCommand) & (CustomFilters.authorized_chat | CustomFilters.authorized_user))
async def qb_leech(client: Client, message: Message):
    await _mirror_leech(client, message, isQbit=True, isLeech=True)


@bot.on_message(filters.command(BotCommands.QbUnzipLeechCommand) & (CustomFilters.authorized_chat | CustomFilters.authorized_user))
async def qb_unzip_leech(client: Client, message: Message):
    await _mirror_leech(client, message, extract=True, isQbit=True, isLeech=True)


@bot.on_message(filters.command(BotCommands.QbZipLeechCommand) & (CustomFilters.authorized_chat | CustomFilters.authorized_user))
async def qb_zip_leech(client: Client, message: Message):
    await _mirror_leech(client, message, True, isQbit=True, isLeech=True)
