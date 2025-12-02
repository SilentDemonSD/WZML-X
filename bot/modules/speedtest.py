#!/usr/bin/env python3
from speedtest import Speedtest, ConfigRetrievalError
from pyrogram.handlers import MessageHandler
from pyrogram.filters import command

from bot import bot, LOGGER
from bot.helper.telegram_helper.filters import CustomFilters
from bot.helper.telegram_helper.bot_commands import BotCommands
from bot.helper.telegram_helper.message_utils import (
    sendMessage,
    deleteMessage,
    editMessage,
)
from bot.helper.ext_utils.bot_utils import get_readable_file_size, new_task


@new_task
async def speedtest(_, message):
    speed = await sendMessage(message, "<i>Initiating Speedtest...</i>")
    try:
        test = Speedtest()
    except ConfigRetrievalError:
        await editMessage(
            speed,
            "<b>ERROR:</b> <i>Can't connect to Server at the Moment, Try Again Later !</i>",
        )
        return

    test.get_best_server()
    test.download()
    test.upload()
    test.results.share()

    result = test.results.dict()
    path = result["share"]

    string_speed = f"""
<b><i>⚡ SPEEDTEST RESULT</i></b>

<b>📤 Upload:</b> <code>{get_readable_file_size(result['upload'] / 8)}/s</code>
<b>📥 Download:</b> <code>{get_readable_file_size(result['download'] / 8)}/s</code>
<b>🏓 Ping:</b> <code>{result['ping']} ms</code>
<b>⏱ Time:</b> <code>{result['timestamp']}</code>
<b>📊 Data Sent:</b> <code>{get_readable_file_size(int(result['bytes_sent']))}</code>
<b>📊 Data Received:</b> <code>{get_readable_file_size(int(result['bytes_received']))}</code>

<b><i>🌐 SPEEDTEST SERVER</i></b>
<b>🏠 Name:</b> <code>{result['server']['name']}</code>
<b>🇨🇺 Country:</b> <code>{result['server']['country']} ({result['server']['cc']})</code>
<b>🎯 Sponsor:</b> <code>{result['server']['sponsor']}</code>
<b>⚡ Latency:</b> <code>{result['server']['latency']}</code>
<b>📌 Coordinates:</b> <code>{result['server']['lat']}, {result['server']['lon']}</code>
"""

    try:
        pho = await sendMessage(message, string_speed, photo=path)
        await deleteMessage(speed)
    except Exception as e:
        LOGGER.error(str(e))
        await editMessage(speed, string_speed)


bot.add_handler(
    MessageHandler(
        speedtest,
        filters=command(BotCommands.SpeedCommand)
        & CustomFilters.authorized
        & ~CustomFilters.blacklisted,
    )
)