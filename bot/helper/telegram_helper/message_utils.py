#!/usr/bin/env python3
from traceback import format_exc
from asyncio import sleep
from aiofiles.os import remove as aioremove
from random import choice as rchoice
from time import time
from re import match as re_match

from pyrogram.types import InputMediaPhoto
from pyrogram.errors import ReplyMarkupInvalid, FloodWait, PeerIdInvalid, RPCError, UserNotParticipant, MessageNotModified, MessageEmpty, PhotoInvalidDimensions, WebpageCurlFailed, MediaEmpty

from bot import config_dict, LOGGER, bot_name, status_reply_dict, status_reply_dict_lock, Interval, bot, user, download_dict_lock
from bot.helper.ext_utils.bot_utils import get_readable_message, setInterval, sync_to_async, download_image_url
from bot.helper.telegram_helper.button_build import ButtonMaker
from bot.helper.ext_utils.exceptions import TgLinkException


async def sendMessage(message, text, buttons=None, photo=None):
    try:
        if photo:
            try:
                if photo == 'IMAGES':
                    photo = rchoice(config_dict['IMAGES'])
                return await message.reply_photo(photo=photo, reply_to_message_id=message.id,
                                                 caption=text, reply_markup=buttons, disable_notification=True)
            except IndexError:
                pass
            except (PhotoInvalidDimensions, WebpageCurlFailed, MediaEmpty):
                des_dir = await download_image_url(photo)
                await sendMessage(message, text, buttons, des_dir)
                await aioremove(des_dir)
                return
            except Exception as e:
                LOGGER.error(format_exc())
        return await message.reply(text=text, quote=True, disable_web_page_preview=True,
                                   disable_notification=True, reply_markup=buttons)
    except FloodWait as f:
        LOGGER.warning(str(f))
        await sleep(f.value * 1.2)
        return await sendMessage(message, text, buttons, photo)
    except ReplyMarkupInvalid:
        return await sendMessage(message, text, None, photo)
    except Exception as e:
        LOGGER.error(format_exc())
        return str(e)


async def sendBot(message, text, buttons=None, photo=None):
    try:
        user_id = message.from_user.id
        if photo:
            try:
                if photo == 'IMAGES':
                    photo = rchoice(config_dict['IMAGES'])
                return await message._client.send_photo(chat_id=user_id, photo=photo, caption=text,
                                                        reply_markup=buttons, disable_notification=True)
            except IndexError:
                pass
            except (PhotoInvalidDimensions, WebpageCurlFailed, MediaEmpty):
                des_dir = await download_image_url(photo)
                await sendBot(message, text, buttons, des_dir)
                await aioremove(des_dir)
                return
            except Exception as e:
                LOGGER.error(format_exc())
        return await message._client.send_message(chat_id=user_id, text=text, disable_web_page_preview=True,
                                                  disable_notification=True, reply_markup=buttons)
    except FloodWait as f:
        LOGGER.warning(str(f))
        await sleep(f.value * 1.2)
        return await sendBot(message, text, buttons, photo)
    except ReplyMarkupInvalid:
        return await sendBot(message, text, None, photo)
    except Exception as e:
        LOGGER.error(format_exc())
        return str(e)


async def chat_info(channel_id):
    if channel_id.startswith('-100'):
        channel_id = int(channel_id)
    elif channel_id.startswith('@'):
        channel_id = channel_id.replace('@', '')
    else:
        return None
    try:
        chat = await bot.get_chat(channel_id)
        return chat
    except PeerIdInvalid as e:
        LOGGER.error(f"{e.NAME}: {e.MESSAGE} for {channel_id}")
        return None


