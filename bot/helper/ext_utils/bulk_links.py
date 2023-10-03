#!/usr/bin/env python3
import re
from aiofiles import open as aiopen
from aiofiles.os import remove
from bot.helper.ext_utils.bot_utils import URL_REGEX, MAGNET_REGEX

async def get_links_from_message(text, bulk_start, bulk_end):
    links_list = text.split('\n')
    links_list = [item.strip() for item in links_list if len(item) != 0]

    if bulk_start != 0 and bulk_end != 0:
        links_list = links_list[bulk_start:bulk_end]
    elif bulk_start != 0:
        links_list = links_list[bulk_start:]
    elif bulk_end != 0:
        links_list = links_list[:bulk_end]

    return links_list


async def get_links_from_file(message, bulk_start, bulk_end):
    links_list = []
    text_file_dir = await message.download()

    async with aiopen(text_file_dir, 'r+') as f:
        content = await f.read()

    # Use the imported regex patterns to find URLs and magnet links in the file content
    urls = re.findall(URL_REGEX, content)
    magnet_links = re.findall(MAGNET_REGEX, content)

    # Combine the lists if needed
    links_list = urls + magnet_links


    if bulk_start != 0 and bulk_end != 0:
        links_list = links_list[bulk_start:bulk_end]
    elif bulk_start != 0:
        links_list = links_list[bulk_start:]
    elif bulk_end != 0:
        links_list = links_list[:bulk_end]

    await remove(text_file_dir)

    return links_list


async def extract_bulk_links(message, bulk_start, bulk_end):
    bulk_start = int(bulk_start)
    bulk_end = int(bulk_end)
    if (reply_to := message.reply_to_message) and (file_ := reply_to.document) and (file_.mime_type == 'text/plain'):
        return await get_links_from_file(message.reply_to_message, bulk_start, bulk_end)
    elif text := message.reply_to_message.text:
        return await get_links_from_message(text, bulk_start, bulk_end)
    return []
