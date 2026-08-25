from speedtest import ConfigRetrievalError, Speedtest

from bot import LOGGER
from bot.helper.ext_utils.bot_utils import new_task, sync_to_async
from bot.helper.telegram_helper.message_utils import (
    delete_message,
    edit_message,
    send_message,
)

from .render import format_result


@new_task
async def speedtest_command(_, message):
    status = await send_message(message, "<i>Initiating Speedtest...</i>")
    try:
        results = await sync_to_async(Speedtest)
        await sync_to_async(results.get_best_server)
        await sync_to_async(results.download)
        await sync_to_async(results.upload)
    except ConfigRetrievalError:
        await edit_message(
            status,
            "<b>ERROR:</b> <i>Can't connect to Server at the Moment, Try Again Later !</i>",
        )
        return
    except Exception as err:
        LOGGER.error(f"speedtest failed: {err}")
        await edit_message(status, f"<b>ERROR:</b> <i>{err}</i>")
        return

    try:
        results.results.share()
    except Exception:
        pass

    result = results.results.dict()
    text = format_result(result)
    try:
        await send_message(message, text, photo=result.get("share"))
        await delete_message(status)
    except Exception as err:
        LOGGER.error(str(err))
        await edit_message(status, text)
