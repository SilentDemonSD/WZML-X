#!/usr/bin/env python3
from asyncio import sleep as asleep
from aiofiles.os import path as aiopath, remove as aioremove, mkdir
from telegraph import upload_file

from pyrogram.handlers import MessageHandler, CallbackQueryHandler
from pyrogram.filters import command, regex

from bot import bot, LOGGER, config_dict, DATABASE_URL
from bot.helper.telegram_helper.message_utils import sendMessage, editMessage, deleteMessage
from bot.helper.ext_utils.bot_utils import handleIndex, new_task
from bot.helper.telegram_helper.filters import CustomFilters
from bot.helper.telegram_helper.bot_commands import BotCommands
from bot.helper.ext_utils.db_handler import DbManger
from bot.helper.telegram_helper.button_build import ButtonMaker

@new_task
async def picture_add(_, message):
    resm = message.reply_to_message
    editable = await sendMessage(message, "<i>Fetching Input ...</i>")
    if len(message.command) > 1 or resm and resm.text:
        msg_text = resm.text if resm else message.command[1]
        if not msg_text.startswith("http"):
            return await editMessage(editable, "<b>Not a Valid Link, Must Start with 'http'</b>")
        pic_add = msg_text.strip()
        await editMessage(editable, f"<b>Adding your Link :</b> <code>{pic_add}</code>")
    elif resm and resm.photo:
        if resm.photo.file_size > 5242880 * 2:
            return await editMessage(editable, "<i>Media is Not Supported! Only Photos!!</i>")
        try:
            photo_dir = await resm.download()
            await editMessage(editable, "<b>Now, Uploading to <code>graph.org</code>, Please Wait...</b>")
            await asleep(1)
            pic_add = f'https://graph.org{upload_file(photo_dir)[0]}'
            LOGGER.info(f"Telegraph Link : {pic_add}")
        except Exception as e:
            LOGGER.error(f"Images Error: {str(e)}")
            await editMessage(editable, str(e))
        finally:
            await aioremove(photo_dir)
    else:
        help_msg = "<b>By Replying to Link (Telegra.ph or DDL):</b>"
        help_msg += f"\n<code>/{BotCommands.AddImageCommand}" + " {link}" + "</code>\n"
        help_msg += "\n<b>By Replying to Photo on Telegram:</b>"
        help_msg += f"\n<code>/{BotCommands.AddImageCommand}" + " {photo}" + "</code>"
        return await editMessage(editable, help_msg)
    config_dict['IMAGES'].append(pic_add)
    if DATABASE_URL:
        await DbManger().update_config({'IMAGES': config_dict['IMAGES']})
    await asleep(1.5)
    await editMessage(editable, f"<b><i>Successfully Added to Images List!</i></b>\n\n<b>• Total Images : {len(config_dict['IMAGES'])}</b>")


async def pictures(_, message):
    if not config_dict['IMAGES']:
        await sendMessage(message, f"<b>No Photo to Show !</b> Add by /{BotCommands.AddImageCommand}")
    else:
        to_edit = await sendMessage(message, "<i>Generating Grid of your Images...</i>")
        buttons = ButtonMaker()
        user_id = message.from_user.id
        buttons.ibutton("<<", f"images {user_id} turn -1")
        buttons.ibutton(">>", f"images {user_id} turn 1")
        buttons.ibutton("Remove Image", f"images {user_id} remov 0")
        buttons.ibutton("Close", f"images {user_id} close")
        buttons.ibutton("Remove All", f"images {user_id} removall", 'footer')
        await deleteMessage(to_edit)
        await sendMessage(message, f'🌄 <b>Image No. : 1 / {len(config_dict["IMAGES"])}</b>', buttons.build_menu(2), config_dict['IMAGES'][0])


@new_task
async def pics_callback(_, query):
    message = query.message
    user_id = query.from_user.id
    data = query.data.split()
    if user_id != int(data[1]):
        await query.answer(text="Not Authorized User!", show_alert=True)
        return
    if data[2] == "turn":
        await query.answer()
        ind = handleIndex(int(data[3]), config_dict['IMAGES'])
        no = len(config_dict['IMAGES']) - abs(ind+1) if ind < 0 else ind + 1
        pic_info = f'🌄 <b>Image No. : {no} / {len(config_dict["IMAGES"])}</b>'
        buttons = ButtonMaker()
        buttons.ibutton("<<", f"images {data[1]} turn {ind-1}")
        buttons.ibutton(">>", f"images {data[1]} turn {ind+1}")
        buttons.ibutton("Remove Image", f"images {data[1]} remov {ind}")
        buttons.ibutton("Close", f"images {data[1]} close")
        buttons.ibutton("Remove All", f"images {data[1]} removall", 'footer')
        await editMessage(message, pic_info, buttons.build_menu(2), config_dict['IMAGES'][ind])
    elif data[2] == "remov":
        config_dict['IMAGES'].pop(int(data[3]))
        if DATABASE_URL:
            await DbManger().update_config({'IMAGES': config_dict['IMAGES']})
        query.answer("Image Successfully Deleted", show_alert=True)
        if len(config_dict['IMAGES']) == 0:
            await deleteMessage(query.message)
            await sendMessage(message, f"<b>No Photo to Show !</b> Add by /{BotCommands.AddImageCommand}")
            return
        ind = int(data[3])+1
        ind = len(config_dict['IMAGES']) - abs(ind) if ind < 0 else ind
        pic_info = f'🌄 <b>Image No. : {ind+1} / {len(config_dict["IMAGES"])}</b>'
        buttons = ButtonMaker()
        buttons.ibutton("<<", f"images {data[1]} turn {ind-1}")
        buttons.ibutton(">>", f"images {data[1]} turn {ind+1}")
        buttons.ibutton("Remove Image", f"images {data[1]} remov {ind}")
        buttons.ibutton("Close", f"images {data[1]} close")
        buttons.ibutton("Remove All", f"images {data[1]} removall", 'footer')
        await editMessage(message, pic_info, buttons.build_menu(2), config_dict['IMAGES'][ind])
    elif data[2] == 'removall':
        config_dict['IMAGES'].clear()
        if DATABASE_URL:
            await DbManger().update_config({'IMAGES': config_dict['IMAGES']})
        await query.answer("All Images Successfully Deleted", show_alert=True)
        await sendMessage(message, f"<b>No Images to Show !</b> Add by /{BotCommands.AddImageCommand}")
        await deleteMessage(message)
    else:
        await query.answer()
        await deleteMessage(message)
        if message.reply_to_message:
            await deleteMessage(message.reply_to_message)


bot.add_handler(MessageHandler(picture_add, filters=command(BotCommands.AddImageCommand) & CustomFilters.authorized & ~CustomFilters.blacklisted))
bot.add_handler(MessageHandler(pictures, filters=command(BotCommands.ImagesCommand) & CustomFilters.authorized & ~CustomFilters.blacklisted))
bot.add_handler(CallbackQueryHandler(pics_callback, filters=regex(r'^images')))
