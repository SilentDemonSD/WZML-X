from asyncio import create_subprocess_exec, gather, sleep
from base64 import b64decode
from datetime import datetime
from os import execl as osexecl
from signal import SIGINT, signal
from sys import executable
from time import monotonic, time
from uuid import uuid4

from aiofiles import open as aiopen
from aiofiles.os import path as aiopath
from aiofiles.os import remove as aioremove
from bs4 import BeautifulSoup
from pyrogram import idle
from pyrogram.enums import ChatMemberStatus, ChatType
from pyrogram.filters import command, private, regex
from pyrogram.handlers import CallbackQueryHandler, MessageHandler
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from pytz import timezone
from requests import get as rget
from swibots import BotCommand

from bot import (
    DATABASE_URL,
    INCOMPLETE_TASK_NOTIFIER,
    LOGGER,
    Intervals,
    app,
    bot,
    bot_name,
    config_dict,
    scheduler,
    user,
    user_data,
)

from .helper.ext_utils.bot_utils import (
    get_readable_time,
    get_stats,
    new_task,
    set_commands,
    sync_to_async,
    update_user_ldata,
)
from .helper.ext_utils.db_handler import DbManager
from .helper.ext_utils.files_utils import clean_all, exit_clean_up
from .helper.ext_utils.telegraph_helper import telegraph
from .helper.listeners.aria2_listener import start_aria2_listener
from .helper.mirror_leech_utils.rclone_utils.serve import rclone_serve_booter
from .helper.tele_swi_helper.bot_commands import BotCommands
from .helper.tele_swi_helper.button_build import ButtonMaker
from .helper.tele_swi_helper.filters import CustomFilters
from .helper.tele_swi_helper.message_utils import (
    delete_status,
    deleteMessage,
    editMessage,
    editReplyMarkup,
    sendFile,
    sendMessage,
)
from .helper.themes import BotTheme
from .modules import *  # noqa: F403
from .version import get_version


async def stats(_, message):
    msg, btns = await get_stats(message)
    await sendMessage(message, msg, btns, photo="IMAGES")


@new_task
async def start(client, message):
    buttons = ButtonMaker()
    buttons.ubutton(BotTheme("ST_BN1_NAME"), BotTheme("ST_BN1_URL"))
    buttons.ubutton(BotTheme("ST_BN2_NAME"), BotTheme("ST_BN2_URL"))
    reply_markup = buttons.build_menu(2)
    if len(message.command) > 1 and message.command[1] == "wzmlx":
        await deleteMessage(message)
    elif len(message.command) > 1 and config_dict["TOKEN_TIMEOUT"]:
        userid = message.from_user.id
        encrypted_url = message.command[1]
        input_token, pre_uid = (b64decode(encrypted_url.encode()).decode()).split("&&")
        if int(pre_uid) != userid:
            return await sendMessage(message, BotTheme("OWN_TOKEN_GENERATE"))
        data = user_data.get(userid, {})
        if "token" not in data or data["token"] != input_token:
            return await sendMessage(message, BotTheme("USED_TOKEN"))
        elif (
            config_dict["LOGIN_PASS"] is not None
            and data["token"] == config_dict["LOGIN_PASS"]
        ):
            return await sendMessage(message, BotTheme("LOGGED_PASSWORD"))
        buttons.ibutton(BotTheme("ACTIVATE_BUTTON"), f"pass {input_token}", "header")
        reply_markup = buttons.build_menu(2)
        msg = BotTheme(
            "TOKEN_MSG",
            token=input_token,
            validity=get_readable_time(int(config_dict["TOKEN_TIMEOUT"])),
        )
        return await sendMessage(message, msg, reply_markup)
    elif await CustomFilters.authorized(client, message):
        start_string = BotTheme("ST_MSG", help_command=f"/{BotCommands.HelpCommand}")
        await sendMessage(message, start_string, reply_markup, photo="IMAGES")
    elif config_dict["BOT_PM"]:
        await sendMessage(message, BotTheme("ST_BOTPM"), reply_markup, photo="IMAGES")
    else:
        await sendMessage(message, BotTheme("ST_UNAUTH"), reply_markup, photo="IMAGES")
    await DbManager().update_pm_users(message.from_user.id)


