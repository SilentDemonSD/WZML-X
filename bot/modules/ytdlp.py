from threading import Thread
from time import sleep, time
from requests import request
from re import split as re_split
from telegram.ext import CommandHandler, CallbackQueryHandler

from bot.helper.ext_utils.bot_utils import get_bot_pm, is_sudo, is_paid, get_user_task, is_url, getUserTDs, new_thread, \
                                            get_category_buttons, get_readable_file_size
from bot.helper.ext_utils.timegap import timegap_check
from bot.helper.mirror_utils.download_utils.yt_dlp_download_helper import YoutubeDLHelper
from bot.helper.telegram_helper.bot_commands import BotCommands
from bot.helper.telegram_helper.button_build import ButtonMaker
from bot.helper.telegram_helper.filters import CustomFilters
from bot.helper.telegram_helper.message_utils import sendMessage, editMessage, auto_delete_message, isAdmin, forcesub
from bot import LOGGER, download_dict, config_dict, OWNER_ID, TIME_GAP_STORE, CATEGORY_NAMES, btn_listener, DOWNLOAD_DIR, user_data, dispatcher
from .listener import MirrorLeechListener

listener_dict = {}

def _ytdl(bot, message, isZip=False, isLeech=False):
    mssg = message.text
    user_id = message.from_user.id
    msg_id = message.message_id
    qual = ''
    select = False
    multi = 0
    c_index = 0
    u_index = None
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
            reply_message = sendMessage(startwarn, bot, message, buttons.build_menu(2))
            Thread(target=auto_delete_message, args=(bot, message, reply_message)).start()
            return reply_message

    total_task = len(download_dict)
    user_id = message.from_user.id
    USER_TASKS_LIMIT = config_dict['USER_TASKS_LIMIT']
    TOTAL_TASKS_LIMIT = config_dict['TOTAL_TASKS_LIMIT']
    if user_id != OWNER_ID and not is_sudo(user_id) and not is_paid(user_id):
        if config_dict['PAID_SERVICE'] is True:
            if TOTAL_TASKS_LIMIT == total_task:
                return sendMessage(f"<b>Bᴏᴛ Tᴏᴛᴀʟ Tᴀsᴋ Lɪᴍɪᴛ : {TOTAL_TASKS_LIMIT}\nTᴀsᴋs Pʀᴏᴄᴇssɪɴɢ : {total_task}\n#total limit exceed </b>\n#Buy Paid Service", bot ,message)
            if USER_TASKS_LIMIT == get_user_task(user_id):
                return sendMessage(f"<b>Bᴏᴛ Usᴇʀ Tᴀsᴋ Lɪᴍɪᴛ : {USER_TASKS_LIMIT} \nYᴏᴜʀ Tᴀsᴋs : {get_user_task(user_id)}\n#user limit exceed</b>\n#Buy Paid Service", bot ,message)
        else:
            if TOTAL_TASKS_LIMIT == total_task:
                return sendMessage(f"<b>Bᴏᴛ Tᴏᴛᴀʟ Tᴀsᴋ Lɪᴍɪᴛ : {TOTAL_TASKS_LIMIT}\nTᴀsᴋs Pʀᴏᴄᴇssɪɴɢ : {total_task}\n#total limit exceed </b>", bot ,message)
            if USER_TASKS_LIMIT == get_user_task(user_id):
                return sendMessage(f"<b>Bᴏᴛ Usᴇʀ Tᴀsᴋ Lɪᴍɪᴛ : {USER_TASKS_LIMIT} \nYᴏᴜʀ Tᴀsᴋs : {get_user_task(user_id)}\n#user limit exceed</b>", bot ,message)
        time_gap = timegap_check(message)
        if time_gap:
            return
        TIME_GAP_STORE[message.from_user.id] = time()
        
    index = 1
    link = ''

    args = mssg.split(maxsplit=2)
    if len(args) > 1:
        for x in args:
            x = x.strip()
            if x in ['|', 'pswd:', 'opt:']:
                break
            elif x == 's':
               select = True
               index += 1
            elif x.strip().isdigit():
                multi = int(x)
                mi = index
        if multi == 0:
            args = mssg.split(maxsplit=index)
            if len(args) > index:
                link = args[index].strip()
                if link.startswith(("|", "pswd:", "opt:")):
                    link = ''
                else:
                    link = re_split(r"opt:|pswd:|\|", link)[0]
                    link = link.strip()

    name = mssg.split('|', maxsplit=1)
    if len(name) > 1:
        if 'opt:' in name[0] or 'pswd:' in name[0]:
            name = ''
        else:
            name = re_split('pswd:|opt:', name[1])[0].strip()
    else:
        name = ''

    pswd = mssg.split(' pswd: ')
    pswd = pswd[1].split(' opt: ')[0] if len(pswd) > 1 else None

    opt = mssg.split(' opt: ')
    opt = opt[1] if len(opt) > 1 else ''

    if message.from_user.username:
        tag = f"@{message.from_user.username}"
    else:
        tag = message.from_user.mention_html(message.from_user.first_name)

    reply_to = message.reply_to_message
    if reply_to is not None:
        if len(link) == 0:
            link = reply_to.text.split(maxsplit=1)[0].strip()
        if reply_to.from_user.username:
            tag = f"@{reply_to.from_user.username}"
        else:
            tag = reply_to.from_user.mention_html(reply_to.from_user.first_name)

    if not is_url(link):
        help_msg = """
<b>Send link along with command line:</b>
<code>/cmd</code> s link |newname pswd: xx(zip) opt: x:y|x1:y1
<b>By replying to link:</b>
<code>/cmd</code> |newname pswd: xx(zip) opt: x:y|x1:y1
<b>Quality Buttons:</b>
Incase default quality added but you need to select quality for specific link or links with multi links feature.
<code>/cmd</code> s link
This perfix should be always before |newname, pswd: and opt:
<b>Options Example:</b> opt: playliststart:^10|matchtitle:S13|writesubtitles:true|live_from_start:true|postprocessor_args:{"ffmpeg": ["-threads", "4"]}|wait_for_video:(5, 100)
<b>Multi links only by replying to first link:</b>
<code>/cmd</code> 10(number of links)
Number should be always before |newname, pswd: and opt:
<b>Options Note:</b> Add `^` before integer, some values must be integer and some string.
Like playlist_items:10 works with string, so no need to add `^` before the number but playlistend works only with integer so you must add `^` before the number like example above.
You can add tuple and dict also. Use double quotes inside dict.
<b>NOTE:</b>
You can add perfix randomly before link those for select (s) and mutli links (number).
You can't add perfix randomly after link. They should be arranged like exmaple above, rename then pswd then opt. If you don't want to add pswd for example then it will be (|newname opt:), just don't change the arrangement.
You can always add video quality from yt-dlp api options.
Check all yt-dlp api options from this <a href='https://github.com/yt-dlp/yt-dlp/blob/master/yt_dlp/YoutubeDL.py#L178'>FILE</a>.
        """
        return sendMessage(help_msg, bot, message)

    CATUSR = getUserTDs(user_id)[0] 
    if len(CATUSR) >= 1: u_index = 0
    listener = [bot, message, isZip, isLeech, pswd, tag, link]
    extra = [name, opt, qual, select, c_index, u_index, time()]
    if ((len(CATEGORY_NAMES) > 1 and len(CATUSR) == 0) or (len(CATEGORY_NAMES) >= 1 and len(CATUSR) > 1)) and not isLeech:
        timeout = 60
        btn_listener[msg_id] = [extra, listener, timeout]
        text, btns = get_category_buttons('ytdlp', timeout, msg_id, c_index, u_index, user_id)
        engine = sendMessage(text, bot, message, btns)
        _auto_start_dl(engine, msg_id, timeout)
    else:
        start_ytdlp(extra, listener)
    if multi > 1:
        sleep(4)
        nextmsg = type('nextmsg', (object, ), {'chat_id': message.chat_id, 'message_id': message.reply_to_message.message_id + 1})
        ymsg = mssg.split(maxsplit=mi+1)
        ymsg[mi] = f"{multi - 1}"
        nextmsg = sendMessage(" ".join(ymsg), bot, nextmsg)
        nextmsg.from_user.id = message.from_user.id
        sleep(4)
        Thread(target=_ytdl, args=(bot, nextmsg, isZip, isLeech)).start()

