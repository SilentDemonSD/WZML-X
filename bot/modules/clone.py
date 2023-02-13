from random import SystemRandom
from html import escape
from string import ascii_letters, digits
from time import time
from asyncio import sleep as asleep, run_coroutine_threadsafe

from bot.helper.ext_utils.bot_utils import is_sudo, is_paid, get_user_task, get_category_buttons, get_readable_file_size, getUserTDs, \
    is_unified_link, get_bot_pm, is_gdrive_link, is_gdtot_link, is_udrive_link, is_sharer_link, \
    is_sharedrive_link, is_filepress_link, userlistype
from bot.helper.ext_utils.exceptions import DirectDownloadLinkException
from bot.helper.ext_utils.timegap import timegap_check
from bot.helper.mirror_utils.download_utils.direct_link_generator import gdtot, udrive, sharer_pw_dl, shareDrive, filepress, unified
from bot.helper.mirror_utils.status_utils.clone_status import CloneStatus
from bot.helper.mirror_utils.upload_utils.gdriveTools import GoogleDriveHelper
from bot.helper.telegram_helper.bot_commands import BotCommands
from bot.helper.telegram_helper.button_build import ButtonMaker
from bot.helper.telegram_helper.filters import CustomFilters
from bot.helper.telegram_helper.message_utils import *
from bot import LOGGER, download_dict, config_dict, user_data, OWNER_ID, TIME_GAP_STORE, CATEGORY_NAMES, btn_listener, download_dict_lock, \
    Interval, bot, main_loop

from pyrogram import filters, Client
from pyrogram.types import Message, CallbackQuery
from pyrogram.enums import ChatType



async def _clone(c: Client, message: Message):
    user_id = message.from_user.id
    if not await isAdmin(message):
        if message.from_user.username:
            tag = f"@{message.from_user.username}"
        else:
            tag = message.from_user.mention_html(message.from_user.first_name)
        if await forcesub(c, message, tag):
            return

    if not config_dict['CLONE_ENABLED'] and message.chat.type != ChatType.PRIVATE and user_id != OWNER_ID and not is_sudo(user_id):
        reply_message = await sendMessage('Clone is Disabled', c, message)
        return reply_message

    total_task = len(download_dict)
    USER_TASKS_LIMIT = config_dict['USER_TASKS_LIMIT']
    TOTAL_TASKS_LIMIT = config_dict['TOTAL_TASKS_LIMIT']
    if user_id != OWNER_ID and not is_sudo(user_id) and not is_paid(user_id):
        if config_dict['PAID_SERVICE'] is True:
            if TOTAL_TASKS_LIMIT == total_task:
                return await sendMessage(f"<b>BOT TOTAL TASK LIMIT : {TOTAL_TASKS_LIMIT}\nTASKS PROCESSING : {total_task}\n#total limit exceed </b>\n#Buy Paid Service", c, message)
            if USER_TASKS_LIMIT == get_user_task(user_id):
                return await sendMessage(f"<b>BOT USER TASK LIMIT : {USER_TASKS_LIMIT} \nYOUR TASK : {get_user_task(user_id)}\n#user limit exceed</b>\n#Buy Paid Service", c, message)
        else:
            if TOTAL_TASKS_LIMIT == total_task:
                return await sendMessage(f"<b>BOT TOTAL TASK LIMIT : {TOTAL_TASKS_LIMIT}\nTASKS PROCESSING : {total_task}\n#total limit exceed </b>", c, message)
            if USER_TASKS_LIMIT == get_user_task(user_id):
                return await sendMessage(f"<b>BOT USER TASK LIMIT : {USER_TASKS_LIMIT} \nYOUR TASK : {get_user_task(user_id)}\n#user limit exceed</b>", c, message)
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
    msg_id = message.id
    CATUSR = getUserTDs(user_id)[0]
    if len(CATUSR) >= 1:
        u_index = 0

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
            tag = reply_to.from_user.mention_html(
                reply_to.from_user.first_name)

    if not (is_gdrive_link(link) or (link.strip().isdigit() and multi == 0) or is_gdtot_link(link) or is_udrive_link(link) or is_sharer_link(link) or is_sharedrive_link(link) or is_filepress_link(link) or is_unified_link(link)):
        return await sendMessage("Send Gdrive or GDToT/HubDrive/DriveHub(ws)/KatDrive/Kolop/DriveFire/FilePress/SharerPw/ShareDrive link along with command or by replying to the link by command\n\n<b>Multi links only by replying to first link/file:</b>\n<code>/cmd</code> 10(number of links/files)", c, message)

    timeout = 60
    listener = [c, message, c_index, u_index, timeout, time(), tag, link]
    if ((len(CATEGORY_NAMES) > 1 and len(CATUSR) == 0) or (len(CATEGORY_NAMES) >= 1 and len(CATUSR) > 1)) and shwbtns:
        text, btns = get_category_buttons(
            'clone', timeout, msg_id, c_index, u_index, user_id)
        btn_listener[msg_id] = listener
        engine = await sendMessage(text, c, message, btns)
        await _auto_start_dl(engine, msg_id, timeout)
    else:
        await start_clone(listener)

    if multi > 1:
        await asleep(4)
        nextmsg = type('nextmsg', (object, ), {
                       'chat_id': message.chat.id, 'message_id': message.reply_to_message.id + 1})
        cmsg = message.text.split(maxsplit=mi+1)
        cmsg[mi] = f"{multi - 1}"
        nextmsg = await sendMessage(" ".join(cmsg), c, nextmsg)
        nextmsg.from_user.id = message.from_user.id
        await asleep(4)
        await _clone(nextmsg, c)
        # Thread(target=_clone, args=(nextmsg, bot)).start()


