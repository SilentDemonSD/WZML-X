import hashlib, os, time
from telegram.ext import CommandHandler
from bot import LOGGER, dispatcher, app
from bot.helper.telegram_helper.filters import CustomFilters
from bot.helper.telegram_helper.bot_commands import BotCommands
from bot.helper.telegram_helper.message_utils import editMessage, sendMessage


def HumanBytes(size):
    if not size: return ""
    power = 2 ** 10
    n = 0
    Dic_powerN = {0: " ", 1: "K", 2: "M", 3: "G", 4: "T"}
    while size > power:
        size /= power
        n += 1
    return str(round(size, 2)) + " " + Dic_powerN[n] + "iB"


def TimeFormatter(milliseconds: int) -> str:
    seconds, milliseconds = divmod(int(milliseconds), 1000)
    minutes, seconds = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    days, hours = divmod(hours, 24)
    tmp = ((str(days) + "d, ") if days else "") + \
        ((str(hours) + "h, ") if hours else "") + \
        ((str(minutes) + "m, ") if minutes else "") + \
        ((str(seconds) + "s, ") if seconds else "") + \
        ((str(milliseconds) + "ms, ") if milliseconds else "")
    return tmp[:-2]


def hash(update, context):
    message = update.effective_message
    mediamessage = message.reply_to_message
    help_msg = "<b>Reply to message including file:</b>"
    help_msg += f"\n<code>/{BotCommands.HashCommand}" + " {message}" + "</code>"
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
    VtPath = os.path.join("Hasher", str(message.from_user.id))
    if not os.path.exists("Hasher"): os.makedirs("Hasher")
    if not os.path.exists(VtPath): os.makedirs(VtPath)
    sent = sendMessage("Trying to download. Please wait.", context.bot, update.message)
    try:
        filename = os.path.join(VtPath, file.file_name)
        file = app.download_media(message=file, file_name=filename)
    except Exception as e:
        LOGGER.error(e)
        try: os.remove(file)
        except: pass
        file = None
    if not file: return editMessage("Error when downloading. Try again later.", sent)
    hashStartTime = time.time()
    try:
        with open(file, "rb") as f:
            md5 = hashlib.md5()
            sha1 = hashlib.sha1()
            sha224 = hashlib.sha224()
            sha256 = hashlib.sha256()
            sha512 = hashlib.sha512()
            sha384 = hashlib.sha384()
            while chunk := f.read(8192):
                md5.update(chunk)
                sha1.update(chunk)
                sha224.update(chunk)
                sha256.update(chunk)
                sha512.update(chunk)
                sha384.update(chunk)
    except Exception as a:
        LOGGER.info(str(a))
        try: os.remove(file)
        except: pass
        return editMessage("Hashing error. Check Logs.", sent)
    # hash text
    finishedText = "🍆 File: <code>{}</code>\n".format(filename)
    finishedText += "🍓 MD5: <code>{}</code>\n".format(md5.hexdigest())
    finishedText += "🍌 SHA1: <code>{}</code>\n".format(sha1.hexdigest())
    finishedText += "🍒 SHA224: <code>{}</code>\n".format(sha224.hexdigest())
    finishedText += "🍑 SHA256: <code>{}</code>\n".format(sha256.hexdigest())
    finishedText += "🥭 SHA512: <code>{}</code>\n".format(sha512.hexdigest())
    finishedText += "🍎 SHA384: <code>{}</code>\n".format(sha384.hexdigest())
    timeTaken = f"🥚 Hash Time: <code>{TimeFormatter((time.time() - hashStartTime) * 1000)}</code>"
    editMessage(f"{timeTaken}\n{finishedText}", sent)
    try: os.remove(file)
    except: pass


hash_handler = CommandHandler(BotCommands.HashCommand, hash,
    filters=CustomFilters.authorized_chat | CustomFilters.authorized_user, run_async=True)
dispatcher.add_handler(hash_handler)