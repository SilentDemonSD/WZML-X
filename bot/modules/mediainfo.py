#!/usr/bin/env python3

import os
import re
import shlex
from aiofiles import open as aiopen, remove as aioremove, path as aiopath
from aiohttp import ClientSession
from pyrogram.handlers import MessageHandler 
from pyrogram.filters import command
from bot.helper.telegram_helper.filters import CustomFilters
from bot.helper.telegram_helper.bot_commands import BotCommands
from bot.helper.telegram_helper.message_utils import editMessage, sendMessage
from bot.helper.ext_utils.bot_utils import cmd_exec
from bot.helper.ext_utils.telegraph_helper import telegraph
from bot import LOGGER, bot, config_dict

# Define the path for MediaInfo files
MEDIAINFO_PATH = "Mediainfo/"

# Define a dictionary for different sections and their corresponding emojis
SECTION_DICT = {
    "General": "🔹",
    "Video": "🎥",
    "Audio": "🎶",
    "Text": "💬",
    "Image": "📷",
    "Other": "📦",
}

# This async function generates MediaInfo for the given link or media
async def generate_mediainfo(message, link=None, media=None, mmsg=None):
    # Send a message indicating that MediaInfo is being generated
    temp_send = await sendMessage(message, 'Generating MediaInfo...')

    try:
        # Create MediaInfo directory if it doesn't exist
        if not await aiopath.isdir(MEDIAINFO_PATH):
            await aiopath.mkdir(MEDIAINFO_PATH)

        # Download the file from the link or save the media file
        if link:
            filename = re.search(".+/(.+)", link).group(1)
            des_path = os.path.join(MEDIAINFO_PATH, filename)
            headers = {"user-agent": "Mozilla/5.0 (Linux; Android 12; 2201116PI) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/107.0.0.0 Mobile Safari/537.36"}
            async with ClientSession() as session:
                async with session.get(link, headers=headers) as response:
                    async with aiopen(des_path, "wb") as f:
                        async for chunk in response.content.iter_chunked(10000000):
                            await f.write(chunk)
                            break
        elif media:
            des_path = os.path.join(MEDIAINFO_PATH, media.file_name)
            if media.file_size <= 50000000:
                await mmsg.download(os.path.join(os.getcwd(), des_path))
            else:
                async for chunk in bot.stream_media(media, limit=5):
                    async with aiopen(des_path, "ab") as f:
                        await f.write(chunk)

        # Execute mediainfo command and parse the output
        stdout, _, _ = await cmd_exec(shlex.split(f'mediainfo "{des_path}"'))
        tc = f"<h4>📌 {os.path.basename(des_path)}</h4><br><br>"
        if len(stdout) != 0:
            tc += parse_info(stdout)
    except Exception as e:
        LOGGER.error(e)
        await editMessage(temp_send, f"MediaInfo Stopped due to {str(e)}")
    finally:
        await aioremove(des_path)

    # Create a Telegraph page with the parsed MediaInfo and send the link
    link_id = (await telegraph.create_page(title='MediaInfo X', content=tc))["path"]
    await temp_send.edit(f"<b>MediaInfo:</b>\n\n➲ <b>Link :</b> https://graph.org/{link_id}", disable_web_page_preview=False)

# This function parses the MediaInfo output and returns the formatted string
def parse_info(out):
    tc = ''
    trigger = False
    for line in out.split('\n'):
        for section, emoji in SECTION_DICT.items():
            if line.startswith(section):
                trigger = True
                if not line.startswith('General'):
                    tc += '</pre><br>'
                tc += f"<h4>{emoji} {line.replace('Text', 'Subtitle')}</h4>"
                break
        if trigger:
            tc += '<br><pre>'
            trigger = False
        else:
            tc += line + '\n'
    tc += '</pre><br>'
    return tc

# This async function handles the /mediainfo command
async def mediainfo(_, message):
    rply = message.reply_to_message
    help_msg = "<b>By replying to media:</b>"
    help_msg += f"\n<code>/{BotCommands.MediaInfoCommand[0]} or /{BotCommands.MediaInfoCommand[1]}" + " {media}" + "</code>"
    help_msg += "\n\n<b>By reply/sending download link:</b>"
    help_msg += f"\n<code>/{BotCommands.MediaInfoCommand[0]} or /{BotCommands.MediaInfoCommand[1]}" + " {link}" + "</code>"

    # Check if a media file or link is provided
    if len(message.command) > 1 or rply and rply.text:
        link = rply.text if rply else message.command[1]
        return await generate_mediainfo(message, link)
    elif rply:
        # Check if the replied message contains a file
        if file := next(
            (
                i
                for i in [
                    rply.document,
                    rply.video,
                    rply.audio,
                    rply.voice,
                    rply.animation,
                    rply.video_note,
                ]
                if i is not None
            ),
            None,
        ):
            return await generate_mediainfo(message, None, file, rply)
        else:
            # Send help message if no file is found
            return await sendMessage(message, help_msg)
    else:
        return await sendMessage(message, help_msg)

# Add the mediainfo function to the bot's message handler
bot.add_handler(MessageHandler(mediainfo, filters=command(BotCommands.MediaInfoCommand) & CustomFilters.authorized & ~CustomFilters.blacklisted))
