#!/usr/bin/env python3
from datetime import datetime
from pyrogram.handlers import MessageHandler, CallbackQueryHandler
from pyrogram.filters import command, regex, create
from aiofiles import open as aiopen
from aiofiles.os import remove as aioremove, path as aiopath, mkdir
from os import path as ospath, getcwd
from PIL import Image
from time import time
from functools import partial
from html import escape
from io import BytesIO
from asyncio import sleep

from bot import OWNER_ID, bot, user_data, config_dict, DATABASE_URL, IS_PREMIUM_USER, MAX_SPLIT_SIZE
from bot.helper.telegram_helper.message_utils import sendMessage, editMessage, sendFile
from bot.helper.telegram_helper.filters import CustomFilters
from bot.helper.telegram_helper.bot_commands import BotCommands
from bot.helper.telegram_helper.button_build import ButtonMaker
from bot.helper.ext_utils.db_handler import DbManger
from bot.helper.ext_utils.bot_utils import getdailytasks, update_user_ldata, get_readable_file_size, sync_to_async, new_thread
from bot.helper.themes import BotTheme

handler_dict = {}
desp_dict = {'rcc': ['RClone is a command-line program to sync files and directories to and from different cloud storage providers like GDrive, OneDrive...', 'Send rclone.conf. Timeout: 60 sec'],
            'lprefix': ['Leech Filename Prefix is the Front Part attacted with the Filename of the Leech Files.', 'Send Leech Filename Prefix. Timeout: 60 sec'],
            'lsuffix': ['Leech Filename Suffix is the End Part attached with the Filename of the Leech Files', 'Send Leech Filename Suffix. Timeout: 60 sec'],
            'lremname': ['Leech Filename Remname is combination of Regex(s) used for removing or manipulating Filename of the Leech Files', 'Send Leech Filename Remname. Timeout: 60 sec'],
            'lcaption': ['Leech Caption is the Custom Caption on the Leech Files Uploaded by the bot', 'Send Leech Caption. You can add HTML tags Timeout: 60 sec'],
            'ldump': ['Leech Files User Dump for Personal Use as a Storage.', 'Send Leech Dump Channel ID. Timeout: 60 sec'],
            'mprefix': ['Mirror Filename Prefix is the Front Part attacted with the Filename of the Mirrored/Cloned Files.', 'Send Mirror Filename Prefix. Timeout: 60 sec'],
            'msuffix': ['Mirror Filename Suffix is the End Part attached with the Filename of the Mirrored/Cloned Files', 'Send Mirror Filename Suffix. Timeout: 60 sec'],
            'mremname': ['Mirror Filename Remname is combination of Regex(s) used for removing or manipulating Filename of the Mirrored/Cloned Files', 'Send Mirror Filename Remname. Timeout: 60 sec'],
            'thumb': ['Custom Thumbnail to appear on the Leeched files uploaded by the bot', 'Send a photo to save it as custom thumbnail. Timeout: 60 sec'],
            'yt_opt': ['YT-DLP Options is the Custom Quality for the extraction of videos from the yt-dlp supported sites.', 'Send YT-DLP Options. Timeout: 60 sec\nFormat: key:value|key:value|key:value.\nExample: format:bv*+mergeall[vcodec=none]|nocheckcertificate:True\nCheck all yt-dlp api options from this <a href="https://github.com/yt-dlp/yt-dlp/blob/master/yt_dlp/YoutubeDL.py#L184">FILE</a> or use this <a href="https://t.me/mltb_official/177">script</a> to convert cli arguments to api options.'],
            'split_size': ['Leech Splits Size is the size to split the Leeched File before uploading', f'Send Leech split size in bytes. IS_PREMIUM_USER: {IS_PREMIUM_USER}. Timeout: 60 sec'],
            'ddl_servers': ['DDL Servers which uploads your File to their Specific Hosting', ''],
            'gofile': ['Gofile is a free file sharing and storage platform. You can store and share your content without any limit.', "Send GoFile's API Key. Get it on https://gofile.io/myProfile"],
            'streamsb': ['StreamSB', "Send StreamSB's API Key"],
            }
fname_dict = {'rcc': 'RClone',
             'lprefix': 'Prefix',
             'lsuffix': 'Suffix',
             'lremname': 'Remname',
             'mprefix': 'Prefix',
             'msuffix': 'Suffix',
             'mremname': 'Remname',
             'ldump': 'Dump',
             'lcaption': 'Caption',
             'thumb': 'Thumbnail',
             'yt_opt': 'YT-DLP Options',
             'split_size': 'Leech Splits',
             'ddl_servers': 'DDL Servers',
             'gofile': 'GoFile',
             'streamsb': 'StreamSB',
             }

