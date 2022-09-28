from threading import Thread
import time
from charset_normalizer import logging
from speedtest import Speedtest
from bot.helper.ext_utils.bot_utils import get_readable_time
from telegram.ext import CommandHandler
from bot.helper.telegram_helper.filters import CustomFilters
from bot import dispatcher, botStartTime
from bot.helper.telegram_helper.bot_commands import BotCommands
from bot.helper.telegram_helper.message_utils import auto_delete_message, sendMessage, deleteMessage, sendPhoto, editMessage

def speedtest(update, context):
    speed = sendMessage("Running Speed Test. Wait about 20 secs.", context.bot, update.message)
    test = Speedtest()
    test.get_best_server()
    test.download()
    test.upload()
    test.results.share()
    result = test.results.dict()
    path = (result['share'])
    currentTime = get_readable_time(time.time() - botStartTime)
    string_speed = f'''
<b>Server</b>
<b>Name:</b> <code>{result['server']['name']}</code>
<b>Country:</b> <code>{result['server']['country']}, {result['server']['cc']}</code>
<b>Sponsor:</b> <code>{result['server']['sponsor']}</code>
<b>ISP:</b> <code>{result['client']['isp']}</code>

<b>SpeedTest Results</b>
<b>Upload:</b> <code>{speed_convert(result['upload'], False)}</code>
<b>Download:</b>  <code>{speed_convert(result['download'], False)}</code>
<b>Ping:</b> <code>{result['ping']} ms</code>
<b>ISP Rating:</b> <code>{result['client']['isprating']}</code>
<b>Bot Uptime:</b> <code>{currentTime}</code>
'''
    try:
        pho = sendPhoto(text=string_speed, bot=context.bot, message=update.message, photo=path)
        deleteMessage(context.bot, speed)
        Thread(target=auto_delete_message, args=(context.bot, update.message, pho)).start()
    except Exception as g:
        logging.error(str(g))
        editMessage(string_speed, speed)
        Thread(target=auto_delete_message, args=(context.bot, update.message, speed)).start()

def speed_convert(size, byte=True):
    """Hi human, you can't read bytes?"""
    if not byte: size = size / 8 # byte or bit ?
    power = 2 ** 10
    zero = 0
    units = {0: "B/s", 1: "KB/s", 2: "MB/s", 3: "GB/s", 4: "TB/s"}
    while size > power:
        size /= power
        zero += 1
    return f"{round(size, 2)} {units[zero]}"


speed_handler = CommandHandler(BotCommands.SpeedCommand, speedtest,
    CustomFilters.authorized_chat | CustomFilters.authorized_user, run_async=True)

dispatcher.add_handler(speed_handler)