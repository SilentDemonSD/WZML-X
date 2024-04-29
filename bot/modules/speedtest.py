#!/usr/bin/env python3
import asyncio
import os
from urllib.parse import urlparse

import aiohttp
import requests
from PIL import Image
from pyrogram.handlers import MessageHandler
from pyrogram.filters import command
from speedtest import Speedtest

from bot import bot, LOGGER, SUPPORT_CHAT, WHITELIST_CHATS
from bot.helper.telegram_helper.filters import CustomFilters
from bot.helper.telegram_helper.bot_commands import BotCommands
from bot.helper.telegram_helper.message_utils import sendMessage, deleteMessage, editMessage
from bot.helper.ext_utils.bot_utils import get_readable_file_size, new_task

@new_task
async def speedtest(_, message):
    speed = await sendMessage(message, "<i>Initializing Speedtest...</i>")
    test = Speedtest()
    test.get_best_server()
    test.download()
    test.upload()
    test.results.share()
    result = test.results.dict()
    path = result['share']
    string_speed = f'''
➲ <b><i>SPEEDTEST INFO</i></b>
┠ <b>Upload:</b> <code>{get_readable_file_size(result['upload'] / 8)}/s</code>
┠ <b>Download:</b>  <code>{get_readable_file_size(result['download'] / 8)}/s</code>
┠ <b>Ping:</b> <code>{result['ping']} ms</code>
┠ <b>Time:</b> <code>{result['timestamp']}</code>
┠ <b>Data Sent:</b> <code>{get_readable_file_size(int(result['bytes_sent']))}</code>
┖ <b>Data Received:</b> <code>{get_readable_file_size(int(result['bytes_received']))}</code>

➲ <b><i>SPEEDTEST SERVER</i></b>
┠ <b>Name:</b> <code>{result['server']['name']}</code>
┠ <b>Country:</b> <code>{result['server']['country']}, {result['server']['cc']}</code>
┠ <b>Sponsor:</b> <code>{result['server']['sponsor']}</code>
┠ <b>Latency:</b> <code>{result['server']['latency']}</code>
┠ <b>Latitude:</b> <code>{result['server']['lat']}</code>
┖ <b>Longitude:</b> <code>{result['server']['lon']}</code>

➲ <b><i>CLIENT DETAILS</i></b>
┠ <b>IP Address:</b> <code>{result['client']['ip']}</code>
┠ <b>Latitude:</b> <code>{result['client']['lat']}</code>
┠ <b>Longitude:</b> <code>{result['client']['lon']}</code>
┠ <b>Country:</b> <code>{result['client']['country']}</code>
┠ <b>ISP:</b> <code>{result['client']['isp']}</code>
┖ <b>ISP Rating:</b> <code>{result['client']['isprating']}</code>
'''
    try:
        # Download the image using aiohttp
        async with aiohttp.ClientSession() as session:
            async with session.get(path) as resp:
                if resp.status != 200:
                    LOGGER.error(f"Failed to download image: {resp.status}")
                    return
                jpg_data = await resp.read()

        # Save the image temporarily
        temp_file = "temp_image.jpg"
        with open(temp_file, "wb") as f:
            f.write(jpg_data)

        # Convert the image to a Telegram-friendly format
        image = Image.open(temp_file)
        img_bytes = await convert_image_to_telegram_format(image)

        # Send the message with the image
        pho = await sendMessage(message, string_speed, photo=img_bytes)
        os.remove(temp_file)
        await deleteMessage(speed)
    except Exception as e:
        LOGGER.error(str(e))
        pho = await editMessage(speed, string_speed)


async def convert_image_to_telegram_format(image):
    """Convert the image to a format suitable for sending via Telegram."""
    img_bytes = await loop.run_in_executor(None, functools.partial(image.tobytes))
    img_data = io.BytesIO(img_bytes)
    img_data.seek(0)
    return img_data


bot.add_handler(MessageHandler(speedtest, filters=command(
    BotCommands.SpeedCommand) & CustomFilters.authorized & ~CustomFilters.blacklisted))