async def get_user_settings(from_user, key=None, edit_type=None, edit_mode=None):
    user_id = from_user.id
    name = from_user.mention(style="html")
    buttons = ButtonMaker()
    thumbpath = f"Thumbnails/{user_id}.jpg"
    rclone_path = f'rclone/{user_id}.conf'
    user_dict = user_data.get(user_id, {})
    if key is None:
        buttons.ibutton("Universal Settings", f"userset {user_id} universal")
        buttons.ibutton("Mirror Settings", f"userset {user_id} mirror")
        buttons.ibutton("Leech Settings", f"userset {user_id} leech")
        if user_dict and any(key in user_dict for key in ['lprefix', 'lsuffix', 'lremname', 'ldump', 'ddl_servers', 'yt_opt', 'bot_pm', 'media_group', 'equal_splits', 'split_size', 'rclone', 'thumb', 'as_doc']):
            buttons.ibutton("Reset Setting", f"userset {user_id} reset_all")
        buttons.ibutton("Close", f"userset {user_id} close")

        text = BotTheme('USER_SETTING', NAME=name, ID=user_id, USERNAME=f'@{from_user.username}', LANG=from_user.language_code, DC=from_user.dc_id)
        
        button = buttons.build_menu(1)
    elif key == 'universal':
        buttons.ibutton("YT-DLP Options", f"userset {user_id} yt_opt")
        ytopt = 'Not Exists' if (val:=user_dict.get('yt_opt', config_dict.get('YT_DLP_OPTIONS', ''))) == '' else val
        bot_pm = "Enabled" if user_dict.get('bot_pm', config_dict['BOT_PM']) else "Disabled"
        buttons.ibutton('Disable Bot PM' if bot_pm == 'Enabled' else 'Enable Bot PM', f"userset {user_id} bot_pm")
        if config_dict['BOT_PM']:
            bot_pm = "Force Enabled"
        mediainfo = "Enabled" if user_dict.get('mediainfo', config_dict['SHOW_MEDIAINFO']) else "Disabled"
        buttons.ibutton('Disable MediaInfo' if mediainfo == 'Enabled' else 'Enable MediaInfo', f"userset {user_id} mediainfo")
        if config_dict['SHOW_MEDIAINFO']:
            mediainfo = "Force Enabled"
        dailytl = config_dict['DAILY_TASK_LIMIT'] if config_dict['DAILY_TASK_LIMIT'] else "♾️"
        dailytas = user_dict.get('dly_tasks')[1] if user_dict and user_dict.get('dly_tasks') and user_id != OWNER_ID and config_dict['DAILY_TASK_LIMIT'] else config_dict.get('DAILY_TASK_LIMIT', "♾️") if user_id != OWNER_ID else "♾️"        
        
        if user_dict.get('dly_tasks', False):
            t = str(datetime.now() - user_dict['dly_tasks'][0]).split(':')
            lastused = f"{t[0]}h {t[1]}m {t[2].split('.')[0]}s ago"
        else: lastused = "Bot Not Used"

        text = BotTheme('UNIVERSAL', NAME=name, YT=escape(ytopt), DT=f"{dailytas} / {dailytl}", LAST_USED=lastused, BOT_PM=bot_pm, MEDIAINFO=mediainfo)
        buttons.ibutton("Back", f"userset {user_id} back", "footer")
        buttons.ibutton("Close", f"userset {user_id} close", "footer")
        button = buttons.build_menu(2)
    elif key == 'mirror':
        buttons.ibutton("RClone", f"userset {user_id} rcc")
        rccmsg = "Exists" if await aiopath.exists(rclone_path) else "Not Exists"
        dailytlup = get_readable_file_size(config_dict['DAILY_MIRROR_LIMIT'] * 1024**3) if config_dict['DAILY_MIRROR_LIMIT'] else "∞"
        dailyup = get_readable_file_size(await getdailytasks(user_id, check_mirror=True)) if config_dict['DAILY_MIRROR_LIMIT'] and user_id != OWNER_ID else "️∞"
        buttons.ibutton("Mirror Prefix", f"userset {user_id} mprefix")
        mprefix = 'Not Exists' if (val:=user_dict.get('mprefix', config_dict.get('MIRROR_FILENAME_PREFIX', ''))) == '' else val

        buttons.ibutton("Mirror Suffix", f"userset {user_id} msuffix")
        msuffix = 'Not Exists' if (val:=user_dict.get('msuffix', config_dict.get('MIRROR_FILENAME_SUFFIX', ''))) == '' else val
            
        buttons.ibutton("Mirror Remname", f"userset {user_id} mremname")
        mremname = 'Not Exists' if (val:=user_dict.get('mremname', config_dict.get('MIRROR_FILENAME_REMNAME', ''))) == '' else val

        ddl_serv = len(val.keys()) if (val := user_dict.get('ddl_servers', False)) else 0
        buttons.ibutton("DDL Servers", f"userset {user_id} ddl_servers")

        text = BotTheme('MIRROR', NAME=name, RCLONE=rccmsg, DDL_SERVER=ddl_serv, DM=f"{dailyup} / {dailytlup}", MREMNAME=escape(mremname), MPREFIX=escape(mprefix),
                MSUFFIX=escape(msuffix))
        
        buttons.ibutton("Back", f"userset {user_id} back", "footer")
        buttons.ibutton("Close", f"userset {user_id} close", "footer")
        button = buttons.build_menu(2)
    elif key == 'leech':
        if user_dict.get('as_doc', False) or 'as_doc' not in user_dict and config_dict['AS_DOCUMENT']:
            ltype = "DOCUMENT"
            buttons.ibutton("Send As Media", f"userset {user_id} doc")
        else:
            ltype = "MEDIA"
            buttons.ibutton("Send As Document", f"userset {user_id} doc")

        dailytlle = get_readable_file_size(config_dict['DAILY_LEECH_LIMIT'] * 1024**3) if config_dict['DAILY_LEECH_LIMIT'] else "️∞"
        dailyll = get_readable_file_size(await getdailytasks(user_id, check_leech=True)) if config_dict['DAILY_LEECH_LIMIT'] and user_id != OWNER_ID else "∞"

        buttons.ibutton("Thumbnail", f"userset {user_id} thumb")
        thumbmsg = "Exists" if await aiopath.exists(thumbpath) else "Not Exists"
            
        buttons.ibutton("Leech Splits", f"userset {user_id} split_size")
        split_size = get_readable_file_size(config_dict['LEECH_SPLIT_SIZE']) + ' (Default)' if user_dict.get('split_size', '') == '' else get_readable_file_size(user_dict['split_size'])
        equal_splits = 'Enabled' if user_dict.get('equal_splits', config_dict.get('EQUAL_SPLITS')) else 'Disabled'
        media_group = 'Enabled' if user_dict.get('media_group', config_dict.get('MEDIA_GROUP')) else 'Disabled'

        buttons.ibutton("Leech Caption", f"userset {user_id} lcaption")
        lcaption = 'Not Exists' if (val:=user_dict.get('lcaption', config_dict.get('LEECH_FILENAME_CAPTION', ''))) == '' else val

        buttons.ibutton("Leech Prefix", f"userset {user_id} lprefix")
        lprefix = 'Not Exists' if (val:=user_dict.get('lprefix', config_dict.get('LEECH_FILENAME_PREFIX', ''))) == '' else val

        buttons.ibutton("Leech Suffix", f"userset {user_id} lsuffix")
        lsuffix = 'Not Exists' if (val:=user_dict.get('lsuffix', config_dict.get('LEECH_FILENAME_SUFFIX', ''))) == '' else val
            
        buttons.ibutton("Leech Remname", f"userset {user_id} lremname")
        lremname = 'Not Exists' if (val:=user_dict.get('lremname', config_dict.get('LEECH_FILENAME_REMNAME', ''))) == '' else val

        buttons.ibutton("Leech Dump", f"userset {user_id} ldump")
        ldump = 'Not Exists' if (val:=user_dict.get('ldump', '')) == '' else val

        text = BotTheme('LEECH', NAME=name, DL=f"{dailyll} / {dailytlle}",
                LTYPE=ltype, THUMB=thumbmsg, SPLIT_SIZE=split_size,
                EQUAL_SPLIT=equal_splits, MEDIA_GROUP=media_group,
                LCAPTION=escape(lcaption), LPREFIX=escape(lprefix),
                LSUFFIX=escape(lsuffix), LDUMP=ldump, LREMNAME=escape(lremname))

        buttons.ibutton("Back", f"userset {user_id} back", "footer")
        buttons.ibutton("Close", f"userset {user_id} close", "footer")
        button = buttons.build_menu(2)
    elif key == "ddl_servers":
        ddl_serv = 0
        if (ddl_dict := user_dict.get('ddl_servers', False)):
            for _, (enabled, _) in ddl_dict.items():
                if enabled:
                    ddl_serv += 1
        text = f"㊂ <b><u>{fname_dict[key]} Settings :</u></b>\n\n" \
               f"➲ <b>Enabled DDL Server(s) :</b> <i>{ddl_serv}</i>\n\n" \
               f"➲ <b>Description :</b> <i>{desp_dict[key][0]}</i>"
        for btn in ['gofile', 'streamsb']:
            buttons.ibutton(fname_dict[btn], f"userset {user_id} {btn}")
        buttons.ibutton("Back", f"userset {user_id} back mirror", "footer")
        buttons.ibutton("Close", f"userset {user_id} close", "footer")
        button = buttons.build_menu(2)
    elif edit_type:
        text = f"㊂ <b><u>{fname_dict[key]} Settings :</u></b>\n\n"
        if key == 'rcc':
            set_exist = await aiopath.exists(rclone_path)
            text += f"➲ <b>RClone.Conf File :</b> <i>{'' if set_exist else 'Not'} Exists</i>\n\n"
        elif key == 'thumb':
            set_exist = await aiopath.exists(thumbpath)
            text += f"➲ <b>Custom Thumbnail :</b> <i>{'' if set_exist else 'Not'} Exists</i>\n\n"
        elif key == 'yt_opt':
            set_exist = 'Not Exists' if (val:=user_dict.get('yt_opt', config_dict.get('YT_DLP_OPTIONS', ''))) == '' else val
            text += f"➲ <b>YT-DLP Options :</b> <code>{escape(set_exist)}</code>\n\n"
        elif key == 'split_size':
            set_exist = get_readable_file_size(config_dict['LEECH_SPLIT_SIZE']) + ' (Default)' if user_dict.get('split_size', '') == '' else get_readable_file_size(user_dict['split_size'])
            text += f"➲ <b>Leech Split Size :</b> <i>{set_exist}</i>\n\n"
            if user_dict.get('equal_splits', False) or ('equal_splits' not in user_dict and config_dict['EQUAL_SPLITS']):
                buttons.ibutton("Disable Equal Splits", f"userset {user_id} esplits", "header")
            else:
                buttons.ibutton("Enable Equal Splits", f"userset {user_id} esplits", "header")
            if user_dict.get('media_group', False) or ('media_group' not in user_dict and config_dict['MEDIA_GROUP']):
                buttons.ibutton("Disable Media Group", f"userset {user_id} mgroup", "header")
            else:
                buttons.ibutton("Enable Media Group", f"userset {user_id} mgroup", "header")
        elif key in ['lprefix', 'lremname', 'lsuffix', 'lcaption', 'ldump']:
            set_exist = 'Not Exists' if (val:=user_dict.get(key, config_dict.get(f'LEECH_FILENAME_{key[1:].upper()}', ''))) == '' else val
            text += f"➲ <b>Leech Filename {fname_dict[key]} :</b> {set_exist}\n\n"
        elif key in ['mprefix', 'mremname', 'msuffix']:
            set_exist = 'Not Exists' if (val:=user_dict.get(key, config_dict.get(f'MIRROR_FILENAME_{key[1:].upper()}', ''))) == '' else val
            text += f"➲ <b>Mirror Filename {fname_dict[key]} :</b> {set_exist}\n\n"
        elif key in ['gofile', 'streamsb']:
            set_exist = 'Exists' if key in (ddl_dict:=user_dict.get('ddl_servers', {})) and ddl_dict[key][1] and ddl_dict[key][1] != '' else 'Not Exists'
            ddl_mode = 'Enabled' if key in (ddl_dict:=user_dict.get('ddl_servers', {})) and ddl_dict[key][0] else 'Disabled'
            text = f"➲ <b>Upload {fname_dict[key]} :</b> {ddl_mode}\n" \
                   f"➲ <b>{fname_dict[key]}'s API Key :</b> {set_exist}\n\n"
            buttons.ibutton('Disable DDL' if ddl_mode == 'Enabled' else 'Enable DDL', f"userset {user_id} s{key}", "header")
        else: return
        text += f"➲ <b>Description :</b> <i>{desp_dict[key][0]}</i>"
        if not edit_mode:
            buttons.ibutton(f"Change {fname_dict[key]}" if set_exist and set_exist != 'Not Exists' and (set_exist != get_readable_file_size(config_dict['LEECH_SPLIT_SIZE']) + ' (Default)') else f"Set {fname_dict[key]}", f"userset {user_id} {key} edit")
        else:
            text += '\n\n' + desp_dict[key][1]
            buttons.ibutton("Stop Change", f"userset {user_id} {key}")
        if set_exist and set_exist != 'Not Exists' and (set_exist != get_readable_file_size(config_dict['LEECH_SPLIT_SIZE']) + ' (Default)'):
            if key == 'thumb':
                buttons.ibutton("View Thumbnail", f"userset {user_id} vthumb", "header")
            buttons.ibutton("↻ Delete", f"userset {user_id} d{key}")
        buttons.ibutton("Back", f"userset {user_id} back {edit_type}", "footer")
        buttons.ibutton("Close", f"userset {user_id} close", "footer")
        button = buttons.build_menu(2)
    return text, button


