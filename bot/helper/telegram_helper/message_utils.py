#!/usr/bin/env python3
from traceback import format_exc
from asyncio import sleep
from aiofiles.os import remove as aioremove
from random import choice as rchoice
from time import time
from re import match as re_match
from cryptography.fernet import InvalidToken

from pyrogram import Client
from pyrogram.enums import ParseMode
from pyrogram.types import InputMediaPhoto
from pyrogram.errors import ReplyMarkupInvalid, FloodWait, PeerIdInvalid, ChannelInvalid, RPCError, UserNotParticipant, MessageNotModified, MessageEmpty, PhotoInvalidDimensions, WebpageCurlFailed, MediaEmpty

from bot import config_dict, user_data, categories_dict, bot_cache, LOGGER, bot_name, status_reply_dict, status_reply_dict_lock, Interval, bot, user, download_dict_lock
from bot.helper.ext_utils.bot_utils import get_readable_message, setInterval, sync_to_async, download_image_url, fetch_user_tds, fetch_user_dumps, new_thread
from bot.helper.telegram_helper.button_build import ButtonMaker
from bot.helper.ext_utils.exceptions import TgLinkException


async def sendMessage(message, text, buttons=None, photo=None, **kwargs):
    try:
        if photo:
            try:
                if photo == 'IMAGES':
                    photo = rchoice(config_dict['IMAGES'])
                return await message.reply_photo(photo=photo, reply_to_message_id=message.id,
                                                 caption=text, reply_markup=buttons, disable_notification=True, **kwargs)
            except IndexError:
                pass
            except (PhotoInvalidDimensions, WebpageCurlFailed, MediaEmpty):
                des_dir = await download_image_url(photo)
                await sendMessage(message, text, buttons, des_dir)
                await aioremove(des_dir)
                return
            except Exception as e:
                LOGGER.error(format_exc())
        return await message.reply(text=text, quote=True, disable_web_page_preview=True, disable_notification=True,
                                    reply_markup=buttons, reply_to_message_id=rply.id if (rply := message.reply_to_message) and not rply.text and not rply.caption else None,
                                    **kwargs)
    except FloodWait as f:
        LOGGER.warning(str(f))
        await sleep(f.value * 1.2)
        return await sendMessage(message, text, buttons, photo)
    except ReplyMarkupInvalid:
        return await sendMessage(message, text, None, photo)
    except MessageEmpty:
        return await sendMessage(message, text, parse_mode=ParseMode.DISABLED)
    except Exception as e:
        LOGGER.error(format_exc())
        return str(e)


async def sendCustomMsg(chat_id, text, buttons=None, photo=None, debug=False):
    try:
        if photo:
            try:
                if photo == 'IMAGES':
                    photo = rchoice(config_dict['IMAGES'])
                return await bot.send_photo(chat_id=chat_id, photo=photo, caption=text,
                                                        reply_markup=buttons, disable_notification=True)
            except IndexError:
                pass
            except (PhotoInvalidDimensions, WebpageCurlFailed, MediaEmpty):
                des_dir = await download_image_url(photo)
                await sendCustomMsg(chat_id, text, buttons, des_dir)
                await aioremove(des_dir)
                return
            except Exception as e:
                LOGGER.error(format_exc())
        return await bot.send_message(chat_id=chat_id, text=text, disable_web_page_preview=True,
                                                  disable_notification=True, reply_markup=buttons)
    except FloodWait as f:
        LOGGER.warning(str(f))
        await sleep(f.value * 1.2)
        return await sendCustomMsg(chat_id, text, buttons, photo)
    except ReplyMarkupInvalid:
        return await sendCustomMsg(chat_id, text, None, photo)
    except Exception as e:
        LOGGER.error(format_exc())
        return str(e)


async def chat_info(channel_id):
    channel_id = str(channel_id).strip()
    if channel_id.startswith('-100'):
        channel_id = int(channel_id)
    elif channel_id.startswith('@'):
        channel_id = channel_id.replace('@', '')
    else:
        return None
    try:
        return await bot.get_chat(channel_id)
    except (PeerIdInvalid, ChannelInvalid) as e:
        LOGGER.error(f"{e.NAME}: {e.MESSAGE} for {channel_id}")
        return None


