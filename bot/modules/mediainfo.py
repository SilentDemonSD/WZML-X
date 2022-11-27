from telegram import Message
import os
from subprocess import run
from bot.helper.ext_utils.shortenurl import short_url
from telegram.ext import CommandHandler
from bot import LOGGER, dispatcher, app, MEDIAINFO_ENABLED, config_dict
from bot.helper.telegram_helper.filters import CustomFilters
from bot.helper.telegram_helper.bot_commands import BotCommands
from bot.helper.telegram_helper.message_utils import editMessage, sendMessage
from bot.helper.ext_utils.telegraph_helper import telegraph


def mediainfo(update, context):
    message:Message = update.effective_message
    mediamessage = message.reply_to_message
    # mediainfo control +
    process = run('mediainfo', capture_output=True, shell=True)
    if process.stderr.decode(): return LOGGER.error("mediainfo not installed. Read readme.")
    # mediainfo control -
    help_msg = "\n<b>By replying to message (including media):</b>"
    help_msg += f"\n<code>/{BotCommands.MediaInfoCommand}" + " {message}" + "</code>"
    if not mediamessage: return sendMessage(help_msg, context.bot, update.message)
    file = None
    media_array = [mediamessage.document, mediamessage.video, mediamessage.audio, mediamessage.document, \
        mediamessage.video, mediamessage.photo, mediamessage.audio, mediamessage.voice, \
        mediamessage.animation, mediamessage.video_note, mediamessage.sticker]
    for i in media_array:
        if i is not None:
            file = i
            break
    if not file: return sendMessage(help_msg, context.bot, update.message)
    sent = sendMessage('Running mediainfo. Downloading your file.', context.bot, update.message)
    try:
        VtPath = os.path.join("Mediainfo", str(message.from_user.id))
        if not os.path.exists("Mediainfo"): os.makedirs("Mediainfo")
        if not os.path.exists(VtPath): os.makedirs(VtPath)
        try: filename = os.path.join(VtPath, file.file_name)
        except: filename = None
        file = app.download_media(message=file, file_name=filename)
    except Exception as e:
        LOGGER.error(e)
        try: os.remove(file)
        except: pass
        file = None
    if not file: return editMessage("Error when downloading. Try again later.", sent)
    cmd = f'mediainfo "{os.path.basename(file)}"'
    LOGGER.info(cmd)
    process = run(cmd, capture_output=True, shell=True, cwd=VtPath)
    reply = f"<b>MediaInfo: {os.path.basename(file)}</b><br>"
    stderr = process.stderr.decode()
    stdout = process.stdout.decode()
    if len(stdout) != 0:
        reply += f"<b>Stdout:</b><br><br><pre>{stdout}</pre><br>"
        # LOGGER.info(f"mediainfo - {cmd} - {stdout}")
    if len(stderr) != 0:
        reply += f"<b>Stderr:</b><br><br><pre>{stderr}</pre>"
        # LOGGER.error(f"mediainfo - {cmd} - {stderr}")
    try: os.remove(file)
    except: pass
    help = telegraph.create_page(title='MediaInfo', content=reply)["path"]
    editMessage(short_url(f"https://telegra.ph/{help}"), sent)


authfilter = CustomFilters.authorized_chat if config_dict['MEDIAINFO_ENABLED'] is True else CustomFilters.owner_filter
mediainfo_handler = CommandHandler(BotCommands.MediaInfoCommand, mediainfo,
                                    filters=authfilter | CustomFilters.authorized_user, run_async=True)


dispatcher.add_handler(mediainfo_handler)