async def _auto_start_dl(msg, msg_id, time_out):
    await asleep(time_out)
    try:
        info = btn_listener[msg_id]
        del btn_listener[msg_id]
        await editMessage("Timed out! Task has been started.", msg)
        await start_clone(info)
    except:
        pass


async def start_clone(listelem):
    c = listelem[0]
    message = listelem[1]
    c_index = listelem[2]
    u_index = listelem[3]
    tag = listelem[6]
    link = listelem[7]
    user_id = message.from_user.id
    BOT_PM_X = get_bot_pm(user_id)
    reply_to = message.reply_to_message

    if BOT_PM_X and message.chat.type == message.chat.type.SUPERGROUP:
        PM = await sendMessage("Added your Requested link to Download\n", c, message, chat_id=user_id)
        if PM:
            await PM.delete()
            PM = True
        else: return
    else:
        PM = None

# ---------------------------------------------------------Warn Messages-----------------------------------------------------------------
    if config_dict["AUTO_DELETE_UPLOAD_MESSAGE_DURATION"] != -1 and message.chat.type != ChatType.PRIVATE:
        auto_delete_message = int(
            config_dict["AUTO_DELETE_UPLOAD_MESSAGE_DURATION"] / 60)
        warnmsg = f'\n<b>❗ This message will be deleted in <i>{auto_delete_message} minutes</i> from this group.</b>\n'
    else:
        warnmsg = ''
    if BOT_PM_X and message.chat.type != ChatType.PRIVATE:
        pmwarn = f"\n\n<b>😉Hey {tag}!, I have sent your Cloned links in PM.</b>\n"
    else:
        pmwarn = ''
    if 'mirror_logs' in user_data and message.chat.type != ChatType.PRIVATE:
        logwarn = f"\n<b>⚠️ I have sent files in Mirror Log Channel. Join <a href=\"{config_dict['MIRROR_LOG_URL']}\">Mirror Log channel</a> </b>\n"
    else:
        logwarn = ''
# ---------------------------------------------------------Warn Messages-----------------------------------------------------------------