async def sendMultiMessage(chat_ids, text, buttons=None, photo=None):
    msg_dict = {}
    for channel_id in chat_ids.split():
        channel_id, *topic_id = channel_id.split(':')
        topic_id = int(topic_id[0]) if len(topic_id) else None
        chat = await chat_info(channel_id)
        try:
            if photo:
                try:
                    if photo == 'IMAGES':
                        photo = rchoice(config_dict['IMAGES'])
                    sent = await bot.send_photo(chat_id=chat.id, photo=photo, caption=text,
                                                     reply_markup=buttons, reply_to_message_id=topic_id, disable_notification=True)
                    msg_dict[f"{chat.id}:{topic_id}"] = sent
                except IndexError:
                    pass
                except (PhotoInvalidDimensions, WebpageCurlFailed, MediaEmpty):
                    des_dir = await download_image_url(photo)
                    await sendMultiMessage(chat_ids, text, buttons, des_dir)
                    await aioremove(des_dir)
                    break
                except Exception as e:
                    LOGGER.error(str(e))
                continue
            LOGGER.info("DEBUG CP 2")
            sent = await bot.send_message(chat_id=chat.id, text=text, disable_web_page_preview=True,
                                               disable_notification=True, reply_to_message_id=topic_id, reply_markup=buttons)
            msg_dict[f"{chat.id}:{topic_id}"] = sent
        except FloodWait as f:
            LOGGER.warning(str(f))
            await sleep(f.value * 1.2)
            return await sendMultiMessage(chat_ids, text, buttons, photo)
        except Exception as e:
            LOGGER.error(str(e))
    return msg_dict


async def editMessage(message, text, buttons=None, photo=None):
    try:
        if message.media:
            if photo:
                photo = rchoice(config_dict['IMAGES']) if photo == 'IMAGES' else photo
                return await message.edit_media(InputMediaPhoto(photo, text), reply_markup=buttons)
            return await message.edit_caption(caption=text, reply_markup=buttons)
        await message.edit(text=text, disable_web_page_preview=True, reply_markup=buttons)
    except FloodWait as f:
        LOGGER.warning(str(f))
        await sleep(f.value * 1.2)
        return await editMessage(message, text, buttons, photo)
    except (MessageNotModified, MessageEmpty):
        pass
    except ReplyMarkupInvalid:
        return await editMessage(message, text, None, photo)
    except Exception as e:
        LOGGER.error(str(e))
        return str(e)


async def editReplyMarkup(message, reply_markup):
    try:
        return await message.edit_reply_markup(reply_markup=reply_markup)
    except MessageNotModified:
        pass
    except Exception as e:
        LOGGER.error(str(e))
        return str(e)


async def sendFile(message, file, caption=None, buttons=None):
    try:
        return await message.reply_document(document=file, quote=True, caption=caption, disable_notification=True, reply_markup=buttons)
    except FloodWait as f:
        LOGGER.warning(str(f))
        await sleep(f.value * 1.2)
        return await sendFile(message, file, caption)
    except Exception as e:
        LOGGER.error(str(e))
        return str(e)


async def sendRss(text):
    try:
        if user:
            return await user.send_message(chat_id=config_dict['RSS_CHAT'], text=text, disable_web_page_preview=True,
                                           disable_notification=True)
        else:
            return await bot.send_message(chat_id=config_dict['RSS_CHAT'], text=text, disable_web_page_preview=True,
                                          disable_notification=True)
    except FloodWait as f:
        LOGGER.warning(str(f))
        await sleep(f.value * 1.2)
        return await sendRss(text)
    except Exception as e:
        LOGGER.error(str(e))
        return str(e)


async def deleteMessage(message):
    try:
        await message.delete()
    except Exception as e:
        LOGGER.error(str(e))


async def auto_delete_message(cmd_message=None, bot_message=None):
    if config_dict['AUTO_DELETE_MESSAGE_DURATION'] != -1:
        await sleep(config_dict['AUTO_DELETE_MESSAGE_DURATION'])
        if cmd_message is not None:
            await deleteMessage(cmd_message)
        if bot_message is not None:
            await deleteMessage(bot_message)


async def delete_links(message):
    if config_dict['DELETE_LINKS']:
        if reply_to := message.reply_to_message:
            await deleteMessage(reply_to)
        await deleteMessage(message)
        
        
async def delete_all_messages():
    async with status_reply_dict_lock:
        for key, data in list(status_reply_dict.items()):
            try:
                del status_reply_dict[key]
                await deleteMessage(data[0])
            except Exception as e:
                LOGGER.error(str(e))