def _qual_subbuttons(task_id, b_name, msg):
    buttons = ButtonMaker()
    task_info = listener_dict[task_id]
    formats_dict = task_info[6]
    for tbr, d_data in formats_dict[b_name].items():
        buttonName = f"{tbr}K ({get_readable_file_size(d_data[0])})"
        buttons.sbutton(buttonName, f"qu {task_id} {b_name}|{tbr}")
    buttons.sbutton("Back", f"qu {task_id} back")
    buttons.sbutton("Cancel", f"qu {task_id} cancel")
    SUBBUTTONS = buttons.build_menu(2)
    editMessage(f"Choose Bit rate for <b>{b_name}</b>:", msg, SUBBUTTONS)

def _mp3_subbuttons(task_id, msg, playlist=False):
    buttons = ButtonMaker()
    audio_qualities = [64, 128, 320]
    for q in audio_qualities:
        if playlist:
            i = 's'
            audio_format = f"ba/b-{q} t"
        else:
            i = ''
            audio_format = f"ba/b-{q}"
        buttons.sbutton(f"{q}K-mp3", f"qu {task_id} {audio_format}")
    buttons.sbutton("Back", f"qu {task_id} back")
    buttons.sbutton("Cancel", f"qu {task_id} cancel")
    SUBBUTTONS = buttons.build_menu(2)
    editMessage(f"Choose Audio{i} Bitrate:", msg, SUBBUTTONS)

