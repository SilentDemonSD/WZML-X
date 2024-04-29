import asyncio
from typing import Union

import pyrogram
from pyrogram.errors import exceptions
from pyrogram.handlers import MessageHandler
from pyrogram.filters import command

from bot import LOGGER
from bot.helper.telegram_helper.bot_utils import is_gdrive_link, sync_to_async
from bot.helper.telegram_helper.bot_commands import BotCommands
from bot.helper.telegram_helper.bot_init import bot
from bot.helper.telegram_helper.message_utils import sendMessage
from bot.helper.telegram_helper.filters import CustomFilters
from bot.helper.mirror_utils.upload_utils.gdriveTools import GoogleDriveHelper

async def deletefile(client: pyrogram.Client, context: pyrogram.Context) -> None:
    # Extract the link from the command arguments or the replied message
    args = context.args
    if len(args) > 0:
        link = args[0].strip()
    elif (reply_to := context.reply_to_message) and isinstance(reply_to, pyrogram.types.Message):
        link = reply_to.text.strip()
    else:
        link = ''

    # Check if the link is a Google Drive link
    if is_gdrive_link(link):
        LOGGER.info(link)
        # Initialize the Google Drive Helper class
        drive = GoogleDriveHelper()
        try:
            # Call the deletefile method of the class with the link
            msg = await sync_to_async(drive.deletefile, link)
        except exceptions.exceptions.bad_request_400.MessageNotModified:
            return
        except Exception as e:
            LOGGER.error(f'Error in deletefile method: {e}')
            msg = 'An error occurred while deleting the file. Please try again later.'
    else:
        # Return an error message if the link is not a Google Drive link
        msg = 'Send Gdrive link along with command or by replying to the link by command'
        LOGGER.warning(f'Link is not a Google Drive link: {link}')

    # Send the message and auto-delete the original message
    reply_message = await sendMessage(context.message, msg)
    try:
        await context.bot.delete_message(context.message.chat.id, context.message.id)
    except exceptions.exceptions.bad_request_400.MessageNotModified:
        pass


# Add the deletefile function as a message handler for the DeleteCommand
bot.add_handler(MessageHandler(deletefile, filters=command(
    BotCommands.DeleteCommand) & CustomFilters.authorized & ~CustomFilters.blacklisted))

