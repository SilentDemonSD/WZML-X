from speedtest import Speedtest, ConfigRetrievalError

from pyrogram import Client
from pyrogram.filters import command
from pyrogram.handlers import MessageHandler
from pyrogram.types import Message

from bot.core.plugin_manager import PluginBase, PluginInfo
from bot.helper.ext_utils.bot_utils import new_task, sync_to_async
from bot.helper.ext_utils.status_utils import get_readable_file_size
from bot.helper.telegram_helper.filters import CustomFilters
from bot.helper.telegram_helper.message_utils import (
    send_message,
    edit_message,
    delete_message,
)


class SpeedtestPlugin(PluginBase):
    PLUGIN_INFO = PluginInfo(
        name="speedtest_plugin",
        version="1.0.0",
        author="WZML-X",
        description="Speedtest plugin for testing internet speed",
        enabled=True,
        handlers=[],
        commands=["speedtest"],
        dependencies=[]
    )

    async def on_load(self) -> bool:
        from bot import LOGGER
        LOGGER.info("Speedtest plugin loaded")
        return True

    async def on_unload(self) -> bool:
        from bot import LOGGER
        LOGGER.info("Speedtest plugin unloaded")
        return True

    async def on_enable(self) -> bool:
        from bot import LOGGER
        LOGGER.info("Speedtest plugin enabled")
        return True

    async def on_disable(self) -> bool:
        from bot import LOGGER
        LOGGER.info("Speedtest plugin disabled")
        return True


@new_task
async def speedtest_command(client: Client, message: Message):
    speed = await send_message(message, "<i>Initiating Speedtest...</i>")
    try:
        speed_results = await sync_to_async(Speedtest)
        await sync_to_async(speed_results.get_best_server)
        await sync_to_async(speed_results.download)
        await sync_to_async(speed_results.upload)
    except ConfigRetrievalError:
        await edit_message(
            speed,
            "<b>ERROR:</b> <i>Can't connect to Server at the Moment, Try Again Later !</i>",
        )
        return
    speed_results.results.share()
    result = speed_results.results.dict()
    string_speed = f"""
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
"""
    try:
        await send_message(message, string_speed, photo=result["share"])
        await delete_message(speed)
    except Exception as e:
        from bot import LOGGER
        LOGGER.error(str(e))
        await edit_message(speed, string_speed) 