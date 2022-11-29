from os import remove as osremove, mkdir, path as ospath
from time import sleep
from telegraph import upload_file

from bot import user_data, dispatcher, LOGGER, config_dict, DATABASE_URL, OWNER_ID
from bot.helper.telegram_helper.message_utils import sendMessage, sendMarkup, editMessage, sendPhoto

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

def pictures(client: Client, message: Message):
    '''/pics command'''
    if not PICS_LIST:
        await message.reply_text("Add Some Photos OR use API to Let me Show you !!")
    else:
        to_edit = await message.reply_text("Generating Grid of your Images...")
        btn = [
            [InlineKeyboardButton("<<", callback_data=f"pic -1"),
            InlineKeyboardButton(">>", callback_data="pic 1")],
            [InlineKeyboardButton("Remove Photo", callback_data="picsremove 0")]
        ]
        await to_edit.delete()
        await message.reply_photo(photo=PICS_LIST[0], caption=f'• Picture No. : 1 / {len(PICS_LIST)}', reply_markup=InlineKeyboardMarkup(btn))

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
users_settings_handler = CommandHandler(BotCommands.UsersCommand, send_users_settings,
                                            filters=CustomFilters.owner_filter | CustomFilters.authorized_user, run_async=True)
user_set_handler  = CommandHandler(BotCommands.UserSetCommand, user_settings,
                                   filters=CustomFilters.authorized_chat | CustomFilters.authorized_user, run_async=True)
but_set_handler = CallbackQueryHandler(edit_user_settings, pattern="userset", run_async=True)

dispatcher.add_handler(picture_add_handler)
dispatcher.add_handler(but_set_handler)
dispatcher.add_handler(users_settings_handler)
