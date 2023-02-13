from time import time
from charset_normalizer import logging
from speedtest import Speedtest
from bot.helper.ext_utils.bot_utils import get_readable_time
from pyrogram import filters, Client
from pyrogram.types import Message
from bot.helper.telegram_helper.filters import CustomFilters
from bot import bot, botStartTime, main_loop
from bot.helper.telegram_helper.bot_commands import BotCommands
from bot.helper.telegram_helper.message_utils import auto_delete_message, sendMessage, deleteMessage, sendPhoto, editMessage
from bot.helper.ext_utils.bot_utils import get_readable_file_size

@bot.on_message(filters.command(BotCommands.SpeedCommand) & (CustomFilters.authorized_chat | CustomFilters.authorized_user))
async def speedtest(c: Client, message: Message):
    speed = await sendMessage("Running Speed Test. Wait about some secs.", c, message)
    test = Speedtest()
    test.get_best_server()
    test.download()
    test.upload()
    test.results.share()
    result = test.results.dict()
    path = (result['share'])
    currentTime = get_readable_time(time() - botStartTime)
    string_speed = f'''
╭─《 🚀 SPEEDTEST INFO 》
├ <b>Upload:</b> <code>{speed_convert(result['upload'], False)}</code>
├ <b>Download:</b>  <code>{speed_convert(result['download'], False)}</code>
├ <b>Ping:</b> <code>{result['ping']} ms</code>
├ <b>Time:</b> <code>{result['timestamp']}</code>
├ <b>Data Sent:</b> <code>{get_readable_file_size(int(result['bytes_sent']))}</code>
╰ <b>Data Received:</b> <code>{get_readable_file_size(int(result['bytes_received']))}</code>

╭─《 🌐 SPEEDTEST SERVER 》
├ <b>Name:</b> <code>{result['server']['name']}</code>
├ <b>Country:</b> <code>{result['server']['country']}, {result['server']['cc']}</code>
├ <b>Sponsor:</b> <code>{result['server']['sponsor']}</code>
├ <b>Latency:</b> <code>{result['server']['latency']}</code>
├ <b>Latitude:</b> <code>{result['server']['lat']}</code>
╰ <b>Longitude:</b> <code>{result['server']['lon']}</code>

╭─《 👤 CLIENT DETAILS 》
├ <b>IP Address:</b> <code>{result['client']['ip']}</code>
├ <b>Latitude:</b> <code>{result['client']['lat']}</code>
├ <b>Longitude:</b> <code>{result['client']['lon']}</code>
├ <b>Country:</b> <code>{result['client']['country']}</code>
├ <b>ISP:</b> <code>{result['client']['isp']}</code>
╰ <b>ISP Rating:</b> <code>{result['client']['isprating']}</code>
'''
    try:
        pho = await sendPhoto(text=string_speed, bot=c, message=message, photo=path)
        await deleteMessage(c, speed)
        main_loop.create_task(auto_delete_message(c, message, pho))
    except Exception as g:
        logging.error(str(g))
        await editMessage(string_speed, speed)
        main_loop.create_task(auto_delete_message(c, message, speed))

def speed_convert(size, byte=True):
    if not byte: size = size / 8
    power = 2 ** 10
    zero = 0
    units = {0: "B/s", 1: "KB/s", 2: "MB/s", 3: "GB/s", 4: "TB/s"}
    while size > power:
        size /= power
        zero += 1
    return f"{round(size, 2)} {units[zero]}"