async def sendMultiMessage(message, chat_ids, text, buttons=None, photo=None):
    for channel_id in chat_ids.split():
        chat = await chat_info(channel_id)
        try:
            if photo:
                try:
                    if photo == 'IMAGES':
                        photo = rchoice(config_dict['IMAGES'])
                    return await message._client.send_photo(chat_id=chat.id, photo=photo, caption=text,
                                                     reply_markup=buttons, disable_notification=True)
                except IndexError:
                    pass
                except (PhotoInvalidDimensions, WebpageCurlFailed, MediaEmpty):
                    des_dir = await download_image_url(photo)
                    await sendMultiMessage(message, chat_ids, text, buttons, des_dir)
                    await aioremove(des_dir)
                    return
                except Exception as e:
                    LOGGER.error(str(e))
            return await message._client.send_message(chat_id=chat.id, text=text, disable_web_page_preview=True,
                                               disable_notification=True, reply_markup=buttons)
        except FloodWait as f:
            LOGGER.warning(str(f))
            await sleep(f.value * 1.2)
            return await sendMultiMessage(message, chat_ids, text, buttons, photo)
        except Exception as e:
            LOGGER.error(str(e))
            return str(e)


async def editMessage(message, text, buttons=None, photo=None):
    try:
        if message.media:
            if photo:
                return await message.edit_media(InputMediaPhoto(photo, text), reply_markup=buttons)
            return await message.edit_caption(caption=text, reply_markup=buttons)
        await message.edit(text=text, disable_web_page_preview=True, reply_markup=buttons)
    except FloodWait as f:
        LOGGER.warning(str(f))
        await sleep(f.value * 1.2)
        return await editMessage(message, text, buttons, photo)
    except (MessageNotModified, MessageEmpty):
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
            return await user.send_message(chat_id=config_dict['RSS_CHAT_ID'], text=text, disable_web_page_preview=True,
                                           disable_notification=True)
        else:
            return await bot.send_message(chat_id=config_dict['RSS_CHAT_ID'], text=text, disable_web_page_preview=True,
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


async def get_tg_link_content(link):
    message = None
    if link.startswith('https://t.me/'):
        private = False
        msg = re_match(r"https:\/\/t\.me\/(?:c\/)?([^\/]+)(?:\/[^\/]+)?\/([0-9]+)", link)
    else:
        private = True
        msg = re_match(r"tg:\/\/openmessage\?user_id=([0-9]+)&message_id=([0-9]+)", link)
        if not user:
            raise TgLinkException('USER_SESSION_STRING required for this private link!')

    chat = msg.group(1)
    msg_id = int(msg.group(2))
    if chat.isdigit():
        chat = int(chat) if private else int(f'-100{chat}')

    if not private:
        try:
            message = await bot.get_messages(chat_id=chat, message_ids=msg_id)
            if message.empty:
                private = True
        except Exception as e:
            private = True
            if not user:
                raise e

    if private and user:
        try:
            user_message = await user.get_messages(chat_id=chat, message_ids=msg_id)
        except Exception as e:
            raise TgLinkException(
                f"You don't have access to this chat!. ERROR: {e}") from e
        if not user_message.empty:
            return user_message, 'user'
        else:
            raise TgLinkException("Private: Please report!")
    elif not private:
        return message, 'bot'
    else:
        raise TgLinkException(
            "Bot can't download from GROUPS without joining!")


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
                rmsg = await editMessage(status_reply_dict[chat_id][0], msg, buttons)
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
        message = await sendMessage(msg, progress, buttons, photo='IMAGES')
        message.text = progress
        status_reply_dict[chat_id] = [message, time()]
        if not Interval:
            Interval.append(setInterval(
                config_dict['STATUS_UPDATE_INTERVAL'], update_all_messages))


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


async def user_info(client, userId):
    return await client.get_users(userId)


async def BotPm_check(message, button=None):
    try:
        temp_msg = await message._client.send_message(chat_id=message.from_user.id, text='<b>Checking Access...</b>')
        await temp_msg.delete()
        return None, button
    except Exception as e:
        if button is None:
            button = ButtonMaker()
        _msg = "<i>You didn't START the bot in PM (Private)</i>"
        button.ubutton("Start Bot Now", f"https://t.me/{bot_name}?start=start", 'header')
        return _msg, button