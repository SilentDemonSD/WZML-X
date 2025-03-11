from time import time
from uuid import uuid4

from pyrogram.enums import ChatAction
from pyrogram.errors import ChannelInvalid, PeerIdInvalid, RPCError, UserNotParticipant

from bot.helper.ext_utils.bot_utils import encode_slink

from ... import LOGGER, user_data
from ...core.config_manager import Config
from ...core.tg_client import TgClient
from ..ext_utils.shortener_utils import short_url
from ..ext_utils.status_utils import get_readable_time
from .button_build import ButtonMaker


async def chat_info(channel_id):
    channel_id = str(channel_id).strip()
    if channel_id.startswith("-100"):
        channel_id = int(channel_id)
    elif channel_id.startswith("@"):
        channel_id = channel_id.replace("@", "")
    else:
        return None
    try:
        return await TgClient.bot.get_chat(channel_id)
    except (PeerIdInvalid, ChannelInvalid) as e:
        LOGGER.error(f"{e.NAME}: {e.MESSAGE} for {channel_id}")
        return None


async def forcesub(message, ids, button=None):
    join_button = {}
    _msg = ""
    for channel_id in ids.split():
        chat = await chat_info(channel_id)
        try:
            await chat.get_member(message.from_user.id)
        except UserNotParticipant:
            if username := chat.username:
                invite_link = f"https://t.me/{username}"
            else:
                invite_link = chat.invite_link
            join_button[chat.title] = invite_link
        except RPCError as e:
            LOGGER.error(f"{e.NAME}: {e.MESSAGE} for {channel_id}")
        except Exception as e:
            LOGGER.error(f"{e} for {channel_id}")
    if join_button:
        if button is None:
            button = ButtonMaker()
        _msg = "┠ Channel(s) pending to be joined, Join Now!"
        for key, value in join_button.items():
            button.url_button(f"Join {key}", value, "footer")
    return _msg, button


async def user_info(user_id):
    try:
        return await TgClient.bot.get_users(user_id)
    except Exception:
        return ""


async def check_botpm(message, button=None):
    try:
        await TgClient.bot.send_chat_action(message.from_user.id, ChatAction.TYPING)
        return None, button
    except Exception:
        if button is None:
            button = ButtonMaker()
        _msg = "┠ <i>Bot isn't Started in PM or Inbox (Private)</i>"
        button.url_button(
            "Start Bot Now", f"https://t.me/{TgClient.BNAME}?start=start", "header"
        )
        return _msg, button


async def verify_token(user_id, button=None):
    if not Config.VERIFY_TIMEOUT or bool(
        user_id == Config.OWNER_ID
        or user_id in user_data
        and user_data[user_id].get("is_sudo")
    ):
        return None, button
    user_data.setdefault(user_id, {})
    data = user_data[user_id]
    expire = data.get("VERIFY_TIME")
    if Config.LOGIN_PASS and data.get("VERIFY_TOKEN", "") == Config.LOGIN_PASS:
        return None, button
    isExpired = (
        expire is None
        or expire is not None
        and (time() - expire) > Config.VERIFY_TIMEOUT
    )
    if isExpired:
        token = (
            data["VERIFY_TOKEN"]
            if expire is None and "VERIFY_TOKEN" in data
            else str(uuid4())
        )
        if expire is not None:
            del data["VERIFY_TIME"]
        data["VERIFY_TOKEN"] = token
        user_data[user_id].update(data)
        if button is None:
            button = ButtonMaker()
        encrypt_url = encode_slink(f"{token}&&{user_id}")
        button.url_button(
            "Verify Access Token",
            await short_url(f"https://t.me/{TgClient.BNAME}?start={encrypt_url}"),
        )
        return (
            f"┠ <i>Verify Access Token has been expired,</i> Kindly validate a new access token to start using bot again.\n┃\n┖ <b>Validity :</b> <code>{get_readable_time(Config.VERIFY_TIMEOUT)}</code>",
            button,
        )
    return None, button
