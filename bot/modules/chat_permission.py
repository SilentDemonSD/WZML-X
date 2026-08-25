from time import time

from .. import user_data
from ..helper.ext_utils.bot_utils import update_user_ldata, new_task
from ..helper.ext_utils.db_handler import database
from ..helper.telegram_helper.message_utils import send_message


def _parse_time(time_str):
    time_str = time_str.strip().lower()
    mult = {"d": 86400, "h": 3600, "m": 60}
    for suffix, factor in mult.items():
        if time_str.endswith(suffix):
            try:
                return int(time_str[: -len(suffix)]) * factor
            except ValueError:
                return None
    return None


def _format_remaining(seconds):
    if seconds >= 86400:
        d = seconds // 86400
        h = (seconds % 86400) // 3600
        return f"{d}d {h}h" if h else f"{d}d"
    if seconds >= 3600:
        h = seconds // 3600
        m = (seconds % 3600) // 60
        return f"{h}h {m}m" if m else f"{h}h"
    m = seconds // 60
    return f"{m}m"


def _get_blacklist_info(bl_value):
    if not bl_value:
        return False, None
    if bl_value is True:
        return True, "Permanent"
    if isinstance(bl_value, (int, float)):
        remaining = bl_value - time()
        if remaining > 0:
            return True, _format_remaining(int(remaining))
        return False, None
    return False, None


@new_task
async def authorize(_, message):
    msg = message.text.split()
    thread_id = None
    if len(msg) > 1:
        if "|" in msg[1]:
            chat_id, thread_id = list(map(int, msg[1].split("|")))
        else:
            chat_id = int(msg[1].strip())
    elif (reply_to := message.reply_to_message) and (not reply_to.text and not reply_to.caption):
            chat_id = message.chat.id
            thread_id = message.message_thread_id
    elif reply_to:
        chat_id = (reply_to.from_user or reply_to.sender_chat).id
    else:
        if message.is_topic_message:
            thread_id = message.message_thread_id
        chat_id = message.chat.id
    if chat_id in user_data and user_data[chat_id].get("AUTH"):
        if (
            thread_id is not None
            and thread_id in user_data[chat_id].get("thread_ids", [])
            or thread_id is None
        ):
            msg = "Already Authorized!"
        else:
            if "thread_ids" in user_data[chat_id]:
                user_data[chat_id]["thread_ids"].append(thread_id)
            else:
                user_data[chat_id]["thread_ids"] = [thread_id]
            msg = "Authorized"
    else:
        update_user_ldata(chat_id, "AUTH", True)
        if thread_id is not None:
            update_user_ldata(chat_id, "thread_ids", [thread_id])
        await database.update_user_data(chat_id)
        msg = "Authorized"
    await send_message(message, msg)


@new_task
async def unauthorize(_, message):
    msg = message.text.split()
    thread_id = None
    if len(msg) > 1:
        if "|" in msg[1]:
            chat_id, thread_id = list(map(int, msg[1].split("|")))
        else:
            chat_id = int(msg[1].strip())
    elif (reply_to := message.reply_to_message) and (not reply_to.text and not reply_to.caption):
            chat_id = message.chat.id
            thread_id = message.message_thread_id
    elif reply_to:
        chat_id = (reply_to.from_user or reply_to.sender_chat).id
    else:
        if message.is_topic_message:
            thread_id = message.message_thread_id
        chat_id = message.chat.id
    if chat_id in user_data and user_data[chat_id].get("AUTH"):
        if thread_id and thread_id in user_data[chat_id].get("thread_ids", []):
            user_data[chat_id]["thread_ids"].remove(thread_id)
            if not user_data[chat_id].get("thread_ids"):
                update_user_ldata(chat_id, "AUTH", False)
        else:
            update_user_ldata(chat_id, "AUTH", False)
        await database.update_user_data(chat_id)
        msg = "Unauthorized"
    else:
        msg = "Already Unauthorized!"
    await send_message(message, msg)


@new_task
async def add_sudo(_, message):
    id_ = ""
    msg = message.text.split()
    if len(msg) > 1:
        id_ = int(msg[1].strip())
    elif reply_to := message.reply_to_message:
        id_ = (reply_to.from_user or reply_to.sender_chat).id
    if id_:
        if id_ in user_data and user_data[id_].get("SUDO"):
            msg = "Already Sudo!"
        else:
            update_user_ldata(id_, "SUDO", True)
            await database.update_user_data(id_)
            msg = "Promoted as Sudo"
    else:
        msg = "Give ID or Reply To message of whom you want to Promote."
    await send_message(message, msg)


