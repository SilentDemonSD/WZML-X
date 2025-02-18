from asyncio import create_subprocess_exec, gather
from datetime import datetime
from os import execl as osexecl
from sys import executable

from aiofiles import open as aiopen
from aiofiles.os import path as aiopath, remove
from pytz import timezone

from bot.version import get_version

from .. import LOGGER, intervals, sabnzbd_client, scheduler
from ..core.config_manager import Config
from ..core.jdownloader_booter import jdownloader
from ..core.tg_client import TgClient
from ..core.torrent_manager import TorrentManager
from ..helper.ext_utils.bot_utils import new_task
from ..helper.ext_utils.db_handler import database
from ..helper.ext_utils.files_utils import clean_all
from ..helper.telegram_helper import button_build
from ..helper.telegram_helper.message_utils import (
    delete_message,
    send_message,
)


@new_task
async def restart_bot(_, message):
    buttons = button_build.ButtonMaker()
    buttons.data_button("Yes!", "botrestart confirm")
    buttons.data_button("No!", "botrestart cancel")
    button = buttons.build_menu(2)
    await send_message(
        message, "<i>Are you really sure you want to restart the bot ?</i>", button
    )


@new_task
async def restart_sessions(_, message):
    buttons = button_build.ButtonMaker()
    buttons.data_button("Yes!", "sessionrestart confirm")
    buttons.data_button("No!", "sessionrestart cancel")
    button = buttons.build_menu(2)
    await send_message(
        message,
        "<i>Are you really sure you want to restart the session(s) ?!</>",
        button,
    )


async def send_incomplete_task_message(cid, msg_id, msg):
    try:
        if msg.startswith("⌬ <b><i>Restarted Successfully!</i></b>"):
            await TgClient.bot.edit_message_text(
                chat_id=cid,
                message_id=msg_id,
                text=msg,
                disable_web_page_preview=True,
            )
            await remove(".restartmsg")
        else:
            await TgClient.bot.send_message(
                chat_id=cid,
                text=msg,
                disable_web_page_preview=True,
                disable_notification=True,
            )
    except Exception as e:
        LOGGER.error(e)


async def restart_notification():
    if await aiopath.isfile(".restartmsg"):
        with open(".restartmsg") as f:
            chat_id, msg_id = map(int, f)
    else:
        chat_id, msg_id = 0, 0

    now = datetime.now(timezone("Asia/Kolkata"))

    if Config.INCOMPLETE_TASK_NOTIFIER and Config.DATABASE_URL:
        if notifier_dict := await database.get_incomplete_tasks():
            for cid, data in notifier_dict.items():
                msg = f"""⌬ <b><i>{"Restarted Successfully!" if cid == chat_id else "Bot Restarted!"}</i></b>
┟ <b>Date:</b> {now.strftime("%d/%m/%y")}
┠ <b>Time:</b> {now.strftime("%I:%M:%S %p")}
┠ <b>TimeZone:</b> Asia/Kolkata
┖ <b>Version:</b> {get_version()}"""
                for tag, links in data.items():
                    msg += f"\n\n{tag}: "
                    for index, link in enumerate(links, start=1):
                        msg += f" <a href='{link}'>{index}</a> |"
                        if len(msg.encode()) > 4000:
                            await send_incomplete_task_message(cid, msg_id, msg)
                            msg = ""
                if msg:
                    await send_incomplete_task_message(cid, msg_id, msg)

    if await aiopath.isfile(".restartmsg"):
        try:
            await TgClient.bot.edit_message_text(
                chat_id=chat_id,
                message_id=msg_id,
                text=f"""⌬ <b><i>Restarted Successfully!</i></b>
┟ <b>Date:</b> {now.strftime("%d/%m/%y")}
┠ <b>Time:</b> {now.strftime("%I:%M:%S %p")}
┠ <b>TimeZone:</b> Asia/Kolkata
┖ <b>Version:</b> {get_version()}""",
            )
        except Exception as e:
            LOGGER.error(e)
        await remove(".restartmsg")


@new_task
async def confirm_restart(_, query):
    await query.answer()
    data = query.data.split()
    message = query.message
    await delete_message(message)
    if data[1] == "confirm":
        reply_to = message.reply_to_message
        intervals["stopAll"] = True
        restart_message = await send_message(reply_to, "<i>Restarting...</i>")
        await delete_message(message)
        await TgClient.stop()
        if scheduler.running:
            scheduler.shutdown(wait=False)
        if qb := intervals["qb"]:
            qb.cancel()
        if jd := intervals["jd"]:
            jd.cancel()
        if nzb := intervals["nzb"]:
            nzb.cancel()
        if st := intervals["status"]:
            for intvl in list(st.values()):
                intvl.cancel()
        await clean_all()
        await TorrentManager.close_all()
        if sabnzbd_client.LOGGED_IN:
            await gather(
                sabnzbd_client.pause_all(),
                sabnzbd_client.delete_job("all", True),
                sabnzbd_client.purge_all(True),
                sabnzbd_client.delete_history("all", delete_files=True),
            )
            await sabnzbd_client.close()
        if jdownloader.is_connected:
            await gather(
                jdownloader.device.downloadcontroller.stop_downloads(),
                jdownloader.device.linkgrabber.clear_list(),
                jdownloader.device.downloads.cleanup(
                    "DELETE_ALL",
                    "REMOVE_LINKS_AND_DELETE_FILES",
                    "ALL",
                ),
            )
            await jdownloader.close()
        proc1 = await create_subprocess_exec(
            "pkill",
            "-9",
            "-f",
            "gunicorn|fastfetcher|torrentmaster|videomancer|cloudsweep|java|newsgator|7z|split",
        )
        proc2 = await create_subprocess_exec("python3", "update.py")
        await gather(proc1.wait(), proc2.wait())
        async with aiopen(".restartmsg", "w") as f:
            await f.write(f"{restart_message.chat.id}\n{restart_message.id}\n")
        osexecl(executable, executable, "-m", "bot")
    else:
        await delete_message(message)
