from os import path as ospath, remove as osremove, makedirs
from subprocess import run as srun
from bot.helper.ext_utils.shortenurl import short_url
from pyrogram import filters, Client
from pyrogram.types import Message
from pyrogram.enums import ChatType
from bot import LOGGER, bot, config_dict, OWNER_ID
from bot.helper.telegram_helper.filters import CustomFilters
from bot.helper.telegram_helper.bot_commands import BotCommands
from bot.helper.telegram_helper.message_utils import editMessage, sendMessage
from bot.helper.ext_utils.telegraph_helper import telegraph
from bot.helper.ext_utils.bot_utils import is_sudo


@bot.on_message(filters.command(BotCommands.MediaInfoCommand) & (CustomFilters.authorized_chat | CustomFilters.authorized_user))
async def mediainfo(c: Client, message: Message):
    user_id = message.from_user.id
    if not config_dict['MEDIAINFO_ENABLED'] and message.chat.type != ChatType.PRIVATE and user_id != OWNER_ID and not is_sudo(user_id):
        return await sendMessage('Mediainfo is Disabled', c, message)
    mediamessage = message.reply_to_message
    process = srun("mediainfo", capture_output=True, shell=True)
    if process.stderr.decode():
        return LOGGER.error("Mediainfo Not Installed.")
    help_msg = "\n<b>By replying to message (including media):</b>"
    help_msg += f"\n<code>/{BotCommands.MediaInfoCommand}" + " {message}" + "</code>"
    if not mediamessage:
        return await sendMessage(help_msg, c, message)
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
        return await sendMessage(help_msg, c, message)
    sent = await sendMessage("Fetching Mediainfo. Downloading your file ...", c, message)
    try:
        VtPath = ospath.join("Mediainfo", str(user_id))
        if not ospath.exists("Mediainfo"):
            makedirs("Mediainfo")
        if not ospath.exists(VtPath):
            makedirs(VtPath)
        try:
            filename = ospath.join(VtPath, file.file_name)
        except:
            filename = None
        file = await c.download_media(message=file, file_name=filename)
    except Exception as e:
        LOGGER.error(e)
        try:
            osremove(file)
        except:
            pass
        file = None
    if not file:
        return await editMessage("Error when downloading. Try again later.", sent)
    cmd = f'mediainfo "{ospath.basename(file)}"'
    LOGGER.info(cmd)
    process = srun(cmd, capture_output=True, shell=True, cwd=VtPath)
    reply = f"<b>MediaInfo: {ospath.basename(file)}</b><br>"
    stderr = process.stderr.decode()
    stdout = process.stdout.decode()
    if len(stdout) != 0:
        reply += f"<b>Stdout:</b><br><br><pre>{stdout}</pre><br>"
        LOGGER.info(f"[Mediainfo] - {cmd} - {stdout}")
    if len(stderr) != 0:
        reply += f"<b>Stderr:</b><br><br><pre>{stderr}</pre>"
        LOGGER.info(f"[Mediainfo] - {cmd} - {stderr}")
    try:
        osremove(file)
    except:
        pass
    help = telegraph.create_page(title="MediaInfo", content=reply)["path"]
    await editMessage(short_url(f"https://te.legra.ph/{help}", message.from_user.id), sent)
