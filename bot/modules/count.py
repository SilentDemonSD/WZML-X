from telegram.ext import CommandHandler
from typing import Union

from bot import dispatcher
from bot.helper.mirror_utils.upload_utils.gdriveTools import GoogleDriveHelper
from bot.helper.telegram_helper.message_utils import deleteMessage, sendMessage
from bot.helper.telegram_helper.filters import CustomFilters
from bot.helper.telegram_helper.bot_commands import BotCommands
from bot.helper.ext_utils.bot_utils import is_gdrive_link, new_thread

@new_thread
def count_node(update: telegram.Update, context: telegram.ext.CallbackContext) -> None:
    reply_to = update.message.reply_to_message
    link = ""

    if len(context.args) == 1:
        link = context.args[0]

    if reply_to:
        link = reply_to.text.split(maxsplit=1)[0].strip() if link == "" else link

    if is_gdrive_link(link):
        tag = (
            f"@{update.message.from_user.username}"
            if update.message.from_user.username
            else update.message.from_user.mention_html(update.message.from_user.first_name)
        )

        msg = sendMessage(f"Counting: <code>{link}</code>", context.bot, update.message)

        try:
            gd = GoogleDriveHelper()
            result = gd.count(link)
            deleteMessage(context.bot, msg)
            sendMessage(f"{result}\n<b>Count By:</b> {tag}", context.bot, update.message)
        except Exception as e:
            deleteMessage(context.bot, msg)
            sendMessage(str(e), context.bot, update.message)
    else:
        sendMessage("Send Gdrive link along with command or by replying to the link by command", context.bot, update.message)

count_handler = CommandHandler(BotCommands.CountCommand, count_node, filters=CustomFilters.authorized_chat | CustomFilters.authorized_user)

dispatcher.add_handler(count_handler)
