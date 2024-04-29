import asyncio
import contextlib
from html import escape
from os import remove
from typing import Any, Callable, Coroutine, Optional

import aiohttp
import telegram
from pyrogram import Client as PyrogramClient
from pyrogram.errors import FloodWait
from telegram import ParseMode, Update
from telegram.error import RetryAfter
from telegram.ext import CommandHandler, Filters, MessageHandler, Updater
from telegram.helpers import mention_html
from telegram.utils.helpers import escape_markdown

from bot import botStartTime
from bot.helper.ext_utils.bot_utils import (
    get_readable_message,
    get_readable_time,
    set_interval,
)
from bot.helper.telegram_helper.button_build import ButtonMaker


async def send_message(
    text: str,
    bot: telegram.Bot,
    message: telegram.Message,
    reply_markup: Optional[telegram.InlineKeyboardMarkup] = None,
) -> telegram.Message:
    try:
        return await bot.send_message(
            chat_id=message.chat_id,
            text=text,
            reply_to_message_id=message.message_id,
            reply_markup=reply_markup,
        )
    except RetryAfter as r:
        await asyncio.sleep(r.retry_after * 1.5)
        return await send_message(text, bot, message, reply_markup)
    except Exception as e:
        LOGGER.error(str(e))
        return


async def edit_message(
    text: str,
    message: telegram.Message,
    reply_markup: Optional[telegram.InlineKeyboardMarkup] = None,
) -> None:
    try:
        await bot.edit_message_text(
            text=text,
            message_id=message.message_id,
            chat_id=message.chat.id,
            reply_markup=reply_markup,
        )
    except RetryAfter as r:
        await asyncio.sleep(r.retry_after * 1.5)
        return await edit_message(text, message, reply_markup)
    except Exception as e:
        LOGGER.error(str(e))


async def edit_photo(
    text: str,
    message: telegram.Message,
    photo: telegram.InputMediaPhoto,
    reply_markup: Optional[telegram.InlineKeyboardMarkup] = None,
) -> None:
    try:
        await bot.edit_message_media(
            media=photo,
            chat_id=message.chat.id,
            message_id=message.message_id,
            reply_markup=reply_markup,
            parse_mode=ParseMode.HTML,
        )
    except RetryAfter as r:
        await asyncio.sleep(r.retry_after * 1.5)
        return await edit_photo(text, message, photo, reply_markup)
    except Exception as e:
        LOGGER.error(str(e))


async def send_rss(text: str, bot: telegram.Bot) -> None:
    if not rss_session:
        try:
            return await bot.send_message(
                config_dict["RSS_CHAT_ID"], text, disable_web_page_preview=True
            )
        except RetryAfter as r:
            await asyncio.sleep(r.retry_after * 1.5)
            return await send_rss(text, bot)
        except Exception as e:
            LOGGER.error(str(e))
            return
    else:
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    "https://api.telegram.org/bot<TOKEN>/sendMessage",
                    json={
                        "chat_id": config_dict["RSS_CHAT_ID"],
                        "text": text,
                        "disable_web_page_preview": True,
                    },
                ) as resp:
                    if resp.status == 200:
                        return
                    LOGGER.error(await resp.text())
        except FloodWait as e:
            await asyncio.sleep(e.value * 1.5)
            return await send_rss(text, bot)
        except Exception as e:
            LOGGER.error(str(e))


async def send_photo(
    text: str,
    bot: telegram.Bot,
    message: telegram.Message,
    photo: telegram.InputMediaPhoto,
    reply_markup: Optional[telegram.InlineKeyboardMarkup] = None,
) -> telegram.Message:
    try:
        return await bot.send_photo(
            chat_id=message.chat_id,
            photo=photo,
            reply_to_message_id=message.message_id,
            caption=text,
            reply_markup=reply_markup,
            parse_mode=ParseMode.HTML,
        )
    except RetryAfter as r:
        await asyncio.sleep(r.retry_after * 1.5)
        return await send_photo(text, bot, message, photo, reply_markup)
    except Exception as e:
        LOGGER.error(str(e))
        return


async def delete_message(bot: telegram.Bot, message: telegram.Message) -> None:
    try:
        await bot.delete_message(
            chat_id=message.chat.id,
            message_id=message.message_id,
        )
    except Exception as e:
        pass


async def send_log_file(bot: telegram.Bot, message: telegram.Message) -> None:
    with open("log.txt", "r") as file:
        log_lines = file.readlines()
    ind = 1
    log_lines_str = ""
    try:
        while len(log_lines_str) <= 2500:
            log_lines_str = log_lines[-ind] + "\n" + log_lines_str
            if ind == len(log_lines):
                break
            ind += 1
        start_line = f"Generated Last {ind} Lines from log.txt: \n\n---------------- START LOG -----------------\n\n"
        end_line = "\n---------------- END LOG -----------------"
        await send_message(escape(start_line + log_lines_str + end_line), bot, message)
    except Exception as err:
        LOGGER.error(f"Log Display : {err}")
    await bot.send_document(
        document="log.txt",
        thumb="Thumbnails/weeb.jpg",
        reply_to_message_id=message.message_id,
        chat_id=message.chat.id,
        caption=f'log.txt\n\n⏰️ UpTime: {get_readable_time(time() - botStartTime)}',
    )


