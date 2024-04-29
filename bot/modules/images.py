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
                content_type = resp.headers.get("Content-Type")
                if "image" not in content_type:
                    await editMessage(editable, "Invalid image format.")
                    return
                img_data = await resp.read()
    except Exception as e:
        LOGGER.error(f"Error downloading image: {str(e)}")
        await editMessage(editable, f"Error downloading image: {str(e)}")
        return

    try:
        photo_dir = await aiofiles.tempfile.mktemp(suffix=".jpg", dir=config_dict["DOWNLOAD_DIR"])
        await aiofiles.open(photo_dir, 'wb').write(img_data)
        await editMessage(editable, "Uploading image to Telegraph...")
        telegraph_url = await upload_image(photo_dir)
        os.remove(photo_dir)
    except Exception as e:
        LOGGER.error(f"Error uploading image to Telegraph: {str(e)}")
        await editMessage(editable, f"Error uploading image to Telegraph: {str(e)}")
        return

    config_dict["IMAGES"].append(telegraph_url)
    if DATABASE_URL:
        await DbManger().update_config({'IMAGES': config_dict['IMAGES']})
    await editMessage(editable, f"Successfully added image to the list!\nTotal Images: {len(config_dict['IMAGES'])}")

async def pictures(_, message):
    if not config_dict['IMAGES']:
        await sendMessage(message, "No images to show! Add images using /addimage command.")
        return

    to_edit = await sendMessage(message, "Generating grid of your images...")
    buttons = ButtonMaker()
    user_id = message.from_user.id
    buttons.ibutton("<<", f"images {user_id} prev")
    buttons.ibutton(">>", f"images {user_id} next")
    buttons.ibutton("Remove Image", f"images {user_id} remove 0")
    buttons.ibutton("Close", f"images {user_id} close")
    buttons.ibutton("Remove All", f"images {user_id} removeall", 'footer')
    await deleteMessage(to_edit)
    await show_images(message, 0)

async def show_images(message, index):
    buttons = ButtonMaker()
    user_id = message.from_user.id
    max_images_per_row = 3
    start_index = index * max_images_per_row
    end_index = min(start_index + max_images_per_row, len(config_dict["IMAGES"]))
    image_rows = []
    for i in range(start_index, end_index):
        img_url = config_dict["IMAGES"][i]
        img_filename = os.path.basename(urlparse(img_url).path)
        image_rows.append([[telegraph.Image(src=img_url, alt=img_filename)]])

    if index == 0:
        buttons.ibutton("<<", f"images {user_id} prev")
    else:
        buttons.ibutton("<<", f"images {user_id} prev", disabled=True)

    if end_index < len(config_dict["IMAGES"]):
        buttons.ibutton(">>", f"images {user_id} next")
    else:
        buttons.ibutton(">>", f"images {user_id} next", disabled=True)

    buttons.ibutton("Remove Image", f"images {user_id} remove {index}", 'footer')
    buttons.ibutton("Close", f"images {user_id} close", 'footer')

    if image_rows:
        img_str = telegraph.Page(image_rows, title="Images").content
        await sendMessage(message, f"<b>Images {start_index+1} to {end_index} of {len(config_dict['IMAGES'])}</b>", buttons.build_menu(2), img_str)
    else:
        await sendMessage(message, f"<b>No images to show! Add images using /addimage command.</b>")

async def pics_callback(_, query):
    message = query.message
    user_id = query.from_user.id
    data = query.data.split()
    if user_id != int(data[1]):
        await query.answer(text="Not Authorized User!", show_alert=True)
        return

    if data[2] == "prev":
        index = int(data[3]) - 1
        await query.answer()
        await show_images(message, index)
    elif data[2] == "next":
        index = int(data[3]) + 1
        await query.answer()
        await show_images(message, index)
    elif data[2] == "remove":
        index = int(data[3])
        config_dict["IMAGES"].pop(index)
        if DATABASE_URL:
            await DbManger().update_config({'IMAGES': config_dict['IMAGES']})
        await query.answer("Image removed successfully.", show_alert=True)
        if len(config_dict['IMAGES']) == 0:
            await deleteMessage(message)
            await sendMessage(message, f"<b>No images to show! Add images using /addimage command.</b>")
            return
        await show_images(message, 0)
    elif data[2] == 'removeall':
        config_dict['IMAGES'].clear()
        if DATABASE_URL:
            await DbManger().update_config({'IMAGES': config_dict['IMAGES']})
        await query.answer("All images removed successfully.", show_alert=True)
        await sendMessage(message, f"<b>No images to show! Add images using /addimage command.</b>")
        await deleteMessage(message)
    else:
        await query.answer()
        await deleteMessage(message)
        if message.reply_to_message:
            await deleteMessage(message.reply_to_message)

async def upload_image(photo_path):
    try:
        response = telegraph.upload_file(photo_path)
        return response["path"]
    except Exception as e:
        LOGGER.error(f"Error uploading image to Telegraph: {str(e)}")
        raise e

bot.add_handler(MessageHandler(picture_add, filters=command(BotCommands.AddImageCommand) & CustomFilters.authorized & ~CustomFilters.blacklisted))
bot.add_handler(MessageHandler(pictures, filters=command(BotCommands.ImagesCommand) & CustomFilters.authorized & ~CustomFilters.blacklisted))
bot.add_handler(CallbackQueryHandler(pics_callback, filters=regex(r'^images')))