async def update_user_settings(query, key=None, edit_type=None, edit_mode=None, msg=None, sdirect=False):
    msg, button = await get_user_settings(msg.from_user if sdirect else query.from_user, key, edit_type, edit_mode)
    await editMessage(query if sdirect else query.message, msg, button)


async def user_settings(client, message):
    if len(message.command) > 1 and message.command[1] == '-s':
        set_arg = message.command[2].strip() if len(message.command) > 2 else None
        msg = await sendMessage(message, '<i>Fetching Settings...</i>', photo='IMAGES')
        if set_arg and (reply_to := message.reply_to_message):
            if message.from_user.id != reply_to.from_user.id:
                return await editMessage(msg, '<i>Reply to Your Own Message for Setting via Args Directly</i>')
            if set_arg in ['lprefix', 'lsuffix', 'lremname', 'lcaption', 'ldump'] and reply_to.text:
                return await set_custom(client, reply_to, msg, set_arg, True)
            elif set_arg == 'thumb' and reply_to.media:
                return await set_thumb(client, reply_to, msg, set_arg, True)
        await editMessage(msg, '''㊂ <b><u>Available Flags :</u></b>
>> Reply to the Value with appropriate arg respectively to set directly without opening USet.

➲ <b>Custom Thumbnail :</b>
    /cmd -s thumb
➲ <b>Leech Filename Prefix :</b>
    /cmd -s lprefix
➲ <b>Leech Filename Suffix :</b>
    /cmd -s lsuffix
➲ <b>Leech Filename Remname :</b>
    /cmd -s lremname
➲ <b>Leech Filename Caption :</b>
    /cmd -s lcaption
➲ <b>Leech User Dump :</b>
    /cmd -s ldump''')
    else:
        msg, button = await get_user_settings(message.from_user)
        await sendMessage(message, msg, button, 'IMAGES')


