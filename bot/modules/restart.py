from asyncio import gather, get_event_loop, sleep
from datetime import datetime
from importlib import reload as reload_module
from os import execl as osexecl
from sys import executable

from aiofiles import open as aiopen
from aiofiles.os import path as aiopath, remove
from pytz import timezone
from pyrogram.enums import ButtonStyle

from bot.version import get_version

from .. import LOGGER, intervals, sabnzbd_client, scheduler
from ..core.config_manager import Config, BinConfig
from ..core.jdownloader_booter import jdownloader
from ..core.tg_client import TgClient
from ..core.torrent_manager import TorrentManager
from ..helper.ext_utils.bot_utils import (
    THREAD_POOL,
    cmd_exec,
    new_task,
    resolve_command,
)
from ..helper.ext_utils.db_handler import database
from ..helper.listeners.mega_listener import mega_cleanup
from ..helper.telegram_helper import button_build
from ..helper.telegram_helper.message_utils import (
    delete_message,
    send_message,
)


@new_task
async def restart_bot(_, message):
    args = message.text.split()
    mode = "soft" if "-s" in args else "hard"
    buttons = button_build.ButtonMaker()
    buttons.data_button("Yes!", f"botrestart confirm {mode}", style=ButtonStyle.SUCCESS)
    buttons.data_button("No!", "botrestart cancel", style=ButtonStyle.DANGER)
    button = buttons.build_menu(2)
    msg = "<i>Are you really sure you want to restart the bot ?</i>"
    if mode == "soft":
        msg += "\n<i>Mode: Soft (code reload only, tasks keep running)</i>"
    await send_message(message, msg, button)


@new_task
async def restart_sessions(_, message):
    buttons = button_build.ButtonMaker()
    buttons.data_button("Yes!", "sessionrestart confirm", style=ButtonStyle.SUCCESS)
    buttons.data_button("No!", "sessionrestart cancel", style=ButtonStyle.DANGER)
    button = buttons.build_menu(2)
    await send_message(
        message,
        "<i>Are you really sure you want to restart the session(s) ?!</i>",
        button,
    )


def _restart_header(now, is_restart_chat=False):
    title = "Restarted Successfully!" if is_restart_chat else "Bot Restarted!"
    return (
        f"⌬ <b><i>{title}</i></b>\n"
        f"┟ <b>Date:</b> {now.strftime('%d/%m/%y')}\n"
        f"┠ <b>Time:</b> {now.strftime('%I:%M:%S %p')}\n"
        f"┠ <b>TimeZone:</b> {Config.TIMEZONE}\n"
        f"┠ <b>Branch:</b> {Config.UPSTREAM_BRANCH}\n"
        f"┖ <b>Version:</b> {get_version()}"
    )


async def _send_msg(cid, msg):
    try:
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
        try:
            with open(".restartmsg") as f:
                chat_id, msg_id = map(int, f)
        except Exception:
            chat_id, msg_id = 0, 0
    else:
        chat_id, msg_id = 0, 0

    now = datetime.now(timezone(Config.TIMEZONE))

    if Config.DATABASE_URL and (Config.INC_TASK_NOTIFY or Config.INC_TASK_RESUME):
        if notifier_dict := await database.get_incomplete_tasks():
            try:
                if Config.INC_TASK_RESUME:
                    await _resume_tasks(notifier_dict)
                if Config.INC_TASK_NOTIFY:
                    await _notify_tasks(notifier_dict, chat_id, now)
            finally:
                await database.drop_incomplete_tasks()

    if await aiopath.isfile(".restartmsg"):
        try:
            await TgClient.bot.edit_message_text(
                chat_id=chat_id,
                message_id=msg_id,
                text=_restart_header(now, is_restart_chat=True),
                disable_web_page_preview=True,
            )
        except Exception as e:
            LOGGER.error(e)
        await remove(".restartmsg")


async def _notify_tasks(notifier_dict, restart_chat_id, now):
    for cid, data in notifier_dict.items():
        is_restart_chat = cid == restart_chat_id
        header = _restart_header(now, is_restart_chat)
        msg = header + "\n\n⌬ <b><i>Incomplete Tasks!</i></b>"
        for tag, tasks in data.items():
            entry = f"\n➲ <b>User:</b> {tag}\n┖ <b>Tasks:</b>"
            for index, task in enumerate(tasks, start=1):
                link = task.get("link", "")
                entry += f" {index}. <a href='{link}'>L</a> |"
            if len((msg + entry).encode()) > 4000:
                await _send_msg(cid, msg)
                msg = header
            msg += entry
        if msg:
            await _send_msg(cid, msg)