async def send_file(
    bot: telegram.Bot,
    message: telegram.Message,
    name: str,
    caption: str = "",
) -> None:
    try:
        await bot.send_document(
            document=name,
            reply_to_message_id=message.message_id,
            caption=caption,
            parse_mode=ParseMode.HTML,
            chat_id=message.chat_id,
            thumb="Thumbnails/weeb.jpg",
        )
        remove(name)
    except FloodWait as r:
        await asyncio.sleep(r.value * 1.5)
        return await send_file(bot, message, name, caption)
    except Exception as e:
        LOGGER.error(str(e))


async def force_subscribe(bot: telegram.Bot, message: telegram.Message, tag: str) -> None:
    if not (FSUB_IDS := config_dict["FSUB_IDS"]):
        return
    join_button = {}
    for channel_id in FSUB_IDS.split():
        if not str(channel_id).startswith("-100"):
            continue
        chat = await bot.get_chat(channel_id)
        member = await chat.get_member(message.from_user.id)
        if member.status in [member.LEFT, member.KICKED]:
            join_button[chat.title] = chat.link or chat.invite_link
    if join_button:
        btn = ButtonMaker()
        for key, value in join_button.items():
            btn.buildbutton(key, value)
        msg = f"💡 {tag},\nYou have to join our channel(s) In Order To Use Bots!\n🔻 Join And Try Again!"
        reply_message = await send_message(msg, bot, message, btn.build_menu(1))
        return reply_message


def is_admin(message: telegram.Message, user_id: Optional[int] = None) -> bool:
    if message.chat.type != message.chat.PRIVATE:
        if user_id:
            member = message.chat.get_member(user_id)
        else:
            member = message.chat.get_member(message.from_user.id)
        return (
            member.status
            in [member.ADMINISTRATOR, member.CREATOR]
            or member.is_anonymous
        )


async def auto_delete_message(
    bot: telegram.Bot,
    cmd_message: Optional[telegram.Message] = None,
    bot_message: Optional[telegram.Message] = None,
) -> None:
    if config_dict["AUTO_DELETE_MESSAGE_DURATION"] != -1:
        await asyncio.sleep(config_dict["AUTO_DELETE_MESSAGE_DURATION"])
        if cmd_message is not None:
            await delete_message(bot, cmd_message)
        if bot_message is not None:
            await delete_message(bot, bot_message)


async def auto_delete_upload_message(
    bot: telegram.Bot,
    cmd_message: Optional[telegram.Message] = None,
    bot_message: Optional[telegram.Message] = None,
) -> None:
    if cmd_message.chat.type == "private":
        pass
    elif config_dict["AUTO_DELETE_UPLOAD_MESSAGE_DURATION"] != -1:
        await asyncio.sleep(
            config_dict["AUTO_DELETE_UPLOAD_MESSAGE_DURATION"]
        )
        if cmd_message is not None:
            await delete_message(bot, cmd_message)
        if bot_message is not None:
            await delete_message(bot, bot_message)


def delete_all_messages() -> None:
    with status_reply_dict_lock:
        for data in list(status_reply_dict.values()):
            try:
                delete_message(bot, data[0])
                del status_reply_dict[data[0].chat.id]
            except Exception as e:
                LOGGER.error(str(e))


def update_all_messages(force: bool = False) -> None:
    with status_reply_dict_lock:
        if not status_reply_dict or (
            not force and time() - list(status_reply_dict.values())[0][1] < 3
        ):
            return
        for chat_id in status_reply_dict:
            status_reply_dict[chat_id][1] = time()

    msg, buttons = get_readable_message()
    if msg is None:
        return
    with status_reply_dict_lock:
        for chat_id in status_reply_dict:
            if status_reply_dict[chat_id] and msg != status_reply_dict[chat_id][0].text:
                if config_dict["PICS"]:
                    rmsg = await edit_photo(
                        msg,
                        status_reply_dict[chat_id][0],
                        choice(config_dict["PICS"]),
                        buttons,
                    )
                else:
                    rmsg = await edit_message(msg, status_reply_dict[chat_id][0], buttons)
                if rmsg == "Message to edit not found":
                    del status_reply_dict[chat_id]
                    return
                status_reply_dict[chat_id][0].text = msg
                status_reply_dict[chat_id][1] = time()


async def send_status_message(
    msg: str, bot: telegram.Bot
) -> telegram.Message:
    progress, buttons = get_readable_message()
    if progress is None:
        return
    with status_reply_dict_lock:
        if msg.chat.id in status_reply_dict:
            message = status_reply_dict[msg.chat.id][0]
            await delete_message(bot, message)
            del status_reply_dict[msg.chat.id]
        if config_dict["PICS"]:
            message = await send_photo(
                progress, bot, msg, choice(config_dict["PICS"]), buttons
            )
        else:
            message = await send_message(progress, bot, msg, buttons)
        status_reply_dict[msg.chat.id] = [message, time()]
        if not Interval:
            Interval.append(set_interval(config_dict["STATUS_UPDATE_INTERVAL"], update_all_messages))
