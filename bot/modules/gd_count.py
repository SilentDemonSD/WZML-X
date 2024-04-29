import asyncio
from pyrogram.handlers import MessageHandler
from pyrogram.filters import command
from bot.helper.mirror_utils.upload_utils.gdriveTools import GoogleDriveHelper
from bot.helper.telegram_helper.message_utils import deleteMessage, sendMessage
from bot.helper.telegram_helper.filters import CustomFilters
from bot.helper.telegram_helper.bot_commands import BotCommands
from bot.helper.ext_utils.bot_utils import is_gdrive_link, sync_to_async, new_task, get_readable_file_size
from bot.helper.themes import BotTheme

@new_task
async def count_node(_, message):
    """
    This function is responsible for counting the number of files and folders in a Google Drive folder.
    :param _: Underscore is used to represent the first parameter which is usually self in object-oriented programming
    :param message: The received message object from Telegram
    """
    args = message.text.split()  # Split the received message into a list of arguments

    # Extract the username and mention of the user
    tag = f"@{message.from_user.username}" if (username := message.from_user.username) else message.from_user.mention

    link = args[1] if len(args) > 1 else ''  # Get the link from the arguments

    # If the link is not provided directly, try to get it from the replied message
    if len(link) == 0 and (reply_to := message.reply_to_message):
        link = reply_to.text.strip()

    # Check if the provided link is a Google Drive link
    if is_gdrive_link(link):
        msg = await sendMessage(message, BotTheme('COUNT_MSG', LINK=link))  # Inform the user that the process has started

        gd = GoogleDriveHelper()  # Initialize the Google Drive helper
        name, mime_type, size, files, folders = await sync_to_async(gd.count, link)  # Count the files and folders

        # Delete the initial message and send the results
        await deleteMessage(msg)
        msg = BotTheme('COUNT_NAME', COUNT_NAME=name)
        msg += BotTheme('COUNT_SIZE', COUNT_SIZE=get_readable_file_size(size))
        msg += BotTheme('COUNT_TYPE', COUNT_TYPE=mime_type)

        # If the link is a folder, display the number of files and folders
        if mime_type == 'Folder':
            msg += BotTheme('COUNT_SUB', COUNT_SUB=folders)
            msg += BotTheme('COUNT_FILE', COUNT_FILE=files)

        msg += BotTheme('COUNT_CC', COUNT_CC=tag)
        await sendMessage(message, msg, photo='IMAGES')

    else:
        msg = 'Send Gdrive link along with command or by replying to the link by command'  # Inform the user that the provided link is not a Google Drive link
        await sendMessage(message, msg, photo='IMAGES')

bot.add_handler(MessageHandler(count_node, filters=command(BotCommands.CountCommand) & CustomFilters.authorized & ~CustomFilters.blacklisted))
