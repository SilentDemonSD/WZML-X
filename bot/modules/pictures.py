from os import remove as osremove, mkdir, path as ospath
from time import sleep
from telegraph import upload_file
from telegram.ext import CommandHandler, CallbackQueryHandler

from bot import dispatcher, LOGGER, config_dict, DATABASE_URL
from bot.helper.telegram_helper.message_utils import sendMessage, editMessage, sendPhoto, deleteMessage, editPhoto
from bot.helper.ext_utils.bot_utils import handleIndex
from bot.helper.telegram_helper.filters import CustomFilters
from bot.helper.ext_utils.db_handler import DbManger
from bot.helper.telegram_helper.button_build import ButtonMaker

def picture_add(update, context):
    editable = sendMessage("<code>Checking Input ...</code>", context.bot, update.message)
    resm = update.message.reply_to_message
    if resm is not None and resm.text:
        msg_text = resm.text
        if msg_text.startswith("http"):
            pic_add = msg_text.strip()
            editMessage("<b>Adding your Link ...</b>", editable)
    elif resm and resm.photo:
        if not (resm.photo and resm.photo[-1].file_size <= 5242880*2):
            editMessage("This Media is Not Supported! Only Send Photos !!", editable)
            return
        path = "Thumbnails/"
        if not ospath.isdir(path):
            mkdir(path)
        photo_dir = resm.photo[-1].get_file().download()
        editMessage("<b>Uploading to telegra.ph Server, Please Wait...</b>", editable)
        sleep(1)
        try:
            pic_add = f'https://graph.org{upload_file(photo_dir)[0]}'
            LOGGER.info(f"Telegraph Link : {pic_add}")
        except Exception as e:
            LOGGER.error(f"Pictures Error: {e}")
            editMessage(str(e), editable)
        finally:
            osremove(photo_dir)
    else:
        help_msg = "<b>By Replying to Link (Telegra.ph or DDL):</b>"
        help_msg += f"\n<code>/addpic" + " {link}" + "</code>\n"
        help_msg += "\n<b>By Replying to Photo on Telegram:</b>"
        help_msg += f"\n<code>/addpic" + " {photo}" + "</code>"
        editMessage(help_msg, editable)
        return
    config_dict['PICS'].append(pic_add)
    if DATABASE_URL:
        DbManger().update_config({'PICS': config_dict['PICS']})
    sleep(1.5)
    editMessage(f"<b><i>Successfully Added to Existing Photos Status List!</i></b>\n\n<b>• Total Pics : </b><code>{len(config_dict['PICS'])}</code>", editable)

def pictures(update, context):
    user_id = update.message.from_user.id
    if not config_dict['PICS']:
        sendMessage("No Photo to Show ! Add by /addpic", context.bot, update.message)
    else:
        to_edit = sendMessage("Generating Grid of your Images...", context.bot, update.message)
        buttons = ButtonMaker()
        buttons.sbutton("<<", f"pics {user_id} turn -1")
        buttons.sbutton(">>", f"pics {user_id} turn 1")
        buttons.sbutton("Remove Photo", f"pics {user_id} remov 0")
        buttons.sbutton("Close", f"pics {user_id} close")
        buttons.sbutton("Remove All", f"pics {user_id} removall", 'footer')
        deleteMessage(context.bot, to_edit)
        sendPhoto(f'🌄 <b>Picture No. : 1 / {len(config_dict["PICS"])}</b>', context.bot, update.message, config_dict['PICS'][0], buttons.build_menu(2))

def pics_callback(update, context):
    query = update.callback_query
    message = query.message
    user_id = query.from_user.id
    data = query.data.split()
    if user_id != int(data[1]) and not CustomFilters.owner_query(user_id):
        query.answer(text="Not Authorized User!", show_alert=True)
        return
    if data[2] == "turn":
        query.answer()
        ind = handleIndex(int(data[3]), config_dict['PICS'])
        no = len(config_dict['PICS']) - abs(ind+1) if ind < 0 else ind + 1
        pic_info = f'🌄 <b>Picture No. : {no} / {len(config_dict["PICS"])}</b>'
        buttons = ButtonMaker()
        buttons.sbutton("<<", f"pics {data[1]} turn {ind-1}")
        buttons.sbutton(">>", f"pics {data[1]} turn {ind+1}")
        buttons.sbutton("Remove Photo", f"pics {data[1]} remov {ind}")
        buttons.sbutton("Close", f"pics {data[1]} close")
        buttons.sbutton("Remove All", f"pics {data[1]} removall", 'footer')
        editPhoto(pic_info, message, config_dict['PICS'][ind], buttons.build_menu(2))
    elif data[2] == "remov":
        config_dict['PICS'].pop(int(data[3]))
        if DATABASE_URL:
            DbManger().update_config({'PICS': config_dict['PICS']})
        query.answer("Photo Successfully Deleted", show_alert=True)
        if len(config_dict['PICS']) == 0:
            query.message.delete()
            sendMessage("No Photo to Show ! Add by /addpic", context.bot, update.message)
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
        editPhoto(pic_info, message, config_dict['PICS'][ind], buttons.build_menu(2))
    elif data[2] == 'removall':
        config_dict['PICS'].clear()
        if DATABASE_URL:
            DbManger().update_config({'PICS': config_dict['PICS']})
        query.answer(text="All Photos Successfully Deleted", show_alert=True)
        query.message.delete()
        sendMessage("No Photo to Show ! Add by /addpic", context.bot, update.message)
    else:
        query.answer()
        query.message.delete()
        query.message.reply_to_message.delete()


picture_add_handler = CommandHandler('addpic', picture_add,
                                    filters=CustomFilters.owner_filter | CustomFilters.sudo_user)
pictures_handler = CommandHandler('pics', pictures,
                                    filters=CustomFilters.owner_filter | CustomFilters.sudo_user)
pic_call_handler = CallbackQueryHandler(pics_callback, pattern="pics")

dispatcher.add_handler(picture_add_handler)
dispatcher.add_handler(pictures_handler)
dispatcher.add_handler(pic_call_handler)