async def get_tg_link_content(link, user_id, decrypter=None):
    message = None
    user_sess = user_data.get(user_id, {}).get('usess', '')
    if link.startswith(('https://t.me/', 'https://telegram.me/', 'https://telegram.dog/', 'https://telegram.space/')):
        private = False
        msg = re_match(r"https:\/\/(t\.me|telegram\.me|telegram\.dog|telegram\.space)\/(?:c\/)?([^\/]+)(?:\/[^\/]+)?\/([0-9]+)", link)
    else:
        private = True
        msg = re_match(r"tg:\/\/(openmessage)\?user_id=([0-9]+)&message_id=([0-9]+)", link)
        if not (user or user_sess):
            raise TgLinkException('USER_SESSION_STRING or Private User Session required for this private link!')

    chat = msg.group(2)
    msg_id = int(msg.group(3))
    if chat.isdigit():
        chat = int(chat) if private else int(f'-100{chat}')

    if not private:
        try:
            message = await bot.get_messages(chat_id=chat, message_ids=msg_id)
            if message.empty:
                private = True
        except Exception as e:
            private = True
            if not (user or user_sess):
                raise e

    if private and user:
        try:
            user_message = await user.get_messages(chat_id=chat, message_ids=msg_id)
            if not user_message.empty:
                return user_message, 'user'
        except Exception as e:
            if not user_sess:
                raise TgLinkException(f"Bot User Session  don't have access to this chat!. ERROR: {e}") from e

    if private and user_sess:
        if decrypter is None:
            return None, ""
        try:
            async with Client(user_id, session_string=decrypter.decrypt(user_sess).decode(), in_memory=True, no_updates=True) as usession:
                user_message = await usession.get_messages(chat_id=chat, message_ids=msg_id)
        except InvalidToken:
            raise TgLinkException("Provided Decryption Key is Invalid, Recheck & Retry")
        except Exception as e:
            raise TgLinkException(f"User Session don't have access to this chat!. ERROR: {e}") from e
        if not user_message.empty:
            return user_message, 'user_sess'
        else:
            raise TgLinkException("Privatly Deleted or Not Accessible!")
    elif not private:
        return message, 'bot'
    else:
        raise TgLinkException("Bot can't download from GROUPS without joining!, Set your Own Session to get access !")


async def update_all_messages(force=False):
    async with status_reply_dict_lock:
        if not status_reply_dict or not Interval or (not force and time() - list(status_reply_dict.values())[0][1] < 3):
            return
        for chat_id in list(status_reply_dict.keys()):
            status_reply_dict[chat_id][1] = time()
    async with download_dict_lock:
        msg, buttons = await sync_to_async(get_readable_message)
    if msg is None:
        return
    async with status_reply_dict_lock:
        for chat_id in list(status_reply_dict.keys()):
            if status_reply_dict[chat_id] and msg != status_reply_dict[chat_id][0].text:
                rmsg = await editMessage(status_reply_dict[chat_id][0], msg, buttons, 'IMAGES')
                if isinstance(rmsg, str) and rmsg.startswith('Telegram says: [400'):
                    del status_reply_dict[chat_id]
                    continue
                status_reply_dict[chat_id][0].text = msg
                status_reply_dict[chat_id][1] = time()


async def sendStatusMessage(msg):
    async with download_dict_lock:
        progress, buttons = await sync_to_async(get_readable_message)
    if progress is None:
        return
    async with status_reply_dict_lock:
        chat_id = msg.chat.id
        if chat_id in list(status_reply_dict.keys()):
            message = status_reply_dict[chat_id][0]
            await deleteMessage(message)
            del status_reply_dict[chat_id]
        if message := await sendMessage(msg, progress, buttons, photo='IMAGES'):
            if hasattr(message, 'caption'):
                message.caption = progress
            else:
                message.text = progress
        status_reply_dict[chat_id] = [message, time()]
        if not Interval:
            Interval.append(setInterval(config_dict['STATUS_UPDATE_INTERVAL'], update_all_messages))
    