@new_task
async def remove_sudo(_, message):
    id_ = ""
    msg = message.text.split()
    if len(msg) > 1:
        id_ = int(msg[1].strip())
    elif reply_to := message.reply_to_message:
        id_ = (reply_to.from_user or reply_to.sender_chat).id
    if id_:
        if id_ in user_data and user_data[id_].get("SUDO"):
            update_user_ldata(id_, "SUDO", False)
            await database.update_user_data(id_)
            msg = "Demoted"
        else:
            msg = "Already Not Sudo! Sudo users added from config must be removed from config."
    else:
        msg = "Give ID or Reply To message of whom you want to remove from Sudo"
    await send_message(message, msg)


@new_task
async def add_blacklist(_, message):
    msg = message.text.split()
    id_ = None
    time_str = None

    i = 1
    while i < len(msg):
        arg = msg[i].lower()
        if arg.startswith("-t") and len(arg) > 2:
            time_str = arg[2:]
            i += 1
        elif arg == "-t" and i + 1 < len(msg):
            time_str = msg[i + 1]
            i += 2
        else:
            try:
                id_ = int(msg[i])
            except ValueError:
                pass
            i += 1

    if id_ is None and message.reply_to_message:
        id_ = (
            message.reply_to_message.from_user or message.reply_to_message.sender_chat
        ).id

    if id_ is None:
        help_msg = """⌬ <b><u>BlackList Usage</u></b>
│
┠ <b>Permanent:</b> <code>/bl {user_id}</code>
┠ <b>Temporary:</b> <code>/bl {user_id} -t 1d</code>
┠ <b>Reply:</b> <code>/bl -t 2h</code> <i>(reply to user)</i>
┖ <b>Time Format:</b> <code>3d</code> | <code>12h</code> | <code>20m</code> <i>(any digit)</i>"""
        return await send_message(message, help_msg)

    if id_ in user_data and _get_blacklist_info(user_data[id_].get("BLACKLIST"))[0]:
        return await send_message(
            message, f"<b>User Already BlackListed!</b> \u2192 <code>{id_}</code>"
        )

    if time_str:
        seconds = _parse_time(time_str)
        if seconds is None:
            return await send_message(
                message,
                "<b>Invalid Time Format!</b> Use <code>1d</code>, <code>2h</code>, or <code>30m</code>.",
            )
        bl_value = time() + seconds
        remaining = _format_remaining(seconds)
        update_user_ldata(id_, "BLACKLIST", bl_value)
        await database.update_user_data(id_)
        msg = f"""⌬ <b><u>BlackList Applied</u></b>
│
┟ <b>User</b> \u2192 <code>{id_}</code>
┠ <b>Type</b> \u2192 <b>Temporary</b>
┠ <b>Duration</b> \u2192 <code>{remaining}</code>
┖ <b>Expires</b> \u2192 <b>{remaining} from now</b>"""
    else:
        update_user_ldata(id_, "BLACKLIST", True)
        await database.update_user_data(id_)
        msg = f"""⌬ <b><u>BlackList Applied</u></b>
│
┟ <b>User</b> \u2192 <code>{id_}</code>
┠ <b>Type</b> \u2192 <b>Permanent</b>
┖ <b>Status</b> \u2192 <i>Restricted from Bot</i>"""

    await send_message(message, msg)


@new_task
async def remove_blacklist(_, message):
    msg = message.text.split()
    id_ = None

    if len(msg) > 1:
        try:
            id_ = int(msg[1].strip())
        except ValueError:
            pass
    if id_ is None and message.reply_to_message:
        id_ = (
            message.reply_to_message.from_user or message.reply_to_message.sender_chat
        ).id

    if id_ is None:
        return await send_message(
            message,
            "Give ID or Reply To message of whom you want to remove from blacklist",
        )

    bl_value = user_data.get(id_, {}).get("BLACKLIST")
    is_bl, remaining = _get_blacklist_info(bl_value)
    if not is_bl:
        return await send_message(
            message, f"<b>User Already Freed</b> \u2192 <code>{id_}</code>"
        )

    update_user_ldata(id_, "BLACKLIST", False)
    await database.update_user_data(id_)
    await send_message(
        message,
        f"""⌬ <b><u>BlackList Removed</u></b>
│
┟ <b>User</b> \u2192 <code>{id_}</code>
┖ <b>Status</b> \u2192 <i>User Set Free!</i>""",
    )


@new_task
async def black_listed(_, message):
    await send_message(
        message, "<b>BlackListed Detected</b> \u2192 <i>Restricted from Bot</i>"
    )