async def token_callback(_, query):
    user_id = query.from_user.id
    input_token = query.data.split()[1]
    data = user_data.get(user_id, {})
    if "token" not in data or data["token"] != input_token:
        return await query.answer("Already Used, Generate New One", show_alert=True)
    update_user_ldata(user_id, "token", str(uuid4()))
    update_user_ldata(user_id, "time", time())
    await query.answer("Activated Temporary Token!", show_alert=True)
    kb = query.message.reply_markup.inline_keyboard[1:]
    kb.insert(
        0, [InlineKeyboardButton(BotTheme("ACTIVATED"), callback_data="pass activated")]
    )
    await editReplyMarkup(query.message, InlineKeyboardMarkup(kb))


async def login(_, message):
    if config_dict["LOGIN_PASS"] is None:
        return
    elif len(message.command) > 1:
        user_id = message.from_user.id
        input_pass = message.command[1]
        if user_data.get(user_id, {}).get("token", "") == config_dict["LOGIN_PASS"]:
            return await sendMessage(message, BotTheme("LOGGED_IN"))
        if input_pass != config_dict["LOGIN_PASS"]:
            return await sendMessage(message, BotTheme("INVALID_PASS"))
        update_user_ldata(user_id, "token", config_dict["LOGIN_PASS"])
        return await sendMessage(message, BotTheme("PASS_LOGGED"))
    else:
        await sendMessage(message, BotTheme("LOGIN_USED"))


async def restart(_, message):
    Intervals["stopAll"] = True
    restart_message = await sendMessage(message, BotTheme("RESTARTING"))
    if scheduler.running:
        scheduler.shutdown(wait=False)
    await delete_status()
    if qb := Intervals["qb"]:
        qb.cancel()
    if st := Intervals["status"]:
        for intvl in list(st.values()):
            intvl.cancel()
    await sleep(0.5)
    await sync_to_async(clean_all)
    await sleep(0.5)
    proc1 = await create_subprocess_exec(
        "pkill", "-9", "-f", "gunicorn|aria2c|qbittorrent-nox|ffmpeg|rclone"
    )
    proc2 = await create_subprocess_exec("python3", "update.py")
    await gather(proc1.wait(), proc2.wait())
    async with aiopen(".restartmsg", "w") as f:
        await f.write(f"{restart_message.chat.id}\n{restart_message.id}\n")
    osexecl(executable, executable, "-m", "bot")


async def ping(_, message):
    start_time = monotonic()
    reply = await sendMessage(message, BotTheme("PING"))
    end_time = monotonic()
    await editMessage(
        reply, BotTheme("PING_VALUE", value=int((end_time - start_time) * 1000))
    )


async def log(_, message):
    buttons = ButtonMaker()
    buttons.ibutton(
        BotTheme("LOG_DISPLAY_BT"), f"wzmlx {message.from_user.id} logdisplay"
    )
    buttons.ibutton(BotTheme("WEB_PASTE_BT"), f"wzmlx {message.from_user.id} webpaste")
    await sendFile(message, "log.txt", buttons=buttons.build_menu(1))


async def search_images():
    if not (query_list := config_dict["IMG_SEARCH"]):
        return
    try:
        total_pages = config_dict["IMG_PAGE"]
        base_url = "https://www.wallpaperflare.com/search"
        for query in query_list:
            query = query.strip().replace(" ", "+")
            for page in range(1, total_pages + 1):
                url = f"{base_url}?wallpaper={query}&width=1280&height=720&page={page}"
                r = rget(url)
                soup = BeautifulSoup(r.text, "html.parser")
                images = soup.select(
                    'img[data-src^="https://c4.wallpaperflare.com/wallpaper"]'
                )
                if len(images) == 0:
                    LOGGER.info(
                        "Maybe Site is Blocked on your Server, Add Images Manually !!"
                    )
                for img in images:
                    img_url = img["data-src"]
                    if img_url not in config_dict["IMAGES"]:
                        config_dict["IMAGES"].append(img_url)
        if len(config_dict["IMAGES"]) != 0:
            config_dict["STATUS_LIMIT"] = 2
        if DATABASE_URL:
            await DbManager().update_config(
                {
                    "IMAGES": config_dict["IMAGES"],
                    "STATUS_LIMIT": config_dict["STATUS_LIMIT"],
                }
            )
    except Exception as e:
        LOGGER.error(f"An error occurred: {e}")


