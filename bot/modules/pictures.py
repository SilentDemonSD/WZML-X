from os import remove as osremove, mkdir, path as ospath
from time import sleep
from telegraph import upload_file
from telegram.ext import Updater, CommandHandler, CallbackQueryHandler, ConversationHandler

from bot import user_data, dispatcher, LOGGER, config_dict, DATABASE_URL, OWNER_ID
from bot.helper.telegram_helper.message_utils import sendMessage, sendMarkup, editMessage, sendPhoto, deleteMessage
from bot.helper.telegram_helper.filters import CustomFilters
from bot.helper.telegram_helper.bot_commands import BotCommands
from bot.helper.telegram_helper.button_build import ButtonMaker

def picture_add(update, context):
    message = update.message
    editable = sendMessage("Checking Input ...", context.bot, update.message)
    resm = message.reply_to_message
    if resm.text:
        msg_text = resm.text
        if msg_text.startswith("http"):
            pic_add = msg_text.strip()
            editMessage("Adding your Link ...", editable)
    elif resm.photo:
        if not (resm.photo and resm.photo.file_size <= 5242880*2):
            editMessage("This Media is Not Supported! Only Send Photos !!", editable)
            return
        editMessage("Uploading to telegra.ph Server ...", editable)
        path = "Thumbnails/"
        if not ospath.isdir(path):
            mkdir(path)
        photo_dir = resm.photo[-1].get_file().download()
        editMessage("`Uploading to te.legra.ph Server, Please Wait...`", editable)
        try:
            tgh_post = upload_file(photo_dir)
            pic_add = f'https://graph.org{tgh_post[0]}'
        except Exception as e:
            editMessage(str(e), editable)
        finally:
            osremove(photo_dir)
    else:
        editMessage("Reply to Any Valid Photo!! Or Provide Direct DL Links of Images.", editable)
        return
    config_dict['PICS'].append(pic_add)
    sleep(1.5)
    editMessage("<b><i>Added to Existing Random Pictures Status List!</i></b>", editable)

def pictures(update, context):
    if not PICS:
        sendMessage("Add Some Photos OR use API to Let me Show you !!", context.bot, update.message)
    else:
        to_edit = sendMessage("Generating Grid of your Images...", context.bot, update.message)
        buttons = ButtonMaker()
        buttons.sbutton("<<", f"pic -1")
        buttons.sbutton(">>", "pic 1")
        buttons.sbutton("Remove Photo", "picsremove 0")
        deleteMessage(context.bot, to_edit)
        sendPhoto(f'• Picture No. : 1 / {len(PICS)}', context.bot, update.message, PICS[0], buttons.build_menu(2))

def pics_callback(client: Client, query: CallbackQuery):
    if query.data.startswith("pic"):
        if query.data.startswith("picsremove"):
            getData = (query.data).split()
            index = int(getData[1])
            PICS_LIST.pop(index)
            await query.edit_message_media(media=InputMediaPhoto(media="https://te.legra.ph/file/06dbd8fb0628b8ba4ab45.png", caption="Removed from Existing Random Pictures Status List !!"))
            return
        getData = (query.data).split()
        ind = int(getData[1])
        no = len(PICS_LIST) - abs(ind+1) if ind < 0 else ind + 1
        pic_info = f'🌄 <b>Picture No. : {no} / {len(PICS_LIST)}</b>'
        btns = [
            [InlineKeyboardButton("<<", callback_data=f"pic {ind-1}"),
            InlineKeyboardButton(">>", callback_data=f"pic {ind+1}")],
            [InlineKeyboardButton("Remove Photo", callback_data=f"picsremove {ind}")]
        ]
        await query.edit_message_media(media=InputMediaPhoto(media=PICS_LIST[ind], caption=pic_info), reply_markup=InlineKeyboardMarkup(btns))
    query.answer()

picture_add_handler = CommandHandler('addpic', picture_add,
                                    filters=CustomFilters.owner_filter | CustomFilters.authorized_user, run_async=True)
pictures_handler = CommandHandler('pics', pictures,
                                    filters=CustomFilters.owner_filter | CustomFilters.authorized_user, run_async=True)
but_set_handler = CallbackQueryHandler(edit_user_settings, pattern="userset", run_async=True)

dispatcher.add_handler(picture_add_handler)
dispatcher.add_handler(pictures_handler)
dispatcher.add_handler(users_settings_handler)
