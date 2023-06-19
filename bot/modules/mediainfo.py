#!/usr/bin/env python3
import aiohttp
from re import search as re_search
from shlex import split as ssplit
from aiofiles import open as aiopen
from aiofiles.os import remove as aioremove, path as aiopath, mkdir
from os import path as ospath, getcwd

from pyrogram.handlers import MessageHandler 
from pyrogram.filters import command

from bot import LOGGER, bot, config_dict
from bot.helper.telegram_helper.filters import CustomFilters
from bot.helper.telegram_helper.bot_commands import BotCommands
from bot.helper.telegram_helper.message_utils import editMessage, sendMessage
from bot.helper.ext_utils.bot_utils import cmd_exec
from bot.helper.ext_utils.telegraph_helper import telegraph


async def telegram_mediainfo(message, media, mmsg):
    temp_send = await sendMessage(message, '<i>Generating MediaInfo...</i>')
    try:
        path = "Mediainfo/"
        if not await aiopath.isdir(path):
            await mkdir(path)
        des_path = ospath.join(path, media.file_name)
        if media.file_size <= 50000000:
            await mmsg.download(ospath.join(getcwd(), des_path))
        else:
            async for chunk in bot.stream_media(media, limit=5):
                async with aiopen(des_path, "ab") as f:
                    await f.write(chunk)
        stdout, stderr, _ = await cmd_exec(ssplit(f'mediainfo "{des_path}"'))
        tele_content = f"<h4>{ospath.basename(des_path)}</h4><br><br>"
        if len(stdout) != 0:
            tele_content += f"<br><br><pre>{stdout}</pre><br>"
        if len(stderr) != 0:
            tele_content += f"<br><br><pre>{stderr}</pre>"
    except Exception as e:
        LOGGER.error(e)
        await editMessage(temp_send, f"MediaInfo Stopped due to {str(e)}")
    finally:
        await aioremove(des_path)
    link_id = (await telegraph.create_page(title='MediaInfo', content=tele_content))["path"]
    await editMessage(temp_send, f"<b>MediaInfo:</b> https://graph.org/{link_id}")

async def ddl_mediainfo(message, link):
    temp_send = await sendMessage(message, '<i>Generating MediaInfo...</i>')
    try:
        path = "Mediainfo/"
        if not await aiopath.isdir(path):
            await mkdir(path)
        filename = re_search(".+/(.+)", link).group(1)
        if len(filename) > 60:
            filename = filename[-60:]
        des_path = ospath.join(path, filename)
        headers = {"user-agent":"Mozilla/5.0 (Linux; Android 12; 2201116PI) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/107.0.0.0 Mobile Safari/537.36"}
        async with aiohttp.ClientSession() as session:
            async with session.get(link, headers=headers) as response:
                async with aiopen(des_path, "wb") as f:
                    async for chunk in response.content.iter_any(10000000):
                        await f.write(chunk)
                        break
        stdout, stderr, _ = await cmd_exec(ssplit(f'mediainfo "{des_path}"'))
        tele_content = f"<h4>{ospath.basename(des_path)}</h4><br><br>"
        if len(stdout) != 0:
            tele_content += f"<br><br><pre>{stdout}</pre><br>"
        if len(stderr) != 0:
            tele_content += f"<br><br><pre>{stderr}</pre>"
    except Exception as e:
        LOGGER.error(e)
        await editMessage(temp_send, f"MediaInfo Stopped due to {str(e)}")
    finally:
        await aioremove(des_path)
    link_id = (await telegraph.create_page(title='MediaInfo', content=tele_content))["path"]
    await editMessage(temp_send, f"<b>MediaInfo:</b> https://graph.org/{link_id}")


async def mediainfo(_, message):
    help_msg = "<b>By replying to message (including media):</b>"
    help_msg += f"\n<code>/{BotCommands.MediaInfoCommand}" + " {message}" + "</code>"
    help_msg = "\n\n<b>By sending link beside the command:</b>"
    help_msg += f"\n<code>/{BotCommands.MediaInfoCommand}" + " {link}" + "</code>"
    if len(message.command) > 1:
        link = message.command[1]
        return await ddl_mediainfo(message, link)
    elif (mediamessage := message.reply_to_message) and not mediamessage.text:
        file = next((i for i in [mediamessage.document, mediamessage.video, mediamessage.audio, mediamessage.photo, mediamessage.voice,
                         mediamessage.animation, mediamessage.video_note] if i is not None), None)
        if not file:
            return await sendMessage(message, help_msg)
        return await telegram_mediainfo(message, file, mediamessage)
    else:
        return await sendMessage(message, help_msg)

bot.add_handler(MessageHandler(mediainfo, filters=command(BotCommands.MediaInfoCommand) & CustomFilters.authorized))