async def bot_help(_, message):
    buttons = ButtonMaker()
    user_id = message.from_user.id
    buttons.ibutton(BotTheme("BASIC_BT"), f"wzmlx {user_id} guide basic")
    buttons.ibutton(BotTheme("USER_BT"), f"wzmlx {user_id} guide users")
    buttons.ibutton(BotTheme("MICS_BT"), f"wzmlx {user_id} guide miscs")
    buttons.ibutton(BotTheme("O_S_BT"), f"wzmlx {user_id} guide admin")
    buttons.ibutton(BotTheme("CLOSE_BT"), f"wzmlx {user_id} close")
    await sendMessage(message, BotTheme("HELP_HEADER"), buttons.build_menu(2))


async def restart_notification():
    now = datetime.now(timezone(config_dict["TIMEZONE"]))
    if await aiopath.isfile(".restartmsg"):
        with open(".restartmsg") as f:
            chat_id, msg_id = map(int, f)
    else:
        chat_id, msg_id = 0, 0

    async def send_incompelete_task_message(cid, msg):
        try:
            if msg.startswith("⌬ <b><i>Restarted Successfully!</i></b>"):
                await bot.edit_message_text(
                    chat_id=chat_id,
                    message_id=msg_id,
                    text=msg,
                    disable_web_page_preview=True,
                )
                await aioremove(".restartmsg")
            else:
                await bot.send_message(
                    chat_id=cid,
                    text=msg,
                    disable_web_page_preview=True,
                    disable_notification=True,
                )
        except Exception as e:
            LOGGER.error(e)

    if INCOMPLETE_TASK_NOTIFIER and DATABASE_URL:
        if notifier_dict := await DbManager().get_incomplete_tasks():
            for cid, data in notifier_dict.items():
                msg = (
                    BotTheme(
                        "RESTART_SUCCESS",
                        time=now.strftime("%I:%M:%S %p"),
                        date=now.strftime("%d/%m/%y"),
                        timz=config_dict["TIMEZONE"],
                        version=get_version(),
                    )
                    if cid == chat_id
                    else BotTheme("RESTARTED")
                )
                msg += "\n\n⌬ <b><i>Incomplete Tasks!</i></b>"
                for tag, links in data.items():
                    msg += f"\n➲ <b>User:</b> {tag}\n┖ <b>Tasks:</b>"
                    for index, link in enumerate(links, start=1):
                        msg_link, source = next(iter(link.items()))
                        msg += f" {index}. <a href='{source}'>S</a> ->  <a href='{msg_link}'>L</a> |"
                        if len(msg.encode()) > 4000:
                            await send_incompelete_task_message(cid, msg)
                            msg = ""
                if msg:
                    await send_incompelete_task_message(cid, msg)

    if await aiopath.isfile(".restartmsg"):
        try:
            await bot.edit_message_text(
                chat_id=chat_id,
                message_id=msg_id,
                text=BotTheme(
                    "RESTART_SUCCESS",
                    time=now.strftime("%I:%M:%S %p"),
                    date=now.strftime("%d/%m/%y"),
                    timz=config_dict["TIMEZONE"],
                    version=get_version(),
                ),
            )
        except Exception as e:
            LOGGER.error(e)
        await aioremove(".restartmsg")


