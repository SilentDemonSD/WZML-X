from pyrogram import filters, Client
from pyrogram.types import Message

from bot import bot, main_loop
from bot.helper.mirror_utils.upload_utils.gdriveTools import GoogleDriveHelper
from bot.helper.telegram_helper.message_utils import deleteMessage, sendMessage
from bot.helper.telegram_helper.filters import CustomFilters
from bot.helper.telegram_helper.bot_commands import BotCommands
from bot.helper.ext_utils.bot_utils import is_gdrive_link


@bot.on_message(filters.command(BotCommands.CountCommand) & (CustomFilters.authorized_chat | CustomFilters.authorized_user))
async def countNode(c: Client, message: Message):
    args = message.text.split()
    reply_to = message.reply_to_message
    link = ''
    tag = ''
    if len(args) > 1:
        link = args[1].strip()
        if message.from_user.username:
            tag = f"@{message.from_user.username}"
        else:
            tag = message.from_user.mention(
                message.from_user.first_name, style='html')
    if reply_to:
        if len(link) == 0:
            link = reply_to.text.split(maxsplit=1)[0].strip()
        if reply_to.from_user.username:
            tag = f"@{reply_to.from_user.username}"
        else:
            tag = reply_to.from_user.mention(
                reply_to.from_user.first_name, style='html')
    if is_gdrive_link(link):
        msg = await sendMessage(f"Counting: <code>{link}</code>", c, message)
        gd = GoogleDriveHelper()
        # result = gd.count(link)
        result = await main_loop.create_task(gd.count(link))
        await deleteMessage(c, msg)
        cc = f'\n<b>╰👤 cc: </b>{tag}'
        await sendMessage(result + cc, c, message)
    else:
        msg = 'Send Gdrive link along with command or by replying to the link by command'
        await sendMessage(msg, c, message)

