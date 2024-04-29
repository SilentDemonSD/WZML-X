from os import remove as osremove, mkdir, path as ospath
from time import sleep
from telegraph import upload_file
from telegram.ext import CommandHandler, CallbackQueryHandler
from typing import Optional, List, Union

from bot import dispatcher, LOGGER, config_dict, DATABASE_URL
from bot.helper.telegram_helper.message_utils import sendMessage, editMessage, sendPhoto, deleteMessage, editPhoto
from bot.helper.ext_utils.bot_utils import handleIndex
from bot.helper.telegram_helper.filters import CustomFilters
from bot.helper.ext_utils.db_handler import DbManger
from bot.helper.telegram_helper.button_build import ButtonMaker

def picture_add(update: telegram.Update, context: telegram.ext.CallbackContext) -> None:
    """Add a photo to the 'PICS' list in the config.

    The photo can be either a link or a photo replied to the command message.

    Args:
        update (telegram.Update): The update object containing the command message.
        context (telegram.ext.CallbackContext): The context object containing the dispatcher and other information.
    """
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
            osremove(photo_dir)
            return
        finally:
            osremove(photo_dir)
    else:
        help_msg = "<b>By Replying to Link (Telegra.ph or DDL):</b>"
        help_msg += f"\n<code>/addpic" + " {link}" + "</code>\n"
        help_msg += "\n<b>By Replying to Photo on Telegram:</b>"
        help_msg += f"\n<code>/addpic" + " {photo}" + "</code>"
        editMessage(help_msg, editable)
        return
    if 'PICS' not in config_dict:
        config_dict['PICS'] = []
    config_dict['PICS'].append(pic_add)
    if DATABASE_URL:
        try:
            DbManger().update_config({'PICS': config_dict['PICS']})
        except Exception as e:
            LOGGER.error(f"Database Error: {e}")
            editMessage("Error updating the config in the database!", editable)
            return
    sleep(1.5)
    editMessage(f"<b><i>Successfully Added to Existing Photos Status List!</i></b>\n\n<b>• Total Pics : </b><code>{len(config_dict['PICS'])}</code>", editable)

def pictures(update: telegram.Update, context: telegram.ext.CallbackContext) -> None:
    """Generate a grid of photos from the 'PICS' list in the config.

    Args:
        update (telegram.Update): The update object containing the command message.
        context (telegram.ext.CallbackContext): The context object containing the dispatcher and other information.
    """
    user_id = update.message.from_user.id
    if not config_dict.get('PICS', []):
        sendMessage("No Photo to Show ! Add by /addpic", context.bot, update.message)
    else:
        to_edit = sendMessage("Generating Grid of your Images...", context.bot, update.message)
        buttons = ButtonMaker()
        buttons.sbutton("<<", f"pics {user_id} turn -1")
        buttons.sbutton(">>", f"pics {user_id} turn 1")
        buttons.sbutton("Remove Photo", f"pics {user_id} remov 0")
        buttons.sbutton("Close", f"pics {user_id} close")
        buttons.sbutton("Remove All", f"pics {user_id} removall", 'footer')
        try:
            sendPhoto(f'🌄 <b>Picture No. : 1 / {len(config_dict["PICS"])}</b>', context.bot, update.message, config_dict['PICS'][0], buttons.build_menu(2))
        except Exception as e:
            LOGGER.error(f"Error sending the picture grid: {e}")
            deleteMessage(context.bot, to_edit)
            sendMessage("Error sending the picture grid!", context.bot, update.message)

def pics_callback(update: telegram.CallbackQuery, context: telegram.ext.CallbackContext) -> None:
    """Handle callback queries for the picture grid.

    Args:
        update (telegram.CallbackQuery): The callback query object containing the query data.
        context (telegram.ext.CallbackContext): The context object containing the dispatcher and other information.
    """
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
        try:
            editPhoto(pic_info, message, config_dict['PICS'][ind], buttons.build_menu(2))
        except Exception as e:
            LOGGER.error(f"Error editing the picture grid: {e}")
            query.answer(text="Error editing the picture grid!", show_alert=True)
    elif data[2] == "remov":
        if int(data[3]) < 0 or int(data[3]) >= len(config_dict['PICS']):
            query.answer(text="Invalid photo index!", show_alert=True)
            return
        config_dict['PICS'].pop(int(data[3]))
        if DATABASE_URL:
            try:
                DbManger().update_config({'PICS': config_dict['PICS']})
            except Exception as e:
                LOGGER.error(f"Database Error: {e}")
                query.answer(text="Error updating the config in the database!", show_alert=True)
                return
        query.answer("Photo Successfully Deleted", show_alert=True)
        if not config_dict['PICS']:
            query.message.delete()
            sendMessage("No Photo to Show ! Add by /addpic", context.bot, update.message)
            return
        ind = int(data[3])
        ind = len(config_dict['PICS']) - abs(ind) if ind < 0 else ind
        pic_info = f'🌄 <b>Picture No. : {ind+1} / {len(config_dict["PICS"])}</b>'
        buttons = ButtonMaker()
        buttons.sbutton("<<", f"pics {data[1]} turn {ind-1}")
        buttons.sbutton(">>", f"pics {data[1]} turn {ind+1}")
        buttons.sbutton("Remove Photo", f"pics {data[1]} remov {ind}")
        buttons.sbutton("Close", f"pics {data[1]} close")
        buttons.sbutton("Remove All", f"pics {data[1]} removall", 'footer')
        try:
            editPhoto(pic_info, message, config_dict['PICS'][ind], buttons.build_menu(2))
        except Exception as e:
            LOGGER.error(f"Error editing the picture grid: {e}")
            query.answer(text="Error editing the picture grid!", show_alert=True)
    elif data[2] == 'removall':
        config_dict['PICS'].clear()
        if DATABASE_URL:
            try:
                DbManger().update_config({'PICS': config_dict['PICS']})
            except Exception as e:
                LOGGER.error(f"Database Error: {e}")
                query.answer(text="Error updating the config in the database!", show_alert=True)
                return
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
dispatcher.add_handler
