#!/usr/bin/env python3
import asyncio
import os
from re import match as re_match
from typing import Union, Any, Dict, List, Optional

import aiofiles
from pyrogram.errors import (
    FloodWait,
    ReplyMarkupInvalid,
    PeerIdInvalid,
    ChannelInvalid,
    RPCError,
    UserNotParticipant,
    MessageNotModified,
    MessageEmpty,
    PhotoInvalidDimensions,
    WebpageCurlFailed,
    MediaEmpty,
)
from pyrogram.types import InputMediaPhoto, Message
from bot.helper.ext_utils.bot_utils import get_readable_message, setInterval, sync_to_async, download_image_url, fetch_user_tds, fetch_user_dumps
from bot.helper.telegram_helper.button_build import ButtonMaker
from bot.helper.ext_utils.exceptions import TgLinkException

bot: Any = None  # type: ignore
user: Any = None  # type: ignore
config_dict: Dict[str, Any] = {}  # type: ignore
Interval: Optional[List[asyncio.Task]] = None  # type: ignore


async def send_message(message: Message, text: str, buttons: Union[ButtonMaker, None] = None, photo: Union[str, bytes] = None) -> Message:
    """
    Send a message to the given message object.

    :param message: The message object to reply to.
    :param text: The text to send.
    :param buttons: The buttons to send with the message.
    :param photo: The photo to send with the message.
    :return: The sent message object.
    """
    try:
        if photo:
            if photo == 'IMAGES':
                photo = rchoice(config_dict['IMAGES'])
            media = InputMediaPhoto(photo) if isinstance(photo, str) else InputMediaPhoto(media=photo)
            return await message.reply_media(media, reply_to_message_id=message.id, caption=text, reply_markup=buttons, disable_notification=True)

        return await message.reply(text=text, quote=True, disable_web_page_preview=True, disable_notification=True, reply_markup=buttons)
    except FloodWait as f:
        await asyncio.sleep(f.value * 1.2)
        return await send_message(message, text, buttons, photo)
    except ReplyMarkupInvalid:
        return await send_message(message, text, None, photo)
    except Exception as e:  # noqa
        print(e)
        return str(e)


# ... other functions ...

async def open_category_btns(message: Message) -> Optional[str]:
    """
    Open category buttons for the user to select a category.

    :param message: The message object to reply to.
    :return: The selected category or None if cancelled.
    """
    user_id = message.from_user.id
    msg_id = message.id
    buttons = ButtonMaker()
    _tick = True
    if len(utds := await fetch_user_tds(user_id)) > 1:
        for _name in utds.keys():
            buttons.ibutton(f'{"✅️" if _tick else ""} {_name}', f"scat {user_id} {msg_id} {_name.replace(' ', '_')}")  # noqa
            if _tick: _tick, cat_name = False, _name
    elif len(categories_dict) > 1:
        for _name in categories_dict.keys():
            buttons.ibutton(f'{"✅️" if _tick else ""} {_name}', f"scat {user_id} {msg_id} {_name.replace(' ', '_')}")  # noqa
            if _tick: _tick, cat_name = False, _name
    buttons.ibutton('Cancel', f'scat {user_id} {msg_id} scancel', 'footer')
    buttons.ibutton(f'Done (60)', f'scat {user_id} {msg_id} sdone', 'footer')
    prompt = await send_message(message, f'<b>Select the category where you want to upload</b>\n\n<i><b>Upload Category:</b></i> <code>{cat_name}</code>\n\n<b>Timeout:</b> 60 sec', buttons.build_menu(3))  # noqa
    start_time = time()
    bot_cache[msg_id] = [None, None, False, False, start_time]
    while time() - start_time <= 60:
        await asyncio.sleep(0.5)
        if bot_cache[msg_id][2] or bot_cache[msg_id][3]:
            break
    drive_id, index_link, _, is_cancelled, __ = bot_cache[msg_id]
    if not is_cancelled:
        await delete_message(prompt)
    else:
        await edit_message(prompt, "<b>Task Cancelled</b>")
    del bot_cache[msg_id]
    return drive_id, index_link


# ... other functions ...
