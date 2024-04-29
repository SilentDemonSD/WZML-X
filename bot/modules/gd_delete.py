import asyncio
import logging
import sys
from typing import Union

import pyrogram
from pyrogram.errors import exceptions, AbleToDelete, UserIsBlocked, ChatWriteForbidden, UserDeactivated, UserBannedInChannel, FloodWait
from pyrogram.raw import functions, inputs

from bot import LOGGER
from bot.helper.telegram_helper.bot_utils import is_gdrive_link, sync_to_async
from bot.helper.telegram_helper.bot_commands import BotCommands
from bot.helper.telegram_helper.bot_init import initialize_bot
from bot.helper.telegram_helper.message_utils import sendMessage
from bot.helper.telegram_helper.filters import CustomFilters
from bot.helper.mirror_utils.upload_utils.gdriveTools import GoogleDriveHelper

async def deletefile(client: pyrogram.Client, context: pyrogram.Context) -> None:
    """
    Delete a file from Google Drive.

    Args:
        client (pyrogram.Client): The Pyrogram client object.
        context (pyrogram.Context): The Pyrogram context object.

    Returns:
        None
    """
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
        try:
            # Initialize the Google Drive Helper class
            async with GoogleDriveHelper() as drive:
                # Call the deletefile method of the class with the link
                result = await sync_to_async(drive.deletefile, link)
                if result:
                    await sendMessage(context.message, 'File deleted successfully.')
                else:
                    await sendMessage(context.message, 'File not found or already deleted.')
        except exceptions.exceptions.bad_request_400.MessageNotModified:
            return
        except exceptions.exceptions.forbidden_403.PeerIdInvalid:
            return
        except FloodWait as e:
            await asyncio.sleep(e.x)
        except UserIsBlocked:
            return
        except ChatWriteForbidden:
            return
        except UserDeactivated:
            return
        except UserBannedInChannel:
            return
        except Exception as e:
            LOGGER.error(f'Error in deletefile method: {e}')
            await sendMessage(context.message, 'An error occurred while deleting the file. Please try again later.')
    else:
        # Return an error message if the link is not a Google Drive link
        await sendMessage(context.message, 'Send Gdrive link along with command or by replying to the link by command')
        LOGGER.warning(f'Link is not a Google Drive link: {link}')

    # Auto-delete the original message
    try:
        await asyncio.sleep(1)
        message = context.message
        if not await sync_to_async(message.delete, timeout=30):
            if not await sync_to_async(message.chat.permissions.can_delete_messages, timeout=30):
                await sendMessage(message.chat, 'I do not have permission to delete messages in this chat.')
    except AbleToDelete:
        pass
    except FloodWait as e:
        await asyncio.sleep(e.x)
    except exceptions.exceptions.forbidden_403.PeerIdInvalid:
        pass
    except exceptions.exceptions.user.UserDeactivated:
        pass
    except exceptions.exceptions.channel.UserBannedInChannel:
        pass

if __name__ == '__main__':
    try:
        client, start_time = initialize_bot()
    except Exception as e:
        LOGGER.error(f'Client initialization failed: {e}')
        sys.exit(1)

    # Add the deletefile function as a message handler for the DeleteCommand
    bot.add_handler(MessageHandler(deletefile, filters=command(
        BotCommands.DeleteCommand) & CustomFilters.authorized & ~CustomFilters.blacklisted))

    app.run()
