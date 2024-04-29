#!/usr/bin/env python3

import asyncio
from typing import Union

import pyrogram
from pyrogram.handlers import MessageHandler
from pyrogram.filters import command

from bot import bot, LOGGER
from bot.helper.telegram_helper.message_utils import auto_delete_message, sendMessage
from bot.helper.telegram_helper.filters import CustomFilters
from bot.helper.telegram_helper.bot_commands import BotCommands
from bot.helper.mirror_utils.upload_utils.gdriveTools import GoogleDriveHelper
from bot.helper.ext_utils.bot_utils import is_gdrive_link

@asyncio.coroutine
def deletefile(client: pyrogram.Client, message: pyrogram.Message) -> None:
    # Extract the link from the command arguments or the replied message
    args = message.text.split()
    if len(args) > 1:
        link = args[1]
    elif (reply_to := message.reply_to_message) and isinstance(reply_to, pyrogram.types.Message):
        link = reply_to.text.split(maxsplit=1)[0].strip()
    else:
        link = ''

    # Check if the link is a Google Drive link
    if is_gdrive_link(link):
        LOGGER.info(link)
        # Initialize the Google Drive Helper class
        drive = GoogleDriveHelper()
        try:
            # Call the deletefile method of the class with the link
            msg = yield from sync_to_async(drive.deletefile, link)
        except Exception as e:
            LOGGER.error(f'Error in deletefile method: {e}')
            msg = 'An error occurred while deleting the file. Please try again later.'
    else:
        # Return an error message if the link is not a Google Drive link
        msg = 'Send Gdrive link along with command or by replying to the link by command'
        LOGGER.warning(f'Link is not a Google Drive link: {link}')

    # Send the message and auto-delete the original message
    reply_message = yield from sendMessage(message, msg)
    yield from auto_delete_message(message, reply_message)


# Add the deletefile function as a message handler for the DeleteCommand
bot.add_handler(MessageHandler(deletefile, filters=command(
    BotCommands.DeleteCommand) & CustomFilters.authorized & ~CustomFilters.blacklisted))