def select_format(update, context):
    query = update.callback_query
    user_id = query.from_user.id
    data = query.data
    msg = query.message
    data = data.split(" ")
    task_id = int(data[1])
    try:
        task_info = listener_dict[task_id]
    except:
        return editMessage("This is an old task", msg)
    uid = task_info[1]
    if user_id != uid and not CustomFilters.owner_query(user_id):
        return query.answer(text="This task is not for you!", show_alert=True)
    elif data[2] == "dict":
        query.answer()
        b_name = data[3]
        _qual_subbuttons(task_id, b_name, msg)
        return
    elif data[2] == "back":
        query.answer()
        return editMessage('Choose Video Quality:', msg, task_info[4])
    elif data[2] == "mp3":
        query.answer()
        playlist = len(data) == 4
        _mp3_subbuttons(task_id, msg, playlist)
        return
    elif data[2] == "cancel":
        query.answer()
        editMessage('Task has been cancelled.', msg)
    else:
        query.answer()
        listener = task_info[0]
        link = task_info[2]
        name = task_info[3]
        opt = task_info[5]
        qual = data[2]
        if len(data) == 4:
            playlist = True
            if '|' in qual:
                qual = task_info[6][qual]
        else:
            playlist = False
            if '|' in qual:
                b_name, tbr = qual.split('|')
                qual = task_info[6][b_name][tbr][1]
        ydl = YoutubeDLHelper(listener)
        LOGGER.info(f"Downloading with YT-DLP: {link}")
        Thread(target=ydl.add_download, args=(link, f'{DOWNLOAD_DIR}{task_id}', name, qual, playlist, opt)).start()
        query.message.delete()
    del listener_dict[task_id]

def _mdisk(link, name):
    key = link.split('/')[-1]
    resp = request('GET', f'https://diskuploader.entertainvideo.com/v1/file/cdnurl?param={key}', headers={
    'Accept': '*/*',
    'Accept-Language': 'en-US,en;q=0.5',
    'Accept-Encoding': 'gzip, deflate, br',
    'Referer': 'https://mdisk.me/',
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/93.0.4577.82 Safari/537.36'
    })
    if resp.ok:
        resp = resp.json()
        link = resp['source']
        if not name:
            name = resp['filename']
    return name, link