# --------------------------------------------------------Clone Link Detect Message-----------------------------------------------------
    is_gdtot = is_gdtot_link(link)
    is_udrive = is_udrive_link(link)
    is_sharer = is_sharer_link(link)
    is_sharedrive = is_sharedrive_link(link)
    is_filepress = is_filepress_link(link)
    is_unified = is_unified_link(link)
    if (is_gdtot or is_udrive or is_sharer or is_sharedrive or is_filepress or is_unified):
        try:
            LOGGER.info(f"Processing: {link}")
            if is_gdtot:
                msg = await sendMessage(f"GDTOT LINK DETECTED !", c, message)
                link = gdtot(link)
            elif is_udrive:
                msg = await sendMessage(f"UDRIVE LINK DETECTED !", c, message)
                link = udrive(link)
            elif is_sharer:
                msg = await sendMessage(f"SHARER LINK DETECTED !", c, message)
                link = sharer_pw_dl(link)
            elif is_sharedrive:
                msg = await sendMessage(f"SHAREDRIVE LINK DETECTED !", c, message)
                link = shareDrive(link)
            elif is_filepress:
                msg = await sendMessage(f"FILEPRESS LINK DETECTED !", c, message)
                link = filepress(link)
            elif is_unified:
                msg = await sendMessage(f"UNIFIED LINK DETECTED !", c, message)
                link = unified(link)
            LOGGER.info(f"Generated GDrive Link: {link}")
            await deleteMessage(c, msg)
        except DirectDownloadLinkException as e:
            await deleteMessage(c, msg)
            return await sendMessage(str(e), c, message)
# --------------------------------------------------------Clone Link Detect Message-----------------------------------------------------

# ------------------------------------------------------STOP DIPLICATE/CLONE LIMIT-------------------------------------------------
    gd = GoogleDriveHelper(user_id=user_id)
    # res, size, name, files = gd.helper(link)
    res, size, name, files = await main_loop.create_task(gd.helper(link))
    user_dict = user_data.get(user_id, False)
    IS_USRTD = user_dict.get('is_usertd') if user_dict and user_dict.get(
        'is_usertd') else False
    if res != "":
        return await sendMessage(res, c, message)
    if config_dict['STOP_DUPLICATE'] and IS_USRTD == False:
        LOGGER.info('Checking File/Folder if already in Drive...')
        smsg, button = await gd.drive_list(name, True, True)
        if smsg:
            tegr, html, tgdi = userlistype(user_id)
            if tegr:
                return await sendMessage("Someone already mirrored it for you !\nHere you go:", c, message, button)
            elif html:
                return await sendFile(c, message, button, f"File/Folder is already available in Drive. Here are the search results:\n\n{smsg}")
            else:
                return await sendMessage(smsg, c, message, button)

    CLONE_LIMIT = config_dict['CLONE_LIMIT']
    if CLONE_LIMIT != '' and user_id != OWNER_ID and not is_sudo(user_id) and not is_paid(user_id):
        LOGGER.info('Checking File/Folder Size...')
        if size > (CLONE_LIMIT * 1024**3):
            msg2 = f'Failed, Clone limit is {CLONE_LIMIT}GB.\nYour File/Folder size is {get_readable_file_size(size)}.'
            return await sendMessage(msg2, c, message)
# ------------------------------------------------------STOP DIPLICATE/CLONE LIMIT-------------------------------------------------


# ------------------------------------------------------CLONE MESSAGE CODE--------------------------------------------------------
    if files <= 20:
        msg = await sendMessage(f"Cloning: <code>{link}</code>", c, message)
        # result, button = await main_loop.run_in_executor(None, gd.clone, link, u_index, c_index)
        result, button = await main_loop.create_task(gd.clone(link, u_index, c_index))
        await deleteMessage(c, msg)
    else:
        drive = GoogleDriveHelper(name, user_id=user_id)
        gid = ''.join(SystemRandom().choices(ascii_letters + digits, k=12))
        clone_status = CloneStatus(drive, size, message, gid)
        async with download_dict_lock:
            download_dict[message.id] = clone_status
        await sendStatusMessage(message, c)
        # result, button = await main_loop.run_in_executor(None, drive.clone, link, u_index, c_index)
        result, button = await main_loop.create_task(drive.clone(link, u_index, c_index))
        async with download_dict_lock:
            del download_dict[message.id]
            count = len(download_dict)
        try:
            if count == 0:
                Interval[0].cancel()
                del Interval[0]
                await delete_all_messages()
            else:
                await update_all_messages()
        except IndexError:
            pass
    if config_dict['EMOJI_THEME']:
        hide = f"<b>🗂️ Name: </b><{config_dict['NAME_FONT']}>{escape(name)}</{config_dict['NAME_FONT']}>\n"
        cc = f'\n<b>╰👤 #Clone_By: </b>{tag}\n\n'
    else:
        hide = f"<b> Name: </b><{config_dict['NAME_FONT']}>{escape(name)}</{config_dict['NAME_FONT']}>\n"
        cc = f'\n<b>╰ #Clone_By: </b>{tag}\n\n'
    if isinstance(button, str) and button.build_menu(2) in ["cancelled", ""]:
        await sendMessage(f"{tag} {result}", c, message)
    else:
        buttons = ButtonMaker()
        bot_d = await c.get_me()
        b_uname = bot_d.username
        botstart = f"http://t.me/{b_uname}"
        buttons.buildbutton("View links in PM", f"{botstart}")
        if PM:
            await sendPhoto(f"{result + cc}", c, message, reply_markup=button.build_menu(2), chat_id=user_id)
            msg = await sendPhoto(f"{hide + warnmsg + pmwarn + logwarn}", c, message, reply_markup=buttons.build_menu(2))
            
        else:
            if message.chat.type != ChatType.PRIVATE:
                if config_dict['SAVE_MSG']:
                    button.sbutton("Save This Message", 'save', 'footer')
            msg = await sendPhoto(f"{result + cc + warnmsg + logwarn}", c, message, reply_markup=button.build_menu(2))
        
        await sendMirrorLogMessage(result + cc, c, message, PM, button)
        main_loop.create_task(auto_delete_upload_message(c, message, msg))
        LOGGER.info(f'Cloning Done: {name}')