async def _resume_tasks(notifier_dict):
    for cid, data in notifier_dict.items():
        for tag, tasks in data.items():
            for task in tasks:
                command = task.get("command", "")
                user_id = task.get("user_id", 0)
                reply_to_msg_id = task.get("reply_to_msg_id", 0)
                dump_msg_id = task.get("dump_msg_id", 0)
                dump_chat = task.get("dump_chat", 0)
                if not command or not user_id:
                    continue
                try:
                    user = await TgClient.bot.get_users(user_id)
                except Exception as e:
                    LOGGER.warning(f"Resume: cannot get user {user_id}: {e}")
                    continue
                handler = resolve_command(command)
                if handler is None:
                    continue
                try:
                    msg = await TgClient.bot.send_message(
                        chat_id=cid,
                        text=command,
                        disable_notification=True,
                    )
                    msg.text = command
                    msg.from_user = user
                    if reply_to_msg_id:
                        try:
                            reply_msg = await TgClient.bot.get_messages(
                                chat_id=cid, message_ids=reply_to_msg_id
                            )
                            if reply_msg:
                                msg.reply_to_message = reply_msg
                        except Exception as e:
                            LOGGER.warning(
                                f"Resume: cannot fetch reply msg {reply_to_msg_id}: {e}"
                            )
                    if not msg.reply_to_message and dump_msg_id and dump_chat:
                        try:
                            dump_msg = await TgClient.bot.get_messages(
                                chat_id=dump_chat, message_ids=dump_msg_id
                            )
                            if dump_msg:
                                msg.reply_to_message = dump_msg
                        except Exception as e:
                            LOGGER.warning(
                                f"Resume: cannot fetch dump msg {dump_msg_id}: {e}"
                            )
                    await handler(TgClient.bot, msg)
                    await sleep(1)
                except Exception as e:
                    LOGGER.error(f"Resume: failed for '{command}' in {cid}: {e}")


@new_task
async def confirm_restart(_, query):
    await query.answer()
    data = query.data.split()
    message = query.message
    reply_to = message.reply_to_message
    await delete_message(message)
    if data[1] == "confirm":
        intervals["stopAll"] = True
        if data[2] == "soft":
            restart_msg = await send_message(reply_to, "<i>Reloading...</i>")
            await _runtime_reload()
            intervals["stopAll"] = False
            try:
                await TgClient.bot.edit_message_text(
                    chat_id=restart_msg.chat.id,
                    message_id=restart_msg.id,
                    text=_restart_header(datetime.now(timezone(Config.TIMEZONE))),
                    disable_web_page_preview=True,
                )
            except Exception as e:
                LOGGER.error(e)
        else:
            restart_message = await send_message(reply_to, "<i>Restarting...</i>")

            if qb := intervals["qb"]:
                qb.cancel()
            if jd := intervals["jd"]:
                jd.cancel()
            if nzb := intervals["nzb"]:
                nzb.cancel()
            if st := intervals["status"]:
                for intvl in list(st.values()):
                    intvl.cancel()

            if scheduler.running:
                scheduler.shutdown(wait=False)

            await mega_cleanup()

            sabnzbd_task = None
            jd_task = None
            if not Config.DISABLE_NZB and sabnzbd_client.LOGGED_IN:
                sabnzbd_task = gather(
                    sabnzbd_client.pause_all(),
                    sabnzbd_client.delete_job("all", True),
                    sabnzbd_client.purge_all(True),
                    sabnzbd_client.delete_history("all", delete_files=True),
                )
            if not Config.DISABLE_JD and jdownloader.is_connected:
                jd_task = gather(
                    jdownloader.device.downloadcontroller.stop_downloads(),
                    jdownloader.device.linkgrabber.clear_list(),
                    jdownloader.device.downloads.cleanup(
                        "DELETE_ALL",
                        "REMOVE_LINKS_AND_DELETE_FILES",
                        "ALL",
                    ),
                )

            try:
                await TorrentManager.remove_all()
            except Exception:
                pass
            await TorrentManager.close_all()

            if sabnzbd_task is not None:
                try:
                    await sabnzbd_task
                except Exception:
                    pass
                try:
                    await sabnzbd_client.close()
                except Exception:
                    pass
            if jd_task is not None:
                try:
                    await jd_task
                except Exception:
                    pass
                try:
                    await jdownloader.close()
                except Exception:
                    pass

            await TgClient.stop()

            THREAD_POOL.shutdown(wait=False)

            await cmd_exec(
                [
                    "pkill",
                    "-9",
                    "-f",
                    f"gunicorn|{BinConfig.ARIA2_NAME}|{BinConfig.QBIT_NAME}|{BinConfig.FFMPEG_NAME}|{BinConfig.RCLONE_NAME}|java|{BinConfig.SABNZBD_NAME}|7z|split",
                ]
            )

            await cmd_exec(["python3", "update.py"])

            try:
                async with aiopen(".restartmsg", "w") as f:
                    await f.write(f"{restart_message.chat.id}\n{restart_message.id}\n")
            except Exception:
                pass

            get_event_loop().create_task(_background_cleanup())

            osexecl(executable, executable, "-m", "bot")
    else:
        await delete_message(message, reply_to)