def start_ytdlp(extra, ytdlp_listener):
    bot = ytdlp_listener[0]
    message = ytdlp_listener[1]
    isZip = ytdlp_listener[2]
    isLeech = ytdlp_listener[3]
    pswd = ytdlp_listener[4]
    tag = ytdlp_listener[5]
    link = ytdlp_listener[6]
    name = extra[0]
    opt = extra[1]
    qual = extra[2]
    select = extra[3]
    c_index = extra[4]
    u_index = extra[5]
    msg_id = message.message_id
    user_id = message.from_user.id

    listener = MirrorLeechListener(bot, message, isZip, isLeech=isLeech, pswd=pswd, tag=tag,  c_index=c_index, u_index=u_index)
    if 'mdisk.me' in link:
        name, link = _mdisk(link, name)
    ydl = YoutubeDLHelper(listener)
    try:
        result = ydl.extractMetaData(link, name, opt, True)
    except Exception as e:
        msg = str(e).replace('<', ' ').replace('>', ' ')
        return sendMessage(tag + " " + msg, bot, message)
    if not select:
        user_dict = user_data.get(user_id, False)
        if 'format:' in opt:
            opts = opt.split('|')
            for f in opts:
                if f.startswith('format:'):
                    qual = f.split('format:', 1)[1]
        elif user_dict and user_dict.get('yt_ql', False):
            qual = user_dict['yt_ql']
        elif config_dict['YT_DLP_QUALITY']:
            qual = config_dict['YT_DLP_QUALITY']
    if qual:
        playlist = 'entries' in result
        LOGGER.info(f"Downloading with YT-DLP: {link}")
        Thread(target=ydl.add_download, args=(link, f'{DOWNLOAD_DIR}{msg_id}', name, qual, playlist, opt)).start()
    else:
        buttons = ButtonMaker()
        best_video = "bv*+ba/b"
        best_audio = "ba/b"
        formats_dict = {}
        if 'entries' in result:
            for i in ['144', '240', '360', '480', '720', '1080', '1440', '2160']:
                video_format = f"bv*[height<=?{i}][ext=mp4]+ba[ext=m4a]/b[height<=?{i}]"
                b_data = f"{i}|mp4"
                formats_dict[b_data] = video_format
                buttons.sbutton(f"{i}-mp4", f"qu {msg_id} {b_data} t")
                video_format = f"bv*[height<=?{i}][ext=webm]+ba/b[height<=?{i}]"
                b_data = f"{i}|webm"
                formats_dict[b_data] = video_format
                buttons.sbutton(f"{i}-webm", f"qu {msg_id} {b_data} t")
            buttons.sbutton("MP3", f"qu {msg_id} mp3 t")
            buttons.sbutton("Best Videos", f"qu {msg_id} {best_video} t")
            buttons.sbutton("Best Audios", f"qu {msg_id} {best_audio} t")
            buttons.sbutton("Cancel", f"qu {msg_id} cancel")
            YTBUTTONS = buttons.build_menu(3)
            listener_dict[msg_id] = [listener, user_id, link, name, YTBUTTONS, opt, formats_dict]
            bmsg = sendMessage('Choose Playlist Videos Quality:', bot, message, YTBUTTONS)
        else:
            formats = result.get('formats')
            is_m4a = False
            if formats is not None:
                for frmt in formats:
                    if frmt.get('tbr'):

                        format_id = frmt['format_id']

                        if frmt.get('filesize'):
                            size = frmt['filesize']
                        elif frmt.get('filesize_approx'):
                            size = frmt['filesize_approx']
                        else:
                            size = 0

                        if frmt.get('video_ext') == 'none' and frmt.get('acodec') != 'none':
                            if frmt.get('audio_ext') == 'm4a':
                                is_m4a = True
                            b_name = f"{frmt['acodec']}-{frmt['ext']}"
                            v_format = f"ba[format_id={format_id}]"
                        elif frmt.get('height'):
                            height = frmt['height']
                            ext = frmt['ext']
                            fps = frmt['fps'] if frmt.get('fps') else ''
                            b_name = f"{height}p{fps}-{ext}"
                            if ext == 'mp4':
                                ba_ext = '[ext=m4a]' if is_m4a else ''
                                v_format = f"bv*[format_id={format_id}]+ba{ba_ext}/b[height=?{height}]"
                            else:
                                v_format = f"bv*[format_id={format_id}]+ba/b[height=?{height}]"
                        else:
                            continue

                        if b_name in formats_dict:
                            formats_dict[b_name][str(frmt['tbr'])] = [size, v_format]
                        else:
                            subformat = {str(frmt['tbr']): [size, v_format]}
                            formats_dict[b_name] = subformat

                for b_name, d_dict in formats_dict.items():
                    if len(d_dict) == 1:
                        tbr, v_list = list(d_dict.items())[0]
                        buttonName = f"{b_name} ({get_readable_file_size(v_list[0])})"
                        buttons.sbutton(buttonName, f"qu {msg_id} {b_name}|{tbr}")
                    else:
                        buttons.sbutton(b_name, f"qu {msg_id} dict {b_name}")
            buttons.sbutton("MP3", f"qu {msg_id} mp3")
            buttons.sbutton("Best Video", f"qu {msg_id} {best_video}")
            buttons.sbutton("Best Audio", f"qu {msg_id} {best_audio}")
            buttons.sbutton("Cancel", f"qu {msg_id} cancel")
            YTBUTTONS = buttons.build_menu(2)
            listener_dict[msg_id] = [listener, user_id, link, name, YTBUTTONS, opt, formats_dict]
            bmsg = sendMessage('Choose Video Quality:', bot, message, YTBUTTONS)
        Thread(target=_auto_cancel, args=(bmsg, msg_id)).start()

