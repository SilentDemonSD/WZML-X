#!/usr/bin/env python3
import os
import re
import shlex
from asyncio import sleep
from pathlib import Path

import aiohttp
from aiofiles import open as aio_open
from aiofiles.os import remove as aio_remove, mkdir
from pyrogram.handlers import MessageHandler
from pyrogram.filters import command
from pyrogram.errors import MediaEmpty, MediaForbidden, MessageNotModified
from bot.helper.telegram_helper.filters import CustomFilters
from bot.helper.telegram_helper.bot_commands import BotCommands
from bot.helper.telegram_helper.message_utils import editMessage, sendMessage
from bot.helper.ext_utils.bot_utils import cmd_exec
from bot.helper.ext_utils.telegraph_helper import telegraph

MEDIA_INFO_PATH = "Mediainfo/"

async def download_file(session, url, file_path):
    async with session.get(url, allow_redirects=True) as response:
        if response.status != 200:
            raise Exception(f"Failed to download file: {response.status}")
        if not response.headers.get("Content-Length"):
            raise Exception("Content-Length header not found")
        content_length = int(response.headers["Content-Length"])
        total_received = 0
        with Path(file_path).open("wb") as f:
            while True:
                chunk = await response.content.read(10000000)
                if not chunk:
                    break
                total_received += len(chunk)
                f.write(chunk)
                await sleep(0.1)
                if total_received >= content_length:
                    break

async def gen_mediainfo(message, link=None, media=None, mmsg=None):
    temp_send = await sendMessage(message, "Generating MediaInfo...")
    try:
        if link:
            filename = re.search(".+/(.+)", link).group(1)
            des_path = os.path.join(MEDIA_INFO_PATH, filename)
            if not os.path.exists(MEDIA_INFO_PATH):
                os.makedirs(MEDIA_INFO_PATH)
            async with aiohttp.ClientSession() as session:
                await download_file(session, link, des_path)
        elif media:
            des_path = os.path.join(MEDIA_INFO_PATH, media.file_name)
            if media.file_size <= 50000000:
                await mmsg.download(os.path.join(os.getcwd(), des_path))
            else:
                async with aiohttp.ClientSession() as session:
                    with Path(des_path).open("wb") as f:
                        async for chunk in bot.stream_media(media, limit=5):
                            f.write(chunk)
        stdout, _ = await cmd_exec(shlex.split(f"mediainfo '{des_path}'"))
        tc = f"<h4>📌 {os.path.basename(des_path)}</h4><br><br>"
        if stdout:
            tc += parseinfo(stdout)
    except Exception as e:
        LOGGER.error(e)
        await editMessage(temp_send, f"MediaInfo Stopped due to {str(e)}")
    finally:
        if os.path.exists(des_path):
            os.remove(des_path)
    link_id = (await telegraph.create_page(title="MediaInfo X", content=tc))["path"]
    await temp_send.edit(
        f"<b>MediaInfo:</b>\n\n➲ <b>Link :</b> https://graph.org/{link_id}",
        disable_web_page_preview=False,
    )

def parseinfo(out):
    tc = ""
    trigger = False
    for line in out.split("\n"):
        for section, emoji in SECTION_DICT.items():
            if line.startswith(section):
                trigger = True
                if section != "General":
                    tc += "</pre><br>"
                tc += f"<h4>{emoji} {line.replace('Text', 'Subtitle')}</h4>"
                break
        if trigger:
            tc += "<br><pre>"
            trigger = False
        else:
            tc += line + "\n"
    tc += "</pre><br>"
    return tc

async def mediainfo(_, message):
    rply = message.reply_to_message
    help_msg = (
        "<b>By replying to media:</b>\n"
        f"<code>/{BotCommands.MediaInfoCommand[0]} or /{BotCommands.MediaInfoCommand[1]} "
        "{media}</code>\n\n"
        "<b>By reply/sending download link:</b>\n"
        f"<code>/{BotCommands.MediaInfoCommand[0]} or /{BotCommands.MediaInfoCommand[1]} "
        "{link}</code>"
    )
    if len(message.command) > 1 or rply and rply.text:
        link = rply.text if rply else message.command[1]
        return await gen_mediainfo(message, link)
    elif rply:
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
            return await gen_mediainfo(message, None, file, rply)
        else:
            return await sendMessage(message, help_msg)
    else:
        return await sendMessage(message, help_msg)

bot.add_handler(
    MessageHandler(
        mediainfo,
        filters=command(BotCommands.MediaInfoCommand)
        & CustomFilters.authorized
        & ~CustomFilters.blacklisted,
    )
)