async def open_category_btns(message):
    user_id = message.from_user.id
    msg_id = message.id
    buttons = ButtonMaker()
    _tick = True
    if len(utds := await fetch_user_tds(user_id)) > 1:
        for _name in utds.keys():
            buttons.ibutton(f'{"✅️" if _tick else ""} {_name}', f"scat {user_id} {msg_id} {_name.replace(' ', '_')}")
            if _tick: _tick, cat_name = False, _name
    elif len(categories_dict) > 1:
        for _name in categories_dict.keys():
            buttons.ibutton(f'{"✅️" if _tick else ""} {_name}', f"scat {user_id} {msg_id} {_name.replace(' ', '_')}")
            if _tick: _tick, cat_name = False, _name
    buttons.ibutton('Cancel', f'scat {user_id} {msg_id} scancel', 'footer')
    buttons.ibutton(f'Done (60)', f'scat {user_id} {msg_id} sdone', 'footer')
    prompt = await sendMessage(message, f'<b>Select the category where you want to upload</b>\n\n<i><b>Upload Category:</b></i> <code>{cat_name}</code>\n\n<b>Timeout:</b> 60 sec', buttons.build_menu(3))
    start_time = time()
    bot_cache[msg_id] = [None, None, False, False, start_time]
    while time() - start_time <= 60:
        await sleep(0.5)
        if bot_cache[msg_id][2] or bot_cache[msg_id][3]:
            break
    drive_id, index_link, _, is_cancelled, __ = bot_cache[msg_id]
    if not is_cancelled:
        await deleteMessage(prompt)
    else:
        await editMessage(prompt, "<b>Task Cancelled</b>")
    del bot_cache[msg_id]
    return drive_id, index_link, is_cancelled
    
    
async def open_dump_btns(message):
    user_id = message.from_user.id
    msg_id = message.id
    buttons = ButtonMaker()
    _tick = True
    if len(udmps := await fetch_user_dumps(user_id)) > 1:
        for _name in udmps.keys():
            buttons.ibutton(f'{"✅️" if _tick else ""} {_name}', f"dcat {user_id} {msg_id} {_name.replace(' ', '_')}")
            if _tick: _tick, cat_name = False, _name
    buttons.ibutton('Upload in All', f'dcat {user_id} {msg_id} All', 'header')
    buttons.ibutton('Cancel', f'dcat {user_id} {msg_id} dcancel', 'footer')
    buttons.ibutton(f'Done (60)', f'dcat {user_id} {msg_id} ddone', 'footer')
    prompt = await sendMessage(message, f'<b>Select the Dump category where you want to upload</b>\n\n<i><b>Upload Category:</b></i> <code>{cat_name}</code>\n\n<b>Timeout:</b> 60 sec', buttons.build_menu(3))
    start_time = time()
    bot_cache[msg_id] = [None, False, False, start_time]
    while time() - start_time <= 60:
        await sleep(0.5)
        if bot_cache[msg_id][1] or bot_cache[msg_id][2]:
            break
    dump_chat, _, is_cancelled, __ = bot_cache[msg_id]
    if not is_cancelled:
        await deleteMessage(prompt)
    else:
        await editMessage(prompt, "<b>Task Cancelled</b>")
    del bot_cache[msg_id]
    return dump_chat, is_cancelled


async def forcesub(message, ids, button=None):
    join_button = {}
    _msg = ''
    for channel_id in ids.split():
        chat = await chat_info(channel_id)
        try:
            await chat.get_member(message.from_user.id)
        except UserNotParticipant:
            if username := chat.username:
                invite_link = f"https://t.me/{username}"
            else:
                invite_link = chat.invite_link
            join_button[chat.title] = invite_link
        except RPCError as e:
            LOGGER.error(f"{e.NAME}: {e.MESSAGE} for {channel_id}")
        except Exception as e:
            LOGGER.error(f'{e} for {channel_id}')
    if join_button:
        if button is None:
            button = ButtonMaker()
        _msg = "You haven't joined our channel yet!"
        for key, value in join_button.items():
            button.ubutton(f'Join {key}', value, 'footer')
    return _msg, button


async def user_info(user_id):
    try:
        return await bot.get_users(user_id)
    except Exception:
        return ''


async def check_botpm(message, button=None):
    try:
        temp_msg = await message._client.send_message(chat_id=message.from_user.id, text='<b>Checking Access...</b>')
        await deleteMessage(temp_msg)
        return None, button
    except Exception as e:
        if button is None:
            button = ButtonMaker()
        _msg = "<i>You didn't START the bot in PM (Private)</i>"
        button.ubutton("Start Bot Now", f"https://t.me/{bot_name}?start=start", 'header')
        return _msg, button