async def _runtime_reload():
    await cmd_exec(["python3", "update.py"])

    import sys as _sys

    modules_to_reload = [
        "bot.helper.ext_utils.bot_utils",
        "bot.helper.ext_utils.help_messages",
        "bot.helper.telegram_helper.message_utils",
        "bot.helper.telegram_helper.button_build",
        "bot.helper.telegram_helper.filters",
        "bot.helper.telegram_helper.bot_commands",
        "bot.modules.bot_settings",
        "bot.modules.plugin_manager",
        "bot.modules.cancel_task",
        "bot.modules.chat_permission",
        "bot.modules.clone",
        "bot.modules.exec",
        "bot.modules.file_selector",
        "bot.modules.force_start",
        "bot.modules.gd_count",
        "bot.modules.gd_delete",
        "bot.modules.gd_clean",
        "bot.modules.gd_search",
        "bot.modules.help",
        "bot.modules.images",
        "bot.modules.category_select",
        "bot.modules.broadcast",
        "bot.modules.mirror_leech",
        "bot.modules.restart",
        "bot.modules.rss",
        "bot.modules.search",
        "bot.modules.services",
        "bot.modules.shell",
        "bot.modules.stats",
        "bot.modules.status",
        "bot.modules.users_settings",
        "bot.modules.ytdlp",
    ]

    for mod_name in modules_to_reload:
        if mod_name in _sys.modules:
            try:
                reload_module(_sys.modules[mod_name])
            except Exception as e:
                LOGGER.error(f"Reload failed for {mod_name}: {e}")

    try:
        import bot.modules as _bm

        reload_module(_bm)
    except Exception as e:
        LOGGER.error(f"Reload failed for bot.modules: {e}")

    try:
        import bot.core.handlers as _bh

        reload_module(_bh)
    except Exception as e:
        LOGGER.error(f"Reload failed for bot.core.handlers: {e}")

    try:
        before = {g: len(hs) for g, hs in TgClient.bot.dispatcher.handlers.items()}
    except Exception:
        before = {}

    try:
        from bot.core.handlers import add_handlers

        await add_handlers()
    except Exception as e:
        LOGGER.error(f"Handler re-registration failed: {e}")
        return

    for group, old_count in before.items():
        if group in TgClient.bot.dispatcher.handlers:
            TgClient.bot.dispatcher.handlers[group] = TgClient.bot.dispatcher.handlers[
                group
            ][old_count:]

    try:
        from bot.core.plugin_manager import get_plugin_manager
        from bot.modules.plugin_manager import register_plugin_commands

        manager = get_plugin_manager()
        manager.bot = TgClient.bot
        register_plugin_commands()
        for rec in manager.list_plugins():
            rec.handlers = []
            rec.registered = False
            if rec.enabled:
                manager._attach(rec)
    except Exception as e:
        LOGGER.error(f"Plugin re-registration failed: {e}")


async def _background_cleanup():
    try:
        await cmd_exec(["rm", "-rf", "/usr/src/app/downloads/"])
    except Exception:
        pass