# ------------------------------------------------------CLONE MESSAGE CODE-----------------------------------------------------


# --------------------------------------------------Delete Gdrive Sharer File---------------------------------------------------
    if config_dict['SAME_ACC_COOKIES']:
        if (is_gdtot or is_udrive or is_sharer or is_sharedrive):
            await main_loop.run_in_executor(None, gd.deletefile, link)
# --------------------------------------------------Delete Gdrive Sharer File---------------------------------------------------


# --------------------------------------------------LINK LOG CODE---------------------------------------------------------------
    mesg = message.text.split('\n')
    message_args = mesg[0].split(' ', maxsplit=1)
    await sendLinkLogMessage(c, message_args, name, size, tag, user_id, reply_to)
    
# --------------------------------------------------LINK LOG CODE---------------------------------------------------------------


@bot.on_callback_query(filters.regex(r"^clone"))
async def confirm_clone(c: Client, query: CallbackQuery):
    user_id = query.from_user.id
    message = query.message
    data = query.data
    data = data.split()
    msg_id = int(data[2])
    try:
        listenerInfo = btn_listener[msg_id]
    except KeyError:
        return await editMessage(f"<b>Download has been cancelled or already started!</b>", message)
    if user_id != listenerInfo[1].from_user.id:
        return await query.answer("You are not the owner of this task!", show_alert=True)
    elif data[1] == 'scat':
        c_index = int(data[3])
        u_index = None
        if listenerInfo[2] == c_index:
            return await query.answer(f"{CATEGORY_NAMES[c_index]} is selected already!", show_alert=True)
        await query.answer()
        listenerInfo[2] = c_index
        listenerInfo[3] = u_index
    elif data[1] == 'ucat':
        u_index = int(data[3])
        c_index = 0
        if listenerInfo[3] == u_index:
            return await query.answer(f"{getUserTDs(listenerInfo[1].from_user.id)[0][u_index]} is already selected!", show_alert=True)
        await query.answer()
        listenerInfo[2] = c_index
        listenerInfo[3] = u_index
    elif data[1] == 'cancel':
        await query.answer()
        del btn_listener[msg_id]
        return await editMessage(f"<b>Download has been cancelled!</b>", message)
    elif data[1] == 'start':
        await query.answer()
        del btn_listener[msg_id]
        await message.delete()
        return await start_clone(listenerInfo)
    timeout = listenerInfo[4] - (time() - listenerInfo[5])
    text, btns = get_category_buttons(
        'clone', timeout, msg_id, listenerInfo[2], listenerInfo[3], listenerInfo[1].from_user.id)
    await editMessage(text, message, btns)


@bot.on_message(filters.command(BotCommands.CloneCommand) & (CustomFilters.authorized_chat | CustomFilters.authorized_user))
async def cloneNode(c: Client, message: Message):
    await _clone(c, message)