async def set_yt_options(client, message, pre_event):
    user_id = message.from_user.id
    handler_dict[user_id] = False
    value = message.text
    update_user_ldata(user_id, 'yt_opt', value)
    await message.delete()
    await update_user_settings(pre_event, 'yt_opt', 'universal')
    if DATABASE_URL:
        await DbManger().update_user_data(user_id)


async def set_custom(client, message, pre_event, key, direct=False):
    user_id = message.from_user.id
    handler_dict[user_id] = False
    value = message.text
    return_key = 'leech'
    n_key = key
    if key in ['gofile', 'streamsb']:
        user_dict = user_data.get(user_id, {})
        ddl_dict = user_dict.get('ddl_servers', {})
        mode, api = ddl_dict.get(key, [False, ""])
        ddl_dict[key] = [mode, value]
        value = ddl_dict
        n_key = 'ddl_servers'
        return_key = 'ddl_servers'
    update_user_ldata(user_id, n_key, value)
    await message.delete()
    await update_user_settings(pre_event, key, return_key, msg=message, sdirect=direct)
    if DATABASE_URL:
        await DbManger().update_user_data(user_id)


async def set_thumb(client, message, pre_event, key, direct=False):
    user_id = message.from_user.id
    handler_dict[user_id] = False
    path = "Thumbnails/"
    if not await aiopath.isdir(path):
        await mkdir(path)
    photo_dir = await message.download()
    des_dir = ospath.join(path, f'{user_id}.jpg')
    await sync_to_async(Image.open(photo_dir).convert("RGB").save, des_dir, "JPEG")
    await aioremove(photo_dir)
    update_user_ldata(user_id, 'thumb', des_dir)
    await message.delete()
    await update_user_settings(pre_event, key, 'leech', msg=message, sdirect=direct)
    if DATABASE_URL:
        await DbManger().update_user_doc(user_id, 'thumb', des_dir)


