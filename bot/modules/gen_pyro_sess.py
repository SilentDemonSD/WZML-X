from asyncio import Event, wait_for, TimeoutError as AsyncTimeout
from os.path import exists as path_exists

from aiofiles.os import remove as aioremove
from pyrogram import Client, __version__ as wzgram_version
from ..version import get_version
from pyrogram.enums import ChatType
from pyrogram.filters import create, user, text, private
from pyrogram.handlers import CallbackQueryHandler, MessageHandler
from pyrogram.errors import (
    SessionPasswordNeeded,
    FloodWait,
    PhoneNumberInvalid,
    ApiIdInvalid,
    PhoneCodeInvalid,
    PhoneCodeExpired,
)

from ..core.tg_client import TgClient
from ..core.config_manager import Config
from ..helper.ext_utils.bot_utils import new_task
from ..helper.ext_utils.status_utils import get_readable_time
from ..helper.telegram_helper.button_build import ButtonMaker
from ..helper.telegram_helper.message_utils import (
    send_message,
    edit_message,
    delete_message,
)

_STOP = "gensess_stop"
_TIMEOUT = 120


def _stop_filter(uid):
    async def _check(_, __, update):
        return update.data == _STOP and update.from_user.id == uid

    return create(_check)


async def _safe_disconnect(client):
    try:
        await client.disconnect()
    except ConnectionError:
        pass


def _stop_btns():
    btns = ButtonMaker()
    btns.data_button("Cancel Process", data=_STOP)
    return btns.build_menu(1)


def _header(user_name):
    return (
        "⌬ <u><i><b>WZGram String Session Generator</b></i></u>\n│\n"
        f"│ <b>User</b> → <b>{user_name}</b>!"
    )


def _collected(api_id=None, api_hash=None, phone=None):
    parts = []
    if api_id is not None:
        parts.append(f"┠ <b>API_ID</b> → <code>{api_id}</code>")
    if api_hash is not None:
        masked = api_hash[:4] + "*" * (len(api_hash) - 4)
        parts.append(f"┠ <b>API_HASH</b> → <code>{masked}</code>")
    if phone is not None:
        parts.append(f"┠ <b>Phone</b> → <code>{phone}</code>")
    return "\n".join(parts) if parts else ""


def _stop_msg(h, c):
    return f"{h}\n┃\n" + (
        f"{c}\n┃\n┖ <b>Process Stopped.</b>" if c else "┖ <b>Process Stopped.</b>"
    )


def _timeout_msg(h, c):
    return f"{h}\n┃\n" + (
        f"{c}\n┃\n┃ <b>Timed Out!</b>\n┖ <i>Process Stopped.</i>"
        if c
        else "┃ <b>Timed Out!</b>\n┖ <i>Process Stopped.</i>"
    )


def _error_msg(h, c, err):
    return f"{h}\n┃\n" + (f"{c}\n┃\n┖ {err}" if c else f"┖ {err}")


async def _invoke(user_id, timeout=_TIMEOUT):
    event = Event()
    result = [None]

    async def _on_text(_, message):
        await delete_message(message)
        result[0] = message.text or ""
        event.set()

    async def _on_stop(_, query):
        await query.answer()
        result[0] = _STOP
        event.set()

    h1 = TgClient.bot.add_handler(
        MessageHandler(_on_text, filters=user(user_id) & text & private),
        group=-1,
    )
    h2 = TgClient.bot.add_handler(
        CallbackQueryHandler(_on_stop, filters=_stop_filter(user_id)),
        group=-1,
    )
    try:
        await wait_for(event.wait(), timeout)
    except AsyncTimeout:
        result[0] = None
    finally:
        TgClient.bot.remove_handler(*h1)
        TgClient.bot.remove_handler(*h2)

    return result[0]


async def _stop_or_timeout(value, msg, h, c, pyro_client=None):
    if value is None:
        await edit_message(msg, _timeout_msg(h, c))
        if pyro_client:
            await _safe_disconnect(pyro_client)
        return True
    if value == _STOP:
        await edit_message(msg, _stop_msg(h, c))
        if pyro_client:
            await _safe_disconnect(pyro_client)
        return True
    return False


