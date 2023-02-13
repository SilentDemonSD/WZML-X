from os import remove as osremove, mkdir, path as ospath
from asyncio import sleep as asleep
from telegraph import upload_file
from pyrogram import filters, Client
from pyrogram.types import Message, CallbackQuery

from bot import bot, LOGGER, config_dict, DATABASE_URL
from bot.helper.telegram_helper.message_utils import sendMessage, editMessage, sendPhoto, deleteMessage, editPhoto
from bot.helper.ext_utils.bot_utils import handleIndex
from bot.helper.telegram_helper.filters import CustomFilters
from bot.helper.ext_utils.db_handler import DbManger
from bot.helper.telegram_helper.button_build import ButtonMaker


@bot.on_message(filters.command("addpic") & (CustomFilters.owner_filter | CustomFilters.sudo_user))
async def picture_add(c: Client, message: Message):
    editable = await sendMessage("<code>Checking Input ...</code>", c, message)
    resm = message.reply_to_message
    if resm is not None and resm.text:
        msg_text = resm.text
        if msg_text.startswith("http"):
            pic_add = msg_text.strip()
            await editMessage("<b>Adding your Link ...</b>", editable)
    elif resm and resm.photo:
        if not (resm.photo and resm.photo.file_size <= 5242880*2):
            await editMessage("This Media is Not Supported! Only Send Photos !!", editable)
            return
        path = "Thumbnails/"
        if not ospath.isdir(path):
            mkdir(path)
        photo_dir = await resm.download()
        await editMessage("<b>Uploading to telegra.ph Server, Please Wait...</b>", editable)
        await asleep(1)
        try:
            pic_add = f'https://graph.org{upload_file(photo_dir)[0]}'
            LOGGER.info(f"Telegraph Link : {pic_add}")
        except Exception as e:
            LOGGER.error(f"Pictures Error: {e}")
            await editMessage(str(e), editable)
        finally:
            osremove(photo_dir)
    else:
        help_msg = "<b>By Replying to Link (Telegra.ph or DDL):</b>"
        help_msg += f"\n<code>/addpic" + " {link}" + "</code>\n"
        help_msg += "\n<b>By Replying to Photo on Telegram:</b>"
        help_msg += f"\n<code>/addpic" + " {photo}" + "</code>"
        await editMessage(help_msg, editable)
        return
    config_dict['PICS'].append(pic_add)
    if DATABASE_URL:
        DbManger().update_config({'PICS': config_dict['PICS']})
    await asleep(1.5)
    await editMessage(f"<b><i>Successfully Added to Existing Photos Status List!</i></b>\n\n<b>• Total Pics : </b><code>{len(config_dict['PICS'])}</code>", editable)


@bot.on_message(filters.command("pics") & (CustomFilters.owner_filter | CustomFilters.sudo_user))
async def pictures(c: Client, message: Message):
    user_id = message.from_user.id
    if not config_dict['PICS']:
        await sendMessage("No Photo to Show ! Add by /addpic", c, message)
    else:
        to_edit = await sendMessage("Generating Grid of your Images...", c, message)
        buttons = ButtonMaker()
        buttons.sbutton("<<", f"pics {user_id} turn -1")
        buttons.sbutton(">>", f"pics {user_id} turn 1")
        buttons.sbutton("Remove Photo", f"pics {user_id} remov 0")
        buttons.sbutton("Close", f"pics {user_id} close")
        buttons.sbutton("Remove All", f"pics {user_id} removall", 'footer')
        await deleteMessage(c, to_edit)
        await sendPhoto(f'🌄 <b>Picture No. : 1 / {len(config_dict["PICS"])}</b>', c, message, photo=config_dict['PICS'][0], reply_markup=buttons.build_menu(2))


@bot.on_callback_query(filters.regex(r"^pics"))
async def pics_callback(c: Client, query: CallbackQuery):
    message = query.message
    user_id = query.from_user.id
    data = query.data.split()
    if user_id != int(data[1]) and not CustomFilters.owner_query(user_id):
        await query.answer(text="Not Authorized User!", show_alert=True)
        return
    if data[2] == "turn":
        await query.answer()
        ind = handleIndex(int(data[3]), config_dict['PICS'])
        no = len(config_dict['PICS']) - abs(ind+1) if ind < 0 else ind + 1
        pic_info = f'🌄 <b>Picture No. : {no} / {len(config_dict["PICS"])}</b>'
        buttons = ButtonMaker()
        buttons.sbutton("<<", f"pics {data[1]} turn {ind-1}")
        buttons.sbutton(">>", f"pics {data[1]} turn {ind+1}")
        buttons.sbutton("Remove Photo", f"pics {data[1]} remov {ind}")
        buttons.sbutton("Close", f"pics {data[1]} close")
        buttons.sbutton("Remove All", f"pics {data[1]} removall", 'footer')
        await editPhoto(pic_info, message, config_dict['PICS'][ind], buttons.build_menu(2))
    elif data[2] == "remov":
        config_dict['PICS'].pop(int(data[3]))
        if DATABASE_URL:
            DbManger().update_config({'PICS': config_dict['PICS']})
        await query.answer("Photo Successfully Deleted", show_alert=True)
        if len(config_dict['PICS']) == 0:
            await query.message.delete()
            await sendMessage("No Photo to Show ! Add by /addpic", c, message)
            return
        ind = int(data[3])+1
        ind = len(config_dict['PICS']) - abs(ind) if ind < 0 else ind
        pic_info = f'🌄 <b>Picture No. : {ind+1} / {len(config_dict["PICS"])}</b>'
        buttons = ButtonMaker()
        buttons.sbutton("<<", f"pics {data[1]} turn {ind-1}")
        buttons.sbutton(">>", f"pics {data[1]} turn {ind+1}")
        buttons.sbutton("Remove Photo", f"pics {data[1]} remov {ind}")
        buttons.sbutton("Close", f"pics {data[1]} close")
        buttons.sbutton("Remove All", f"pics {data[1]} removall", 'footer')
        await editPhoto(pic_info, message, config_dict['PICS'][ind], buttons.build_menu(2))
    elif data[2] == 'removall':
        config_dict['PICS'].clear()
        if DATABASE_URL:
            DbManger().update_config({'PICS': config_dict['PICS']})
        await query.answer(text="All Photos Successfully Deleted", show_alert=True)
        await query.message.delete()
        await sendMessage("No Photo to Show ! Add by /addpic", c, message)
    else:
        await query.answer()
        await query.message.delete()
        await query.message.reply_to_message.delete()