async def add_rclone(client, message, pre_event):
    user_id = message.from_user.id
    handler_dict[user_id] = False
    path = f'{getcwd()}/rclone/'
    if not await aiopath.isdir(path):
        await mkdir(path)
    des_dir = ospath.join(path, f'{user_id}.conf')
    await message.download(file_name=des_dir)
    update_user_ldata(user_id, 'rclone', f'rclone/{user_id}.conf')
    await message.delete()
    await update_user_settings(pre_event, 'rcc', 'mirror')
    if DATABASE_URL:
        await DbManger().update_user_doc(user_id, 'rclone', des_dir)


async def leech_split_size(client, message, pre_event):
    user_id = message.from_user.id
    handler_dict[user_id] = False
    sdic = ['b', 'kb', 'mb', 'gb']
    value = message.text.strip()
    slice = -2 if value[-2].lower() in ['k', 'm', 'g'] else -1
    out = value[slice:].strip().lower()
    if out in sdic:
        value = min((float(value[:slice].strip()) * 1024**sdic.index(out)), MAX_SPLIT_SIZE)
    update_user_ldata(user_id, 'split_size', int(round(value)))
    await message.delete()
    await update_user_settings(pre_event, 'split_size', 'leech')
    if DATABASE_URL:
        await DbManger().update_user_data(user_id)


