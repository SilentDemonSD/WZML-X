from random import choice as rchoice
from html import escape
from time import time
from os import remove as osremove
from asyncio import sleep as asleep
from pyrogram import Client
from pyrogram.enums import ParseMode, ChatMemberStatus, ChatType
from pyrogram.errors import FloodWait, Unauthorized, MessageNotModified, MessageIdInvalid
from pyrogram.types import Message, InputMediaPhoto

from bot import bot, botStartTime, user_data, main_loop, LOGGER, status_reply_dict, status_reply_dict_lock, Interval, bot, rss_session, config_dict
from bot.helper.ext_utils.bot_utils import get_readable_time, is_url, get_readable_file_size, get_readable_message, setInterval
from bot.helper.telegram_helper.button_build import ButtonMaker


async def sendMessage(text, bot: Client, message: Message, reply_markup=None, chat_id=None):
    try:
        return await bot.send_message(chat_id= chat_id or message.chat.id, reply_to_message_id=message.id, disable_web_page_preview=True,
                               text=text, reply_markup=reply_markup)
    except FloodWait as fw:
        LOGGER.warning(str(fw))
        await asleep(fw.value * 1.5)
        return await sendMessage(text, bot, message, reply_markup, chat_id)
    except Unauthorized:
        buttons = ButtonMaker()
        buttons.buildbutton("Start", f"{bot.link}?start=start")
        startwarn = f"<b>I found that you haven't started me in PM (Private Chat) yet.</b>\n\n" \
                    f"From now on i will give Mirror/Clone link and leeched files in PM"
        msg = sendPhoto(startwarn, bot, message, reply_markup=buttons.build_menu(1))
        main_loop.create_task(auto_delete_upload_message(bot, message, msg))
        return
    except Exception as e:
        LOGGER.error(str(e))
        return

async def editMessage(text, message, reply_markup=None):
    try:
        await bot.edit_message_text(text=text, message_id=message.id, chat_id=message.chat.id, reply_markup=reply_markup)
    except FloodWait as fw:
        LOGGER.warning(str(fw))
        await asleep(fw.value * 1.5)
        return await editMessage(text, message, reply_markup)
    except MessageNotModified as e:
        pass
    except Exception as e:
        LOGGER.error(str(e))
        return str(e)

async def editCaption(text, message, reply_markup=None):
    try:
        await bot.edit_message_caption(chat_id=message.chat.id, message_id=message.id, caption=text, 
                              reply_markup=reply_markup)
    except FloodWait as fw:
        LOGGER.warning(str(fw))
        await asleep(fw.value * 1.5)
        return await editMessage(text, message, reply_markup)
    except MessageNotModified as e:
        pass
    except Exception as e:
        LOGGER.error(str(e))
        return str(e)

async def sendRss(text, bot):
    if not rss_session:
        try:
            return await bot.send_message(config_dict['RSS_CHAT_ID'], text)
        except FloodWait as fw:
            LOGGER.warning(str(fw))
            await asleep(fw.value * 1.5)
            return await sendRss(text, bot)
        except Exception as e:
            LOGGER.error(str(e))
            return
    else:
        try:
            with rss_session:
                return rss_session.send_message(config_dict['RSS_CHAT_ID'], text, disable_web_page_preview=True)
        except FloodWait as e:
            LOGGER.warning(str(e))
            await asleep(e.value * 1.5)
            return await sendRss(text, bot)
        except Exception as e:
            LOGGER.error(str(e))
            return


async def sendPhoto(text, bot, message, photo=None, reply_markup=None, chat_id=None):
    try:
        if config_dict['PICS'] or photo:
            return await bot.send_photo(chat_id=chat_id or message.chat.id, photo=photo or rchoice(config_dict['PICS']), reply_to_message_id=message.id,
                    caption=text, reply_markup=reply_markup)
        else:
            return await sendMessage(text, bot, message, reply_markup, chat_id or message.chat.id)
    except FloodWait as fw:
        LOGGER.warning(str(fw))
        await asleep(fw.value * 1.5)
        return await sendPhoto(text, bot, message, photo, reply_markup, chat_id)
    except Exception as e:
        LOGGER.error(str(e))
        return

async def editPhoto(text, message, photo, reply_markup=None):
    try:
        return await bot.edit_message_media(media=InputMediaPhoto(media=photo, caption=text, parse_mode=ParseMode.HTML), chat_id=message.chat.id, message_id=message.id,
                                      reply_markup=reply_markup)
    except FloodWait as fw:
        LOGGER.warning(str(fw))
        await asleep(fw.value * 1.5)
        return await editPhoto(text, message, photo, reply_markup)
    except MessageNotModified as e:
        pass
    except Exception as e:
        LOGGER.error(str(e))
        return

