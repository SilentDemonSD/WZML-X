import os
import shlex
import time
from subprocess import run
from telegram import Message, Bot
from telegram.ext import CommandHandler
from telegram.helpers import escape_markdown
from bot.helper.ext_utils.shortenurl import short_url
from bot.helper.telegram_helper.filters import CustomFilters
from bot.helper.telegram_helper.bot_commands import BotCommands
from bot.helper.telegram_helper.message_utils import editMessage, sendMessage
from bot.helper.ext_utils.telegraph_helper import telegraph
import logging
import time

logger = logging.getLogger(__name__)

def mediainfo(update: Message, context: Bot) -> None:
    message: Message = update.effective_message
    mediamessage = message.reply_to_message

    if not mediamessage:
        return sendMessage(get_help_msg(), context.bot, update.message)

    file = None
    media_array = [
        mediamessage.document,
        mediamessage.video,
        mediamessage.audio,
        mediamessage.document,
        mediamessage.video,
        mediamessage.photo,
        mediamessage.audio,
        mediamessage.voice,
        mediamessage.animation,
        mediamessage.video_note,
        mediamessage.sticker,
    ]

    for i in media_array:
        if i is not None:
            file = i
            break

    if not file:
        return sendMessage(get_help_msg(), context.bot, update.message)

    sent = sendMessage('Running mediainfo. Downloading your file.', context.bot, update.message)

    try:
        VtPath = os.path.join("Mediainfo", str(message.from_user.id))
        os.makedirs(VtPath, exist_ok=True)
        filename = os.path.join(VtPath, file.file_name)
        file = context.bot.download_media(message=file, file_name=filename)
    except Exception as e:
        logger.error(e)
        try:
            os.remove(file)
        except:
            pass
        file = None

    if not file:
        return editMessage("Error when downloading. Try again later.", sent)

    time.sleep(1)

    cmd = f'mediainfo "{os.path.abspath(file)}"'
    logger.info(f"mediainfo - {cmd}")

    try:
        process = run(shlex.quote(cmd), capture_output=True, shell=True, cwd=VtPath)
    except Exception as e:
        logger.error(e)
        try:
            os.remove(file)
        except:
            pass
        return editMessage("Error when running mediainfo. Try again later.", sent)

    reply = f"<b>MediaInfo: {os.path.basename(file)}</b><br>"
    stderr = process.stderr.decode()
    stdout = process.stdout.decode()

    if len(stdout) != 0:
        reply += f"<b>Stdout:</b><br><br><pre>{escape_markdown(stdout)}</pre><br>"
        logger.info(f"mediainfo - {cmd} - {stdout}")

    if len(stderr) != 0:
        reply += f"<b>Stderr:</b><br><br><pre>{escape_markdown(stderr)}</pre>"
        logger.error(f"mediainfo - {cmd} - {stderr}")

    try:
        os.remove(file)
    except:
        pass

    help = telegraph.create_page(title='MediaInfo', content=reply)["path"]
    editMessage(short_url(f"https://telegra.ph/{help}", update.message.from_user.id), sent)

    context.job_queue.run_once(delete_telegraph_page, 1800, context=help)

def delete_telegraph_page(context):
    help = context
    try:
        telegraph.delete_page(help)
    except:
        pass

def get_help_msg() -> str:
    return f"<b>By replying to message (including media):</b>" \
           f"\n<code>/{BotCommands.MediaInfoCommand} {message}</code>"

authfilter = CustomFilters.authorized_chat if config_dict['MEDIAINFO_ENABLED'] is True else CustomFilters.owner_filter
mediainfo_handler = CommandHandler(BotCommands.MediaInfoCommand, mediainfo, filters=authfilter | CustomFilters.authorized_user)

dispatcher.add_handler(mediainfo_handler)
