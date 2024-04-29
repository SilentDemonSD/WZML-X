#!/usr/bin/env python3
from pyrogram.handlers import MessageHandler
from pyrogram.filters import command
from pyrogram.errors import UserAlreadyParticipant
from typing import Union

from bot import bot, LOGGER
from bot.helper.telegram_helper.message_utils import auto_delete_message, sendMessage
from bot.helper.telegram_helper.filters import CustomFilters
from bot.helper.telegram_helper.bot_commands import BotCommands
from bot.helper.mirror_utils.upload_utils.gdriveTools import GoogleDriveHelper
from bot.helper.ext_utils.bot_utils import is_gdrive_link, sync_to_async, new_task


@new_task
async def deletefile(message: telegram.Message) -> None:
    args = message.text.split()
    link: str = ''
    if len(args) > 1:
        link = args[1]
    elif (reply_to := message.reply_to_message) and reply_to.text:
        link = reply_to.text.split(maxsplit=1)[0].strip()
    if is_gdrive_link(link):
        LOGGER.info(link)
        drive = GoogleDriveHelper()
        try:
            await sync_to_async(drive.deletefile, link)
            msg = 'File deleted successfully.'
        except Exception as e:
            msg = f'Error deleting file: {str(e)}'
    else:
        msg = 'Send Gdrive link along with command or by replying to the link by command'
    reply_message = await sendMessage(message, msg)
    await auto_delete_message(message, reply_message)


bot.add_handler(MessageHandler(deletefile, filters=command(
    BotCommands.DeleteCommand) & CustomFilters.authorized & ~CustomFilters.blacklisted))
