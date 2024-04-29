#!/usr/bin/env python3
import asyncio
import os
import re
from urllib.parse import urlparse

import aiofiles
import aiohttp
import telegraph
from pyrogram.handlers import MessageHandler, CallbackQueryHandler
from pyrogram.filters import command, regex
from pyrogram.errors import FloodWait

from bot import bot, LOGGER, config_dict, DATABASE_URL
from bot.helper.telegram_helper.message_utils import sendMessage, editMessage, deleteMessage
from bot.helper.ext_utils.bot_utils import handleIndex, new_task
from bot.helper.telegram_helper.filters import CustomFilters
from bot.helper.telegram_helper.bot_commands import BotCommands
from bot.helper.ext_utils.db_handler import DbManger
from bot.helper.telegram_helper.button_build import ButtonMaker

async def picture_add(_, message):
    editable = await sendMessage(message, "Fetching Input...")
    args = message.command[1:] if message.command else message.text.split()
    if len(args) < 1:
        return await editMessage(editable, "Invalid input. Use /addimage [image_url] or reply to an image.")

    if re.match(r'^https?://', args[0]):
        pic_add = args[0].strip()
    elif message.reply_to_message and message.reply_to_message.photo:
        pic_add = await download_image(message.reply_to_message)
    else:
        return await editMessage(editable, "Invalid image URL or not a reply to an image.")

    config_dict['IMAGES'].append(pic_add)
    if DATABASE_URL:
        await DbManger().update_config({'IMAGES': config_dict['IMAGES']})
    await editMessage(editable, f"Successfully added to Images List!\n• Total Images: {len(config_dict['IMAGES'])}")


async def pictures(_, message):
    if not config_dict['IMAGES']:
        await sendMessage(message, "No photos to show! Add photos by /addimage command.")
        return

    to_edit = await sendMessage(message, "Generating grid of your images...")
    buttons = ButtonMaker()
    buttons.ibutton("<<", f"images {message.from_user.id} turn -1")
    buttons.ibutton(">>", f"images {message.from_user.id} turn 1")
    buttons.ibutton("Remove Image", f"images {message.from_user.id} remov 0")
    buttons.ibutton("Close", f"images {message.from_user.id} close")
    buttons.ibutton("Remove All", f"images {message.from_user.id} removall", 'footer')
    await deleteMessage(to_edit)
    await sendMessage(message, f'🌄 <b>Image No. : 1 / {len(config_dict["IMAGES"])}</b>', buttons.build_menu(2), config_dict['IMAGES'][0])


@new_task
async def pics_callback(_, query):
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
        await editMessage(query.message, pic_info, buttons.build_menu(2), config_dict['IMAGES'][ind])
    elif data[2] == "remov":
        config_dict['IMAGES'].pop(int(data[3]))
        if DATABASE_URL:
            await DbManger().update_config({'IMAGES': config_dict['IMAGES']})
        await query.answer("Image Successfully Deleted", show_alert=True)
        if len(config_dict['IMAGES']) == 0:
            await deleteMessage(query.message)
            await sendMessage(query.message, "No photos to show! Add photos by /addimage command.")
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
        await editMessage(query.message, pic_info, buttons.build_menu(2), config_dict['IMAGES'][ind])
    elif data[2] == 'removall':
        config_dict['IMAGES'].clear()
        if DATABASE_URL:
            await DbManger().update_config({'IMAGES': config_dict['IMAGES']})
        await query.answer("All Images Successfully Deleted", show_alert=True)
        await sendMessage(query.message, "No images to show! Add photos by /addimage command.")
        await deleteMessage(query.message)
    else:
        await query.answer()
        await deleteMessage(query.message)


async def download_image(message):
    try:
        file_path = await message.download()
    except FloodWait as e:
        await asyncio.sleep(e.x)
        file_path = await message.download()
    except Exception as e:
        LOGGER.error(f"Error downloading image: {str(e)}")
        return None

    url = urlparse(message.reply_to_message.photo.file_unique_id)
    file_name = f"{url.hostname}.jpg"
    new_file_path = os.path.join("temp_images", file_name)
    os.makedirs(os.path.dirname(new_file_path), exist_ok=True)
    async with aiofiles.open(file_path, 'rb') as f:
        async with aiofiles.open(new_file_path, 'wb') as out_f:
            while content := await f.read(4096):
                await out_f.write(content)
    os.remove(file_path)
    return new_file_path


bot.add_handler(MessageHandler(picture_add, filters=command(BotCommands.AddImageCommand) & CustomFilters.authorized & ~CustomFilters.blacklisted))
bot.add_handler(MessageHandler(pictures, filters=command(BotCommands.ImagesCommand) & CustomFilters.authorized & ~CustomFilters.blacklisted))
bot.add_handler(CallbackQueryHandler(pics_callback, filters=regex(r'^images')))