async def deleteMessage(bot, message):
    try:
        await bot.delete_messages(chat_id=message.chat.id, message_ids=message.id)
    except MessageIdInvalid as e:
        pass
    except Exception as e:
        LOGGER.error(str(e))
        pass

async def sendLogFile(client, message):
    logFileRead = open('log.txt', 'r')
    logFileLines = logFileRead.read().splitlines()
    ind = 1
    Loglines = ''
    try:
        while len(Loglines) <= 2500:
            Loglines = logFileLines[-ind]+'\n'+Loglines
            if ind == len(logFileLines): break
            ind += 1
        startLine = f"Generated Last {ind} Lines from log.txt: \n\n---------------- START LOG -----------------\n\n"
        endLine = "\n---------------- END LOG -----------------"
        await sendMessage(escape(startLine+Loglines+endLine), client, message)
    except Exception as err:
        LOGGER.error(f"Log Display : {err}")
    await client.send_document(document='log.txt', thumb='Thumbnails/weeb.jpg',
                          reply_to_message_id=message.id,
                          chat_id=message.chat.id, caption=f'log.txt\n\n⏰️ UpTime: {get_readable_time(time() - botStartTime)}')

async def sendFile(c: Client, message, name, caption=""):
    try:
        await c.send_document(document=name, reply_to_message_id=message.id,
                             caption=caption, parse_mode=ParseMode.HTML, chat_id=message.chat.id,
                             thumb='Thumbnails/weeb.jpg')
        osremove(name)
        return
    except FloodWait as r:
        LOGGER.warning(str(r))
        await asleep(r.value * 1.5)
        return await sendFile(c, message, name, caption)
    except Exception as e:
        LOGGER.error(str(e))
        return

async def forcesub(bot, message, tag):
    if not (FSUB_IDS := config_dict['FSUB_IDS']):
        return
    join_button = {}
    for channel_id in FSUB_IDS.split():
        if not str(channel_id).startswith('-100'):
            continue
        chat = await bot.get_chat(channel_id)
        member = chat.get_member(message.from_user.id)
        if member.status in [member.LEFT, member.KICKED] :
            join_button[chat.title] = chat.link or chat.invite_link
    if join_button:
        btn = ButtonMaker()
        for key, value in join_button.items():
            btn.buildbutton(key, value)
        msg = f'💡 {tag},\nYou have to join our channel(s) In Order To Use Bots!\n🔻 Join And Try Again!'
        reply_message = await sendMessage(msg, bot, message, btn.build_menu(1))
        return reply_message


async def sendMirrorLogMessage(text, bot, message, botpm, button):
    if 'mirror_logs' in user_data:
        if config_dict['SAVE_MSG'] and (botpm or message.chat.type == ChatType.PRIVATE):
                button.sbutton("Save This Message", 'save', 'footer')
        for chatid in user_data['mirror_logs']:
            await sendPhoto(text, bot, message, reply_markup=button.build_menu(2), chat_id=chatid)            


async def sendLinkLogMessage(bot, message_args, name, size, tag, user_id, reply_to):
    NAME_FONT = config_dict['NAME_FONT']
    if config_dict['EMOJI_THEME']:
        slmsg = f"🗂️ Name: <{NAME_FONT}>{escape(name)}</{NAME_FONT}>\n\n"
        try:
            slmsg += f"📐 Size: {size}\n"
        except ValueError:
            slmsg += f"📐 Size: {get_readable_file_size(int(size))}\n"
        slmsg += f"👥 Added by: {tag} | <code>{user_id}</code>\n\n"
    else:
        slmsg = f"Name: <{NAME_FONT}>{escape(name)}</{NAME_FONT}>\n\n"
        try:
            slmsg += f"Size: {get_readable_file_size(int(size))}\n"
        except ValueError:
            slmsg += f"Size: {size}\n"
        slmsg += f"Added by: {tag} | <code>{user_id}</code>\n\n"
    if 'link_logs' in user_data:
        try:
            source_link = f"‒‒‒‒‒‒‒‒‒‒‒‒‒‒‒‒‒‒‒‒‒‒‒‒‒‒‒‒‒‒‒‒\n<code>{message_args[1]}</code>\n‒‒‒‒‒‒‒‒‒‒‒‒‒‒‒‒‒‒‒‒‒‒‒‒‒‒‒‒‒‒‒‒\n"
            for link_log in user_data['link_logs']:
                await bot.send_message(link_log, text=slmsg + source_link, parse_mode=ParseMode.HTML)
        except IndexError:
            pass
        if reply_to is not None:
            try:
                reply_text = reply_to.text
                if is_url(reply_text):
                    source_link = f"‒‒‒‒‒‒‒‒‒‒‒‒‒‒‒‒‒‒‒‒‒‒‒‒‒‒‒‒‒‒‒‒\n<code>{reply_text.strip()}</code>\n‒‒‒‒‒‒‒‒‒‒‒‒‒‒‒‒‒‒‒‒‒‒‒‒‒‒‒‒‒‒‒‒\n"
                    for link_log in user_data['link_logs']:
                        await bot.send_message(chat_id=link_log, text=slmsg + source_link, parse_mode=ParseMode.HTML)
            except TypeError:
                pass

