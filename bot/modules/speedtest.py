#!/usr/bin/env python3

import os
import asyncio
import sys
from typing import Any, Coroutine, Optional
from pathlib import Path

import speedtest
from pyrogram.handlers import MessageHandler
from pyrogram.filters import command
from pyrogram.errors import ConfigRetrievalError

from bot import bot, LOGGER
from bot.helper.telegram_helper.filters import CustomFilters
from bot.helper.telegram_helper.bot_commands import BotCommands
from bot.helper.telegram_helper.message_utils import sendMessage, deleteMessage, editMessage
from bot.helper.ext_utils.bot_utils import get_readable_file_size, new_task

async def speedtest(_, message: Any) -> Optional[Coroutine[Any, Any, Any]]:
    """
    Initiates a speedtest and sends the results to the user.
    """
    speed = await sendMessage(message, "<i>Initiating Speedtest...</i>")
    try:
        test = Speedtest()
    except ConfigRetrievalError:
        await editMessage(speed, "<b>ERROR:</b> <i>Can't connect to Server at the Moment, Try Again Later !</i>")
        return
    test.get_best_server()
    test.download()
    test.upload()
    test.results.share()
    result = test.results.dict()
    path = Path(result['share'])
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
        result_message = await sendMessage(message, string_speed, photo=path)
        await deleteMessage(speed)
    except Exception as e:
        LOGGER.error(str(e))
        try:
            await editMessage(speed, string_speed)
        except Exception as e:
            LOGGER.error(str(e))

async def main():
    try:
        bot.add_handler(MessageHandler(speedtest, filters=command(
            BotCommands.SpeedCommand) & CustomFilters.authorized & ~CustomFilters.blacklisted))
    except Exception as e:
        LOGGER.error(str(e))

    try:
        await new_task(bot.start())
        await bot.idle()
    except KeyboardInterrupt:
        await bot.stop()

if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