async def event_handler(client, query, pfunc, rfunc, photo=False, document=False):
    user_id = query.from_user.id
    handler_dict[user_id] = True
    start_time = time()

    async def event_filter(_, __, event):
        if photo:
            mtype = event.photo
        elif document:
            mtype = event.document
        else:
            mtype = event.text
        user = event.from_user or event.sender_chat
        return bool(user.id == user_id and event.chat.id == query.message.chat.id and mtype)
    handler = client.add_handler(MessageHandler(
        pfunc, filters=create(event_filter)), group=-1)
    while handler_dict[user_id]:
        await sleep(0.5)
        if time() - start_time > 60:
            handler_dict[user_id] = False
            await rfunc()
    client.remove_handler(*handler)


@new_thread
async def edit_user_settings(client, query):
    from_user = query.from_user
    user_id = from_user.id
    message = query.message
    data = query.data.split()
    thumb_path = f'Thumbnails/{user_id}.jpg'
    rclone_path = f'rclone/{user_id}.conf'
    user_dict = user_data.get(user_id, {})
    if user_id != int(data[1]):
        await query.answer("Not Yours!", show_alert=True)
    elif data[2] in ['universal', 'mirror', 'leech']:
        await query.answer()
        await update_user_settings(query, data[2])
    elif data[2] == "doc":
        update_user_ldata(user_id, 'as_doc',
                          not user_dict.get('as_doc', False))
        await query.answer()
        await update_user_settings(query, 'leech')
        if DATABASE_URL:
            await DbManger().update_user_data(user_id)
    elif data[2] == 'vthumb':
        handler_dict[user_id] = False
        await query.answer()
        await sendFile(message, thumb_path, from_user.mention)
        await update_user_settings(query, 'thumb', 'leech')
    elif data[2] == "dthumb":
        handler_dict[user_id] = False
        if await aiopath.exists(thumb_path):
            await query.answer()
            await aioremove(thumb_path)
            update_user_ldata(user_id, 'thumb', '')
            await update_user_settings(query, 'thumb', 'leech')
            if DATABASE_URL:
                await DbManger().update_user_doc(user_id, 'thumb')
        else:
            await query.answer("Old Settings", show_alert=True)
            await update_user_settings(query, 'leech')
    elif data[2] == 'thumb':
        await query.answer()
        edit_mode = len(data) == 4
        await update_user_settings(query, data[2], 'leech', edit_mode)
        if not edit_mode: return
        pfunc = partial(set_thumb, pre_event=query, key=data[2])
        rfunc = partial(update_user_settings, query, data[2], 'leech')
        await event_handler(client, query, pfunc, rfunc, True)
    elif data[2] == 'yt_opt':
        await query.answer()
        edit_mode = len(data) == 4
        await update_user_settings(query, data[2], 'universal', edit_mode)
        if not edit_mode: return
        pfunc = partial(set_yt_options, pre_event=query)
        rfunc = partial(update_user_settings, query, data[2], 'universal')
        await event_handler(client, query, pfunc, rfunc)
    elif data[2] == 'dyt_opt':
        handler_dict[user_id] = False
        await query.answer()
        update_user_ldata(user_id, 'yt_opt', '')
        await update_user_settings(query, 'yt_opt', 'universal')
        if DATABASE_URL:
            await DbManger().update_user_data(user_id)
    elif data[2] in ['bot_pm', 'mediainfo']:
        handler_dict[user_id] = False
        if data[2] == 'bot_pm' and config_dict['BOT_PM'] or data[2] == 'mediainfo' and config_dict['SHOW_MEDIAINFO']:
            return await query.answer("Force Enabled! Can't Alter Settings", show_alert=True)
        await query.answer()
        update_user_ldata(user_id, data[2], not user_dict.get(data[2], False))
        await update_user_settings(query, 'universal')
        if DATABASE_URL:
            await DbManger().update_user_data(user_id)
    elif data[2] == 'split_size':
        await query.answer()
        edit_mode = len(data) == 4
        await update_user_settings(query, data[2], 'leech', edit_mode)
        if not edit_mode: return
        pfunc = partial(leech_split_size, pre_event=query)
        rfunc = partial(update_user_settings, query, data[2], 'leech')
        await event_handler(client, query, pfunc, rfunc)
    elif data[2] == 'dsplit_size':
        handler_dict[user_id] = False
        await query.answer()
        update_user_ldata(user_id, 'split_size', '')
        await update_user_settings(query, 'split_size', 'leech')
        if DATABASE_URL:
            await DbManger().update_user_data(user_id)
    elif data[2] == 'esplits':
        handler_dict[user_id] = False
        await query.answer()
        update_user_ldata(user_id, 'equal_splits', not user_dict.get('equal_splits', False))
        await update_user_settings(query, 'leech')
        if DATABASE_URL:
            await DbManger().update_user_data(user_id)
    elif data[2] == 'mgroup':
        handler_dict[user_id] = False
        await query.answer()
        update_user_ldata(user_id, 'media_group', not user_dict.get('media_group', False))
        await update_user_settings(query, 'leech')
        if DATABASE_URL:
            await DbManger().update_user_data(user_id)
    elif data[2] in ['sgofile', 'sstreamsb', 'dgofile', 'dstreamsb']:
        handler_dict[user_id] = False
        ddl_dict = user_dict.get('ddl_servers', {})
        key = data[2][1:]
        mode, api = ddl_dict.get(key, [False, ""])
        if data[2][0] == 's':
            if not mode and api == '':
                return await query.answer('Set API to Enable DDL Server', show_alert=True)
            ddl_dict[key] = [not mode, api]
        elif data[2][0] == 'd':
            ddl_dict[key] = [mode, '']
        await query.answer()
        update_user_ldata(user_id, 'ddl_servers', ddl_dict)
        await update_user_settings(query, key, 'ddl_servers')
        if DATABASE_URL:
            await DbManger().update_user_data(user_id)
    elif data[2] == 'rcc':
        await query.answer()
        edit_mode = len(data) == 4
        await update_user_settings(query, data[2], 'mirror', edit_mode)
        if not edit_mode: return
        pfunc = partial(add_rclone, pre_event=query)
        rfunc = partial(update_user_settings, query, data[2], 'mirror')
        await event_handler(client, query, pfunc, rfunc, document=True)
    elif data[2] == 'drcc':
        handler_dict[user_id] = False
        if await aiopath.exists(rclone_path):
            await query.answer()
            await aioremove(rclone_path)
            update_user_ldata(user_id, 'rclone', '')
            await update_user_settings(query, 'rcc', 'mirror')
            if DATABASE_URL:
                await DbManger().update_user_doc(user_id, 'rclone')
        else:
            await query.answer("Old Settings", show_alert=True)
            await update_user_settings(query)
    elif data[2] in ['ddl_servers', 'gofile', 'streamsb']:
        handler_dict[user_id] = False
        await query.answer()
        edit_mode = len(data) == 4
        await update_user_settings(query, data[2], 'mirror' if data[2] == 'ddl_servers' else 'ddl_servers', edit_mode)
        if not edit_mode: return
        pfunc = partial(set_custom, pre_event=query, key=data[2])
        rfunc = partial(update_user_settings, query, data[2], 'mirror' if data[2] == "ddl_servers" else "ddl_servers")
        await event_handler(client, query, pfunc, rfunc)
    elif data[2] in ['lprefix', 'lsuffix', 'lremname', 'lcaption', 'ldump', 'mprefix', 'msuffix', 'mremname']:
        handler_dict[user_id] = False
        await query.answer()
        edit_mode = len(data) == 4
        return_key = 'leech' if data[2][0] == 'l' else 'mirror'
        await update_user_settings(query, data[2], return_key, edit_mode)
        if not edit_mode: return
        pfunc = partial(set_custom, pre_event=query, key=data[2])
        rfunc = partial(update_user_settings, query, data[2], return_key)
        await event_handler(client, query, pfunc, rfunc)
    elif data[2] in ['dlprefix', 'dlsuffix', 'dlremname', 'dlcaption', 'dldump']:
        handler_dict[user_id] = False
        await query.answer()
        update_user_ldata(user_id, data[2][1:], '')
        await update_user_settings(query, data[2][1:], 'leech')
        if DATABASE_URL:
            await DbManger().update_user_data(user_id)
    elif data[2] in ['dmprefix', 'dmsuffix', 'dmremname']:
        handler_dict[user_id] = False
        await query.answer()
        update_user_ldata(user_id, data[2][1:], '')
        await update_user_settings(query, data[2][1:], 'mirror')
        if DATABASE_URL:
            await DbManger().update_user_data(user_id)
    elif data[2] == 'back':
        handler_dict[user_id] = False
        await query.answer()
        setting = data[3] if len(data) == 4 else None
        await update_user_settings(query, setting)
    elif data[2] == 'reset_all':
        handler_dict[user_id] = False
        await query.answer()
        buttons = ButtonMaker()
        buttons.ibutton('Yes', f"userset {user_id} reset_now y")
        buttons.ibutton('No', f"userset {user_id} reset_now n")
        buttons.ibutton("Close", f"userset {user_id} close", "footer")
        await editMessage(message, 'Do you want to Reset Settings ?', buttons.build_menu(2))
    elif data[2] == 'reset_now':
        handler_dict[user_id] = False
        if data[3] == 'n':
            return await update_user_settings(query)
        if await aiopath.exists(thumb_path):
            await aioremove(thumb_path)
        if await aiopath.exists(rclone_path):
            await aioremove(rclone_path)
        await query.answer()
        update_user_ldata(user_id, None, None)
        await update_user_settings(query)
        if DATABASE_URL:
            await DbManger().update_user_data(user_id)
            await DbManger().update_user_doc(user_id, 'thumb')
            await DbManger().update_user_doc(user_id, 'rclone')
    elif data[2] == 'user_del':
        user_id = int(data[3])
        await query.answer()
        thumb_path = f'Thumbnails/{user_id}.jpg'
        rclone_path = f'rclone/{user_id}.conf'
        if await aiopath.exists(thumb_path):
            await aioremove(thumb_path)
        if await aiopath.exists(rclone_path):
            await aioremove(rclone_path)
        update_user_ldata(user_id, None, None)
        if DATABASE_URL:
            await DbManger().update_user_data(user_id)
            await DbManger().update_user_doc(user_id, 'thumb')
            await DbManger().update_user_doc(user_id, 'rclone')
        await editMessage(message, f'Data Reset for {user_id}')
    else:
        handler_dict[user_id] = False
        await query.answer()
        await message.reply_to_message.delete()
        await message.delete()

