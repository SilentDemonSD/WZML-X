from pyrogram.enums import ButtonStyle

from .. import bot_cache, bot_loop, categories_dict, user_data
from ..core.config_manager import Config
from ..helper.ext_utils.bot_utils import arg_parser, fetch_drive_cat, new_task
from ..helper.ext_utils.links_utils import is_gdrive_link
from ..helper.listeners.task_listener import TaskListener
from ..helper.mirror_leech_utils.gdrive_utils.clean import GoogleDriveClean
from ..helper.telegram_helper.button_build import ButtonMaker
from ..helper.telegram_helper.message_utils import (
    edit_message,
    open_drive_clean,
    send_message,
)


class GDClean(TaskListener):
    def __init__(self, client, message):
        self.message = message
        self.client = client
        super().__init__()

    async def new_event(self):
        args = self.message.text.split()
        arg_base = {"link": "", "-gc": ""}
        arg_parser(args[1:], arg_base)
        link = arg_base["link"]
        gc_name = arg_base["-gc"]
        if reply_to := self.message.reply_to_message:
            reply_text = reply_to.text or reply_to.caption or ""
            if reply_text:
                link = reply_text.split(maxsplit=1)[0].strip()
        if link and not is_gdrive_link(link):
            return await send_message(
                self.message,
                "Provide a valid GDrive link or use /gdclean -gc <category>",
            )
        self.link = link
        obj = GoogleDriveClean(self)
        if gc_name:
            cat_name = gc_name.replace("_", " ")
            default_id = (
                user_data.get(self.user_id, {}).get("GDRIVE_ID") or Config.GDRIVE_ID
            )
            default_index = (
                user_data.get(self.user_id, {}).get("INDEX_URL") or Config.INDEX_URL
            )
            merged = {
                "Default": {"drive_id": default_id, "index_link": default_index},
                **fetch_drive_cat(self.user_id),
                **categories_dict,
            }
            if cat_name not in merged:
                return await send_message(
                    self.message, f"Category '{cat_name}' not found"
                )
            drive_id = merged[cat_name].get("drive_id")
            if not drive_id:
                return await send_message(
                    self.message, f"Category '{cat_name}' has no drive ID"
                )
            await obj.start(drive_id=drive_id)
        elif link:
            await obj.start(link=link)
        else:
            drive_id, is_cancelled, cat_name = await open_drive_clean(self.message)
            if is_cancelled:
                return
            if not drive_id:
                return await send_message(self.message, "No drive ID selected")
            await obj.start(drive_id=drive_id, cat_name=cat_name)


@new_task
async def drive_clean(client, message):
    bot_loop.create_task(GDClean(client, message).new_event())


@new_task
async def confirm_drive_clean_cb(_, query):
    user_id = query.from_user.id
    data = query.data.split(maxsplit=3)
    msg_id = int(data[2])
    if msg_id not in bot_cache:
        return await edit_message(query.message, "<b>Session Expired</b>")
    elif user_id != int(data[1]):
        return await query.answer(text="This task is not for you!", show_alert=True)
    cat_name = data[3]
    if cat_name == "ccancel":
        bot_cache[msg_id][1] = True
        return
    if cat_name == "cstart":
        if bot_cache[msg_id][0]:
            bot_cache[msg_id][2] = True
        return
    await query.answer()
    merged = {
        "Default": {
            "drive_id": user_data.get(user_id, {}).get("GDRIVE_ID") or Config.GDRIVE_ID,
            "index_link": user_data.get(user_id, {}).get("INDEX_URL")
            or Config.INDEX_URL,
        },
        **fetch_drive_cat(user_id),
        **categories_dict,
    }
    selected_id = merged.get(cat_name, {}).get("drive_id")
    bot_cache[msg_id][0] = selected_id
    bot_cache[msg_id][4] = cat_name
    buttons = ButtonMaker()
    for name in merged:
        selected = cat_name == name
        buttons.data_button(
            f"{'✓️' if selected else ''} {name}",
            f"gdccat {user_id} {msg_id} {name}",
        )
    if selected_id:
        buttons.data_button(
            "Start Cleaning",
            f"gdccat {user_id} {msg_id} cstart",
            style=ButtonStyle.DANGER,
        )
    buttons.data_button(
        "Cancel",
        f"gdccat {user_id} {msg_id} ccancel",
        position="footer",
        style=ButtonStyle.DANGER,
    )
    await edit_message(
        query.message,
        f"<b>Select Drive Category to Clean</b>\n\n"
        f"<b>Category:</b> <code>{cat_name}</code>\n\n"
        f"<b>Timeout:</b> 60 sec",
        buttons.build_menu(3),
    )