async def sendLeechLogIndexMsg(text, bot, message, reply_markup=None):
    if 'is_leech_log' in user_data and config_dict['LEECH_LOG_INDEXING']:
        for chatid in user_data['is_leech_log']:
            await sendPhoto(text, bot, message, reply_markup=reply_markup, chat_id=chatid)
    else:
        pass

async def isAdmin(message, user_id=None):
    if message.chat.type != ChatType.PRIVATE:
        chat = message.chat
        if user_id:
            member = await chat.get_member(user_id)
        else:
            member = await chat.get_member(message.from_user.id)    
        return member.status in [ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER]

async def auto_delete_message(bot, cmd_message=None, bot_message=None):
    if config_dict['AUTO_DELETE_MESSAGE_DURATION'] != -1:
        await asleep(config_dict['AUTO_DELETE_MESSAGE_DURATION'])
        if cmd_message is not None:
            await deleteMessage(bot, cmd_message)
        if bot_message is not None:
            await deleteMessage(bot, bot_message)


async def auto_delete_upload_message(bot, cmd_message=None, bot_message=None):
    if cmd_message.chat.type == ChatType.PRIVATE:
        pass
    elif config_dict['AUTO_DELETE_UPLOAD_MESSAGE_DURATION'] != -1:
        await asleep(config_dict['AUTO_DELETE_UPLOAD_MESSAGE_DURATION'])
        reply_to = cmd_message.reply_to_message
        if reply_to is not None:
            await reply_to.delete()
        if bot_message is not None:
            await deleteMessage(bot, bot_message)
    if cmd_message is not None:
        await deleteMessage(bot, cmd_message)
            
async def delete_all_messages():
    async with status_reply_dict_lock:
        for data in list(status_reply_dict.values()):
            try:
                await deleteMessage(bot, data[0])
                del status_reply_dict[data[0].chat.id]
            except Exception as e:
                LOGGER.error(str(e))

async def update_all_messages(force=False):
    async with status_reply_dict_lock:
        if not status_reply_dict or not Interval or (not force and time() - list(status_reply_dict.values())[0][1] < 3):
            return
        for chat_id in status_reply_dict:
            status_reply_dict[chat_id][1] = time()

    msg, buttons = await get_readable_message()
    if msg is None:
        return
    async with status_reply_dict_lock:
        for chat_id in status_reply_dict:
            if status_reply_dict[chat_id] and msg != status_reply_dict[chat_id][0].text:
                if config_dict['PICS']:
                    rmsg = await editPhoto(msg, status_reply_dict[chat_id][0], rchoice(config_dict['PICS']), buttons)
                else:
                    rmsg = await editMessage(msg, status_reply_dict[chat_id][0], buttons)
                if rmsg == "Message to edit not found":
                    del status_reply_dict[chat_id]
                    return
                status_reply_dict[chat_id][0].text = msg
                status_reply_dict[chat_id][1] = time()

async def sendStatusMessage(msg, bot):
    progress, buttons = await get_readable_message()
    if progress is None:
        return
    async with status_reply_dict_lock:
        if msg.chat.id in status_reply_dict:
            message = status_reply_dict[msg.chat.id][0]
            await deleteMessage(bot, message)
            del status_reply_dict[msg.chat.id]
        message = await sendPhoto(progress, bot, msg, reply_markup=buttons)
        status_reply_dict[msg.chat.id] = [message, time()]
        if not Interval:
            Interval.append(setInterval(config_dict['STATUS_UPDATE_INTERVAL'], update_all_messages))
