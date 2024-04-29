from threading import Thread
from time import time
from charset_normalizer import logging
from speedtest import Speedtest
from bot.helper.ext_utils.bot_utils import get_readable_time
from telegram.ext import CommandHandler
from bot.helper.telegram_helper.filters import CustomFilters
from bot import dispatcher, botStartTime
from bot.helper.telegram_helper.bot_commands import BotCommands
from bot.helper.telegram_helper.message_utils import auto_delete_message, sendMessage, deleteMessage, sendPhoto, editMessage
from bot.helper.ext_utils.bot_utils import get_readable_file_size

def speedtest(update: telegram.Update, context: telegram.ext.CallbackContext) -> None:
    """Runs a speed test and sends the results to the user."""
    speed = sendMessage("Running Speed Test. Wait about some secs.", context.bot, update.message)
    test = Speedtest()
    test.get_best_server()
    test.download()
    test.upload()
    try:
        test.results.share()
    except Exception:
        result = test.results.dict()
    else:
        result = test.results.share()
    currentTime = get_readable_time(time() - botStartTime)
    if 'upload' not in result or 'download' not in result:
        sendMessage("An error occurred while running the speed test.", context.bot, update.message)
        deleteMessage(context.bot, speed)
        return
    download_speed = result['download'] / (1024 * 1024)
    upload_speed = result['upload'] / (1024 * 1024)
    ping = result['ping']
    timestamp = result['timestamp']
    bytes_sent = result['bytes_sent']
    bytes_received = result['bytes_received']
    server = result['server']
    client = result['client']
    string_speed = f'''
🚀 SPEEDTEST INFO:
<b>Upload:</b> <code>{f"{upload_speed:.2f} MB/s"}</code>
<b>Download:</b>  <code>{f"{download_speed:.2f} MB/s"}</code>
<b>Ping:</b> <code>{ping} ms</code>
<b>Time:</b> <code>{timestamp}</code>
<b>Data Sent:</b> <code>{get_readable_file_size(bytes_sent)}</code>
<b>Data Received:</b> <code>{get_readable_file_size(bytes_received)}</code>

🌍 SPEEDTEST SERVER:
<b>Name:</b> <code>{server['name']}</code>
<b>Country:</b> <code>{server['country']}, {server['cc']}</code>
<b>Sponsor:</b> <code>{server['sponsor']}</code>
<b>Latency:</b> <code>{server['latency']}</code>
<b>Latitude:</b> <code>{server['lat']}</code>
<b>Longitude:</b> <code>{server['lon']}</code>

👨‍💻 CLIENT DETAILS:
<b>IP Address:</b> <code>{client['ip']}</code>
<b>Latitude:</b> <code>{client['lat']}</code>
<b>Longitude:</b> <code>{client['lon']}</code>
<b>Country:</b> <code>{client['country']}</code>
<b>ISP:</b> <code>{client['isp']}</code>
<b>ISP Rating:</b> <code>{client['isprating']}</code>
'''
    try:
        sendMessage(text=string_speed, bot=context.bot, message=update.message)
        deleteMessage(context.bot, speed)
        Thread(target=auto_delete_message, args=(context.bot, update.message)).start()
    except Exception as g:
        logging.error(str(g))
        editMessage(string_speed, speed)
        Thread(target=auto_delete_message, args=(context.bot, update.message, speed)).start()

def speed_convert(size: float, byte: bool = True) -> str:
    """Converts a size in bytes to a human-readable string.

    Args:
        size (float): The size in bytes.
        byte (bool): Whether the size is in bytes or bits. Defaults to True.

    Returns:
        str: The human-readable string.
    """
    if not byte:
        size = size / 8
    power = 2 ** 10
    zero = 0
    units = {0: "B/s", 1: "KB/s", 2: "MB/s", 3: "GB/s", 4: "TB/s"}
    while size > power:
        size /= power
        zero += 1
    return f"{round(size, 2)} {units[zero]}"

speed_handler = CommandHandler(BotCommands.SpeedCommand, speedtest,
    CustomFilters.authorized_chat | CustomFilters.authorized_user)

dispatcher.add_handler(speed_handler)
