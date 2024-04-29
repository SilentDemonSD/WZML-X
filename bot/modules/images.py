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
    args = message.command[1:]
    if len(args) > 0:
        msg_text = args[0]
    elif message.reply_to_message:
        msg_text = message.reply_to_message.text or message.reply_to_message.caption
    else:
        await editMessage(editable, "Invalid input. Use /addimage [image_url] or reply to an image.")
        return

    if not msg_text.startswith("http"):
        await editMessage(editable, "Image URL must start with 'http'")
        return

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(msg_text) as resp:
                if resp.status != 200:
                    await editMessage(editable, "Failed to download image.")
                    return
                img_data = await resp.read()
    except Exception as e:
        await editMessage(editable, f"Error: {str(e)}")
        return

    try:
        photo_dir = "photo_{}.jpg".format(int(time.time()))
        await aiofiles.open(photo_dir, 'wb').write(img_data)
        await editMessage(editable, "Uploading image to graph.org...")
        tg_url = await upload_image(photo_dir)
        os.remove(photo_dir)
    except Exception as e:
        await editMessage(editable, f"Error: {str(e)}")
        return

    config_dict['IMAGES'].append(tg_url)
    if DATABASE_URL:
        await DbManger().update_config({'IMAGES': config_dict['IMAGES']})
    await editMessage(editable, f"Successfully added image to the list.\nTotal Images: {len(config_dict['IMAGES'])}")

async def pictures(_, message):
    if not config_dict['IMAGES']:
        await sendMessage(message, "No images to show! Add images using /addimage command.")
        return

    editable = await sendMessage(message, "Generating grid of your images...")
    buttons = ButtonMaker()
    user_id = message.from_user.id
    buttons.ibutton("<<", f"images {user_id} turn -1")
    buttons.ibutton(">>", f"images {user_id} turn 1")
    buttons.ibutton("Remove Image", f"images {user_id} remov 0")
    buttons.ibutton("Close", f"images {user_id} close")
    buttons.ibutton("Remove All", f"images {user_id} removall", 'footer')

    try:
        index = 0
        image_msg = await sendMessage(message, f"🌄 <b>Image No. : 1 / {len(config_dict['IMAGES'])}</b>", buttons.build_menu(2), config_dict['IMAGES'][index])
    except FloodWait as e:
        await asyncio.sleep(e.x)
        image_msg = await sendMessage(message, f"🌄 <b>Image No. : 1 / {len(config_dict['IMAGES'])}</b>", buttons.build_menu(2), config_dict['IMAGES'][index])

    await deleteMessage(editable)

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

        try:
            await editMessage(message, pic_info, buttons.build_menu(2), config_dict['IMAGES'][ind])
        except FloodWait as e:
            await asyncio.sleep(e.x)
            await editMessage(message, pic_info, buttons.build_menu(2), config_dict['IMAGES'][ind])

    elif data[2] == "remov":
        config_dict['IMAGES'].pop(int(data[3]))
        if DATABASE_URL:
            await DbManger().update_config({'IMAGES': config_dict['IMAGES']})
        await query.answer("Image Successfully Deleted", show_alert=True)

        if len(config_dict['IMAGES']) == 0:
            await deleteMessage(query.message)
            await sendMessage(message, f"<b>No Images to Show !</b> Add by /{BotCommands.AddImageCommand}")
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

        try:
            await editMessage(message, pic_info, buttons.build_menu(2), config_dict['IMAGES'][ind])
        except FloodWait as e:
            await asyncio.sleep(e.x)
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

async def upload_image(photo_path):
    try:
        telegraph_client = telegraph.Telegraph()
        response = telegraph_client.create_account(short_name="bot_images")
        auth_url = response["auth_url"]
        telegraph_client.create_page(auth_url, title="Bot Images", html_content=f"<img src='{photo_path}'>")
        page_url = telegraph_client.get_page(auth_url)["path"]
        return f"https://telegra.ph{page_url}"
    except Exception as e:
        LOGGER.error(f"Error uploading image: {str(e)}")
        return None

bot.add_handler(MessageHandler(picture_add, filters=command(BotCommands.AddImageCommand) & CustomFilters.authorized & ~CustomFilters.blacklisted))
bot.add_handler(MessageHandler(pictures, filters=command(BotCommands.ImagesCommand) & CustomFilters.authorized & ~CustomFilters.blacklisted))
bot.add_handler(CallbackQueryHandler(pics_callback, filters=regex(r'^images')))