async def log_check():
    if not config_dict["LEECH_LOG_ID"]:
        return
    for chat_id in config_dict["LEECH_LOG_ID"].split():
        chat_id, *topic_id = chat_id.split(":")
        try:
            try:
                chat = await bot.get_chat(int(chat_id))
            except Exception:
                LOGGER.error(
                    f"Not Connected Chat ID : {chat_id}, Make sure the Bot is Added!"
                )
                continue
            if chat.type == ChatType.CHANNEL:
                if not (await chat.get_member(bot.me.id)).privileges.can_post_messages:
                    LOGGER.error(
                        f"Not Connected Chat ID : {chat_id}, Make the Bot is Admin in Channel to Connect!"
                    )
                    continue
                if (
                    user
                    and not (
                        await chat.get_member(user.me.id)
                    ).privileges.can_post_messages
                ):
                    LOGGER.error(
                        f"Not Connected Chat ID : {chat_id}, Make the User is Admin in Channel to Connect!"
                    )
                    continue
            elif chat.type == ChatType.SUPERGROUP:
                if (await chat.get_member(bot.me.id)).status not in [
                    ChatMemberStatus.OWNER,
                    ChatMemberStatus.ADMINISTRATOR,
                ]:
                    LOGGER.error(
                        f"Not Connected Chat ID : {chat_id}, Make the Bot is Admin in Group to Connect!"
                    )
                    continue
                if user and (await chat.get_member(user.me.id)).status not in [
                    ChatMemberStatus.OWNER,
                    ChatMemberStatus.ADMINISTRATOR,
                ]:
                    LOGGER.error(
                        f"Not Connected Chat ID : {chat_id}, Make the User is Admin in Group to Connect!"
                    )
                    continue
            LOGGER.info(f"Connected Chat ID : {chat_id}")
        except Exception as e:
            LOGGER.error(f"Not Connected Chat ID : {chat_id}, ERROR: {e}")


async def setup_switch_bot_cmds():
    app.set_bot_commands(
        [
            BotCommand(BotCommands.EvalCommand, "Evaluate Code", True),
        ]
    )


async def main():
    if app:
        await setup_switch_bot_cmds()
        await app.start()
    await gather(
        sync_to_async(clean_all),
        DbManager().db_load(),
        torrent_search.initiate_search_tools(),
        restart_notification(),
        search_images(),
        telegraph.create_account(),
        rclone_serve_booter(),
        set_commands(bot),
        log_check(),
        sync_to_async(start_aria2_listener, wait=False),
    )

    bot.add_handler(
        MessageHandler(start, filters=command(BotCommands.StartCommand) & private)
    )
    bot.add_handler(CallbackQueryHandler(token_callback, filters=regex(r"^pass")))
    bot.add_handler(
        MessageHandler(login, filters=command(BotCommands.LoginCommand) & private)
    )
    bot.add_handler(
        MessageHandler(
            log, filters=command(BotCommands.LogCommand) & CustomFilters.sudo
        )
    )
    bot.add_handler(
        MessageHandler(
            restart, filters=command(BotCommands.RestartCommand) & CustomFilters.sudo
        )
    )
    bot.add_handler(
        MessageHandler(
            ping,
            filters=command(BotCommands.PingCommand)
            & CustomFilters.authorized
            & ~CustomFilters.blacklisted,
        )
    )
    bot.add_handler(
        MessageHandler(
            bot_help,
            filters=command(BotCommands.HelpCommand)
            & CustomFilters.authorized
            & ~CustomFilters.blacklisted,
        )
    )
    bot.add_handler(
        MessageHandler(
            stats,
            filters=command(BotCommands.StatsCommand)
            & CustomFilters.authorized
            & ~CustomFilters.blacklisted,
        )
    )
    if app:
        LOGGER.info("WZML-X Switch Bot Started!")
    if bot:
        LOGGER.info(f"WZML-X Telegram Bot [@{bot_name}] Started!")
    if user:
        LOGGER.info(f"WZ's User [@{user.me.username}] Ready!")
    signal(SIGINT, exit_clean_up)


async def stop_signals():
    if app:
        await app.stop()
    if user:
        await gather(bot.stop(), user.stop())
    else:
        await bot.stop()

# fix loop fetch
bot_run = bot.loop.run_until_complete
bot_run(main())
bot_run(idle())
bot_run(stop_signals())
