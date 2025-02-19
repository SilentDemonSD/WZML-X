from speedtest import Speedtest, ConfigRetrievalError

from .. import LOGGER
from ..helper.telegram_helper.message_utils import send_message, edit_message, delete_message
from ..helper.ext_utils.bot_utils import new_task, sync_to_async
from ..helper.ext_utils.status_utils import get_readable_file_size

@new_task
async def speedtest(_, message):
    speed = await send_message(message, "<i>Initiating Speedtest...</i>")
    try:
        speed_results = await sync_to_async(Speedtest)
        await sync_to_async(speed_results.get_best_server)
        await sync_to_async(speed_results.download)
        await sync_to_async(speed_results.upload)
    except ConfigRetrievalError:
        await edit_message(speed, "<b>ERROR:</b> <i>Can't connect to Server at the Moment, Try Again Later !</i>")
        return
    speed_results.results.share()
    result = speed_results.results.dict()
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
        await send_message(message, string_speed, photo=result['share'])
        await delete_message(speed)
    except Exception as e:
        LOGGER.error(str(e))
        await edit_message(speed, string_speed)