@new_task
async def gen_pyro_string(_, message):
    if message.chat.type != ChatType.PRIVATE:
        return

    user_id = message.from_user.id
    user_name = message.from_user.first_name or "User"
    btns = _stop_btns()
    h = _header(user_name)

    api_id = Config.TELEGRAM_API
    api_hash = Config.TELEGRAM_HASH

    if not api_id or not api_hash:
        sess_msg = await send_message(
            message,
            f"{h}\n┃\n"
            "┃ <i>Send your <code>API_ID</code> (also known as <code>APP_ID</code>).</i>\n"
            "┃ <i>Get it from <a href='https://my.telegram.org'>my.telegram.org</a>.</i>\n"
            "┃\n"
            f"┖ <b>Timeout:</b> <code>{get_readable_time(_TIMEOUT)}</code>",
            btns,
        )

        api_id = await _invoke(user_id)
        if await _stop_or_timeout(api_id, sess_msg, h, ""):
            return

        try:
            api_id = int(api_id)
        except ValueError:
            return await edit_message(
                sess_msg, _error_msg(h, "", "<i><code>APP_ID</code> is Invalid.</i>")
            )

        c = _collected(api_id=api_id)
        await edit_message(
            sess_msg,
            f"{h}\n\n{c}\n\n"
            "┃ <i>Send your <code>API_HASH</code>.</i>\n"
            "┃ <i>Get it from <a href='https://my.telegram.org'>my.telegram.org</a>.</i>\n"
            "┃\n"
            f"┖ <b>Timeout:</b> <code>{get_readable_time(_TIMEOUT)}</code>",
            btns,
        )

        api_hash = await _invoke(user_id)
        if await _stop_or_timeout(api_hash, sess_msg, h, c):
            return
        if len(api_hash) <= 30:
            return await edit_message(
                sess_msg, _error_msg(h, c, "<i><code>API_HASH</code> is Invalid.</i>")
            )

        c = _collected(api_id=api_id, api_hash=api_hash)
    else:
        sess_msg = await send_message(
            message,
            f"{h}\n┃\n"
            f"┃ <i>Using <b>API_ID</b> &amp; <b>API_HASH</b> from bot config.</i>\n"
            "┃\n"
            f"┖ <b>Timeout:</b> <code>{get_readable_time(_TIMEOUT)}</code>",
            btns,
        )
        c = _collected(api_id=api_id, api_hash=api_hash)

    while True:
        await edit_message(
            sess_msg,
            f"{h}\n┃\n{c}\n┃\n"
            "┃ <i>Send your phone number in International Format.</i>\n"
            "┖ <b>Example:</b> <code>+14154566376</code>",
            btns,
        )

        phone_no = await _invoke(user_id)
        if await _stop_or_timeout(phone_no, sess_msg, h, c):
            return

        c_phone = _collected(api_id=api_id, api_hash=api_hash, phone=phone_no)
        await edit_message(
            sess_msg,
            f"{h}\n┃\n{c_phone}\n┃\n"
            f"┃ Is <code>{phone_no}</code> correct?\n"
            "┖ <b>Send:</b> <code>y</code> / <code>yes</code> | <code>n</code> / <code>no</code>",
            btns,
        )

        confirm = await _invoke(user_id)
        if await _stop_or_timeout(confirm, sess_msg, h, c_phone):
            return
        if confirm.lower() in ("y", "yes"):
            c = c_phone
            break

    try:
        pyro_client = Client(
            f"WZML-X-{user_id}",
            in_memory=True,
            api_id=api_id,
            api_hash=api_hash,
            workdir="/usr/src/app",
            app_version=f"@WZML_X {get_version()}",
            device_model="@WZML_X Bot V3",
            system_version="@WZML_X WzPyro Server",
        )
    except Exception as e:
        return await edit_message(
            sess_msg, _error_msg(h, c, f"<b>Client Error:</b> <i>{e}</i>")
        )

    try:
        await pyro_client.connect()
    except ConnectionError:
        await _safe_disconnect(pyro_client)
        await pyro_client.connect()

    try:
        user_code = await pyro_client.send_code(phone_no)
    except FloodWait as e:
        await _safe_disconnect(pyro_client)
        return await edit_message(
            sess_msg,
            _error_msg(
                h,
                c,
                f"<b>FloodWait:</b> <i>Retry after {get_readable_time(e.value)}.</i>",
            ),
        )
    except ApiIdInvalid:
        await _safe_disconnect(pyro_client)
        return await edit_message(
            sess_msg,
            _error_msg(
                h,
                c,
                "<i><code>API_ID</code> and <code>API_HASH</code> are Invalid.</i>",
            ),
        )
    except PhoneNumberInvalid:
        await _safe_disconnect(pyro_client)
        return await edit_message(
            sess_msg, _error_msg(h, c, "<i>Phone Number is Invalid.</i>")
        )

    await edit_message(
        sess_msg,
        f"{h}\n┃\n{c}\n┃\n"
        "┃ <i>OTP sent to your Phone Number.</i>\n"
        "┃ <i>Enter in <code>1 2 3 4 5</code> format. (Space in between)</i>\n"
        "┃\n"
        f"┖ <b>Timeout:</b> <code>{get_readable_time(_TIMEOUT)}</code>",
        btns,
    )

    otp_str = await _invoke(user_id)
    if await _stop_or_timeout(otp_str, sess_msg, h, c, pyro_client):
        return

    otp = " ".join(str(otp_str).split())

    try:
        if not pyro_client.is_connected:
            await pyro_client.connect()
        await pyro_client.sign_in(phone_no, user_code.phone_code_hash, phone_code=otp)
    except PhoneCodeInvalid:
        await _safe_disconnect(pyro_client)
        return await edit_message(sess_msg, _error_msg(h, c, "<i>OTP is Invalid.</i>"))
    except PhoneCodeExpired:
        await _safe_disconnect(pyro_client)
        return await edit_message(sess_msg, _error_msg(h, c, "<i>OTP has Expired.</i>"))
    except SessionPasswordNeeded:
        hint = await pyro_client.get_password_hint()
        await edit_message(
            sess_msg,
            f"{h}\n┃\n{c}\n┃\n"
            "┃ <i>Account is protected with <b>Two-Step Verification</b>.</i>\n"
            f"┃ <b>Hint:</b> <i>{hint}</i>\n"
            "┃\n"
            "┖ <i>Send your Password Now.</i>",
            btns,
        )

        password = await _invoke(user_id)
        if await _stop_or_timeout(password, sess_msg, h, c, pyro_client):
            return

        try:
            await pyro_client.check_password(password.strip())
        except Exception as e:
            await _safe_disconnect(pyro_client)
            return await edit_message(
                sess_msg, _error_msg(h, c, f"<b>Password Error:</b> <i>{e}</i>")
            )
    except Exception as e:
        await _safe_disconnect(pyro_client)
        return await edit_message(
            sess_msg, _error_msg(h, c, f"<b>Sign In Error:</b> <i>{e}</i>")
        )

    try:
        session_string = await pyro_client.export_session_string()
        await pyro_client.send_message(
            "me",
            f"⌬ <b><u>WZGram Session Generated</u></b>\n\n"
            f"<code>{session_string}</code>\n\n"
            f"<b>WZGram v{wzgram_version} | WZML-X {get_version()}</b>\n"
            f"<b>Via <a href='https://github.com/SilentDemonSD/WZML-X'>WZML-X</a> [ @WZML_X ]</b>",
            disable_web_page_preview=True,
        )
        await _safe_disconnect(pyro_client)
        await edit_message(
            sess_msg,
            f"{h}\n┃\n{c}\n┃\n"
            "┠  <b>WZGram Session Generated Successfully!</b>\n"
            "┃\n"
            "┖ <i>Check your <b>Saved Messages</b>.</i>",
        )
    except Exception as e:
        await _safe_disconnect(pyro_client)
        return await edit_message(
            sess_msg, _error_msg(h, c, f"<b>Export Error:</b> <i>{e}</i>")
        )

    for ext in ("session", "session-journal"):
        path = f"WZML-X-{user_id}.{ext}"
        if path_exists(path):
            try:
                await aioremove(path)
            except Exception:
                pass