@new_thread
def _auto_start_dl(msg, msg_id, time_out):
    sleep(time_out)
    if msg_id not in btn_listener:
        return
    info = btn_listener[msg_id]
    del btn_listener[msg_id]
    start_ytdlp(info[0], info[1])
    editMessage("Timed out! Task has been started.", msg)

@new_thread
def ytdl_confirm(update, context):
    query = update.callback_query
    user_id = query.from_user.id
    message = query.message
    data = query.data
    data = data.split()
    msg_id = int(data[2])
    try:
        listnerInfo = btn_listener[msg_id]
    except KeyError:
        return editMessage(f"<b>Download has been cancelled or already started!</b>", message)
    extra = listnerInfo[0]
    listener = listnerInfo[1]
    if user_id != listener[1].from_user.id and not CustomFilters.owner_query(user_id):
        return query.answer("You are not the owner of this download", show_alert=True)
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
    elif data[1] == "cancel":
        query.answer()
        del btn_listener[msg_id]
        return editMessage('<b>Download has been cancelled</b>', message)
    else:
        query.answer()
        message.delete()
        del btn_listener[msg_id]
        return start_ytdlp(extra, listener)
    timeout = listnerInfo[2] - (time() - extra[6])
    text, btns = get_category_buttons('ytdlp', timeout, msg_id, extra[4], extra[5], listener[1].from_user.id)
    editMessage(text, message, btns)

def _auto_cancel(msg, task_id):
    sleep(120)
    try:
        del listener_dict[task_id]
        editMessage('Timed out! Task has been cancelled.', msg)
    except:
        pass

def ytdl(update, context):
    _ytdl(context.bot, update.message)

def ytdlZip(update, context):
    _ytdl(context.bot, update.message, True)

def ytdlleech(update, context):
    _ytdl(context.bot, update.message, isLeech=True)

def ytdlZipleech(update, context):
    _ytdl(context.bot, update.message, True, True)


authfilter = CustomFilters.authorized_chat if config_dict['WATCH_ENABLED'] is True else CustomFilters.owner_filter
ytdl_handler = CommandHandler(BotCommands.YtdlCommand, ytdl,
                                    filters=authfilter | CustomFilters.authorized_user)
ytdl_zip_handler = CommandHandler(BotCommands.YtdlZipCommand, ytdlZip,
                                    filters=authfilter | CustomFilters.authorized_user)
ytdl_leech_handler = CommandHandler(BotCommands.YtdlLeechCommand, ytdlleech,
                                    filters=authfilter | CustomFilters.authorized_user)
ytdl_zip_leech_handler = CommandHandler(BotCommands.YtdlZipLeechCommand, ytdlZipleech,
                                    filters=authfilter | CustomFilters.authorized_user)


quality_handler = CallbackQueryHandler(select_format, pattern="qu")
ytdl_confirm_handler = CallbackQueryHandler(ytdl_confirm, pattern="ytdlp")

dispatcher.add_handler(ytdl_confirm_handler)
dispatcher.add_handler(ytdl_handler)
dispatcher.add_handler(ytdl_zip_handler)
dispatcher.add_handler(ytdl_leech_handler)
dispatcher.add_handler(ytdl_zip_leech_handler)
dispatcher.add_handler(quality_handler)