async def getUserInfo(client, id):
    try:
        return (await client.get_users(id)).mention(style="html")
    except Exception:
        return ''
        
async def send_users_settings(client, message):
    text = message.text.split(maxsplit=1)
    userid = text[1] if len(text) > 1 else None
    if userid and not userid.isdigit():
        userid = None
    elif (reply_to := message.reply_to_message) and reply_to.from_user and not reply_to.from_user.is_bot:
        userid = reply_to.from_user.id
    if not userid:
        msg = f'<u><b>Total Users / Chats Data Saved :</b> {len(user_data)}</u>'
        buttons = ButtonMaker()
        buttons.ibutton("Close", f"userset {message.from_user.id} close")
        button = buttons.build_menu(1)
        for user, data in user_data.items():
            msg += f'\n\n<code>{user}</code>:'
            if data:
                for key, value in data.items():
                    if key in ['token', 'time']:
                        continue
                    msg += f'\n<b>{key}</b>: <code>{escape(str(value))}</code>'
            else:
                msg += "\nUser's Data is Empty!"
        if len(msg.encode()) > 4000:
            with BytesIO(str.encode(msg)) as ofile:
                ofile.name = 'users_settings.txt'
                await sendFile(message, ofile)
        else:
            await sendMessage(message, msg, button)
    elif int(userid) in user_data:
        msg = f'{await getUserInfo(client, userid)} ( <code>{userid}</code> ):'
        if data := user_data[int(userid)]:
            buttons = ButtonMaker()
            buttons.ibutton("Delete Data", f"userset {message.from_user.id} user_del {userid}")
            buttons.ibutton("Close", f"userset {message.from_user.id} close")
            button = buttons.build_menu(1)
            for key, value in data.items():
                if key in ['token', 'time']:
                    continue
                msg += f'\n<b>{key}</b>: <code>{escape(str(value))}</code>'
        else:
            msg += '\nThis User has not Saved anything.'
            button = None
        await sendMessage(message, msg, button)
    else:
        await sendMessage(message, f'{userid} have not saved anything..')


bot.add_handler(MessageHandler(send_users_settings, filters=command(
    BotCommands.UsersCommand) & CustomFilters.sudo))
bot.add_handler(MessageHandler(user_settings, filters=command(
    BotCommands.UserSetCommand) & CustomFilters.authorized_uset))
bot.add_handler(CallbackQueryHandler(edit_user_settings, filters=regex("^userset")))
