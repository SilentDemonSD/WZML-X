#
from aiofiles.os import remove as aioremove, path as aiopath, mkdir
from bot.helper.ext_utils.shortners import short_url

from pyrogram.handlers import MessageHandler 
from pyrogram.filters import command

from bot import LOGGER, bot, config_dict
from bot.helper.telegram_helper.filters import CustomFilters
from bot.helper.telegram_helper.bot_commands import BotCommands
from bot.helper.telegram_helper.message_utils import editMessage, sendMessage
from bot.helper.ext_utils.bot_utils import cmd_exec
#from bot.helper.ext_utils.telegraph_helper import telegraph


async def telegram_mediainfo(message, media):
    temp_send = await sendMessage(message, 'Generating MediaInfo...')
    try:
        VtPath = aiopath.join("Mediainfo", str(message.id))
        if not aiopath.exists("Mediainfo"): 
            mkdir("Mediainfo")
        if not aiopath.exists(VtPath): 
            os.makedirs(VtPath)
        try: filename = os.path.join(VtPath, file.file_name)
        except: filename = None
        #file
    except Exception as e:
        LOGGER.error(e)
        try: aioremove(file)
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
    editMessage(short_url(f"https://telegra.ph/{help}", update.message.from_user.id), sent)

async def mediainfo(_, message):
    help_msg = "\n<b>By replying to message (including media):</b>"
    help_msg += f"\n<code>/{BotCommands.MediaInfoCommand}" + " {message}" + "</code>"
    if message.command > 2:
        link = message.command[1]
        
    elif mediamessage := message.reply_to_message:
        file = next((i for i in [mediamessage.document, mediamessage.video, mediamessage.audio, mediamessage.document,
                         mediamessage.video, mediamessage.photo, mediamessage.audio, mediamessage.voice,
                         mediamessage.animation, mediamessage.video_note, mediamessage.sticker] if i is not None), None)
        if not file:
            return await sendMessage(message, help_msg)
        await telegram_mediainfo(message, file)
    else:
        return await sendMessage(message, help_msg)

bot.add_handler(MessageHandler(mediainfo, filters=command(BotCommands.MediaInfoCommand) & CustomFilters.authorized))
