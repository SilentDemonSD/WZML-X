#!/usr/bin/env python3
from traceback import format_exc
from logging import getLogger, ERROR
from aiofiles.os import remove as aioremove, path as aiopath, rename as aiorename, makedirs, rmdir, mkdir
from os import walk, path as ospath
from time import time
from PIL import Image
from pyrogram.types import InputMediaVideo, InputMediaDocument, InlineKeyboardMarkup
from pyrogram.errors import FloodWait, RPCError, PeerIdInvalid, ChannelInvalid
from asyncio import sleep
from tenacity import retry, wait_exponential, stop_after_attempt, retry_if_exception_type, RetryError
from re import match as re_match, sub as re_sub
from natsort import natsorted
from aioshutil import copy

from bot import config_dict, user_data, GLOBAL_EXTENSION_FILTER, bot, user, IS_PREMIUM_USER
from bot.helper.themes import BotTheme
from bot.helper.telegram_helper.button_build import ButtonMaker
from bot.helper.telegram_helper.message_utils import sendCustomMsg, editReplyMarkup, sendMultiMessage, chat_info, deleteMessage, get_tg_link_content
from bot.helper.ext_utils.fs_utils import clean_unwanted, is_archive, get_base_name
from bot.helper.ext_utils.bot_utils import get_readable_file_size, is_telegram_link, is_url, sync_to_async, download_image_url
from bot.helper.ext_utils.leech_utils import get_audio_thumb, get_media_info, get_document_type, take_ss, get_ss, get_mediainfo_link, format_filename

LOGGER = getLogger(__name__)
getLogger("pyrogram").setLevel(ERROR)


class TgUploader:

    def __init__(self, name=None, path=None, listener=None):
        self.name = name
        self.__last_uploaded = 0
        self.__processed_bytes = 0
        self.__listener = listener
        self.__path = path
        self.__start_time = time()
        self.__total_files = 0
        self.__is_cancelled = False
        self.__retry_error = False
        self.__thumb = f"Thumbnails/{listener.message.from_user.id}.jpg"
        self.__sent_msg = None
        self.__has_buttons = False
        self.__msgs_dict = {}
        self.__corrupted = 0
        self.__is_corrupted = False
        self.__media_dict = {'videos': {}, 'documents': {}}
        self.__last_msg_in_group = False
        self.__prm_media = False
        self.__client = bot
        self.__up_path = ''
        self.__mediainfo = False
        self.__as_doc = False
        self.__media_group = False
        self.__upload_dest = ''
        self.__bot_pm = False
        self.__user_id = listener.message.from_user.id
        self.__leechmsg = {}
        self.__leech_utils = self.__listener.leech_utils
        
    async def get_custom_thumb(self, thumb):
        if is_telegram_link(thumb):
            try:
                msg, client = await get_tg_link_content(thumb, self.__user_id )
            except Exception as e:
                LOGGER.error(f"Thumb Access Error: {e}")
                return None
            if msg and not msg.photo:
                LOGGER.error("Thumb TgLink Invalid: Provide Link to Photo Only !")
                return None
            _client = bot if client == 'bot' else user
            photo_dir = await _client.download_media(msg)
        elif is_url(thumb):
            photo_dir = await download_image_url(thumb)
        else:
            LOGGER.error("Custom Thumb Invalid")
            return None
        if await aiopath.exists(photo_dir):
            path = "Thumbnails"
            if not await aiopath.isdir(path):
                await mkdir(path)
            des_dir = ospath.join(path, f'{time()}.jpg')
            await sync_to_async(Image.open(photo_dir).convert("RGB").save, des_dir, "JPEG")
            await aioremove(photo_dir)
            return des_dir
        return None

    async def __buttons(self, up_path, is_video=False):
        buttons = ButtonMaker()
        try:
            if config_dict['SCREENSHOTS_MODE'] and is_video and bool(self.__leech_utils['screenshots']):
                buttons.ubutton(BotTheme('SCREENSHOTS'), await get_ss(up_path, self.__leech_utils['screenshots']))
        except Exception as e:
            LOGGER.error(f"ScreenShots Error: {e}")
        try:
            if self.__mediainfo:
                buttons.ubutton(BotTheme('MEDIAINFO_LINK'), await get_mediainfo_link(up_path))
        except Exception as e:
            LOGGER.error(f"MediaInfo Error: {e}")
        if config_dict['SAVE_MSG'] and (config_dict['LEECH_LOG_ID'] or not self.__listener.isPrivate):
            buttons.ibutton(BotTheme('SAVE_MSG'), 'save', 'footer')
        if self.__has_buttons:
            return buttons.build_menu(1)
        return None

    async def __copy_file(self):
        try:
            if self.__bot_pm and (self.__leechmsg and not self.__listener.excep_chat or self.__listener.isSuperGroup):
                copied = await bot.copy_message(
                    chat_id=self.__user_id,
                    from_chat_id=self.__sent_msg.chat.id,
                    message_id=self.__sent_msg.id,
                    reply_to_message_id=self.__listener.botpmmsg.id if self.__listener.botpmmsg else None
                )
                if copied and self.__has_buttons:
                    btn_markup = InlineKeyboardMarkup(BTN) if (BTN := self.__sent_msg.reply_markup.inline_keyboard[:-1]) else None
                    await editReplyMarkup(copied, btn_markup if config_dict['SAVE_MSG'] else self.__sent_msg.reply_markup)
        except Exception as err:
            if not self.__is_cancelled:
                LOGGER.error(f"Failed To Send in BotPM:\n{str(err)}")
        
        try:
            if len(self.__leechmsg) > 1 and not self.__listener.excep_chat:
                for chat_id, msg in list(self.__leechmsg.items())[1:]:
                    chat_id, *topics = chat_id.split(':')
                    leech_copy = await bot.copy_message(
                        chat_id=int(chat_id),
                        from_chat_id=self.__sent_msg.chat.id,
                        message_id=self.__sent_msg.id,
                        reply_to_message_id=msg.id
                    )
                    # Layer 161 Needed for Topics !
                    if config_dict['CLEAN_LOG_MSG'] and msg.text:
                        await deleteMessage(msg)
                    if leech_copy and self.__has_buttons:
                        await editReplyMarkup(leech_copy, self.__sent_msg.reply_markup)
        except Exception as err:
            if not self.__is_cancelled:
                LOGGER.error(f"Failed To Send in Leech Log [ {chat_id} ]:\n{str(err)}")
        
        try:
            if self.__upload_dest:
                for channel_id in self.__upload_dest:
                    if chat := (await chat_info(channel_id)):
                        try:
                            dump_copy = await bot.copy_message(
                                chat_id=chat.id,
                                from_chat_id=self.__sent_msg.chat.id,
                                message_id=self.__sent_msg.id
                            )
                            if dump_copy and self.__has_buttons:
                                btn_markup = InlineKeyboardMarkup(BTN) if (BTN := self.__sent_msg.reply_markup.inline_keyboard[:-1]) else None
                                await editReplyMarkup(dump_copy, btn_markup if config_dict['SAVE_MSG'] else self.__sent_msg.reply_markup)
                        except (ChannelInvalid, PeerIdInvalid) as e:
                            LOGGER.error(f"{e.NAME}: {e.MESSAGE} for {channel_id}")
                            continue
        except Exception as err:
            if not self.__is_cancelled:
                LOGGER.error(f"Failed To Send in User Dump:\n{str(err)}")


    async def __upload_progress(self, current, total):
        if self.__is_cancelled:
            if IS_PREMIUM_USER:
                user.stop_transmission()
            bot.stop_transmission()
        chunk_size = current - self.__last_uploaded
        self.__last_uploaded = current
        self.__processed_bytes += chunk_size

    async def __user_settings(self):
        user_dict = user_data.get(self.__user_id, {})
        self.__as_doc = user_dict.get('as_doc', False) or (config_dict['AS_DOCUMENT'] if 'as_doc' not in user_dict else False)
        self.__media_group = user_dict.get('media_group') or (config_dict['MEDIA_GROUP'] if 'media_group' not in user_dict else False)
        self.__bot_pm = user_dict.get('bot_pm') or (config_dict['BOT_PM'] if 'bot_pm' not in user_dict else False)
        self.__mediainfo = user_dict.get('mediainfo') or (config_dict['SHOW_MEDIAINFO'] if 'mediainfo' not in user_dict else False)
        self.__upload_dest = ud if (ud:=self.__listener.upPath) and isinstance(ud, list) else [ud]
        self.__has_buttons = bool(config_dict['SAVE_MSG'] or self.__mediainfo or self.__leech_utils['screenshots'])
        if not await aiopath.exists(self.__thumb):
            self.__thumb = None

    async def __msg_to_reply(self):
        msg_link = self.__listener.message.link if self.__listener.isSuperGroup else ''
        msg_user = self.__listener.message.from_user
        if config_dict['LEECH_LOG_ID'] and not self.__listener.excep_chat:
            try:
                self.__leechmsg = await sendMultiMessage(config_dict['LEECH_LOG_ID'], BotTheme('L_LOG_START', mention=msg_user.mention(style='HTML'), uid=msg_user.id, msg_link=self.__listener.source_url))
            except Exception as er:
                await self.__listener.onUploadError(str(er))
                return False
            self.__sent_msg = list(self.__leechmsg.values())[0]
        elif IS_PREMIUM_USER:
            if not self.__listener.isSuperGroup:
                await self.__listener.onUploadError('Use SuperGroup to leech with User Client! or Set LEECH_LOG_ID to Leech in PM')
                return False
            self.__sent_msg = self.__listener.message
        else:
            self.__sent_msg = self.__listener.message
        return True

    async def __prepare_file(self, prefile_, dirpath):
        try:
            file_, cap_mono = await format_filename(prefile_, self.__user_id, dirpath)
        except Exception as err:
            LOGGER.info(format_exc())
            return await self.__listener.onUploadError(f'Error in Format Filename : {err}')
        if prefile_ != file_:
            if self.__listener.seed and not self.__listener.newDir and not dirpath.endswith("/splited_files_mltb"):
                dirpath = f'{dirpath}/copied_mltb'
                await makedirs(dirpath, exist_ok=True)
                new_path = ospath.join(dirpath, file_)
                self.__up_path = await copy(self.__up_path, new_path)
            else:
                new_path = ospath.join(dirpath, file_)
                await aiorename(self.__up_path, new_path)
                self.__up_path = new_path
        if len(file_) > 64:
            if is_archive(file_):
                name = get_base_name(file_)
                ext = file_.split(name, 1)[1]
            elif match := re_match(r'.+(?=\..+\.0*\d+$)|.+(?=\.part\d+\..+)', file_):
                name = match.group(0)
                ext = file_.split(name, 1)[1]
            elif len(fsplit := ospath.splitext(file_)) > 1:
                name = fsplit[0]
                ext = fsplit[1]
            else:
                name = file_
                ext = ''
            extn = len(ext)
            remain = 64 - extn
            name = name[:remain]
            if self.__listener.seed and not self.__listener.newDir and not dirpath.endswith("/splited_files_mltb"):
                dirpath = f'{dirpath}/copied_mltb'
                await makedirs(dirpath, exist_ok=True)
                new_path = ospath.join(dirpath, f"{name}{ext}")
                self.__up_path = await copy(self.__up_path, new_path)
            else:
                new_path = ospath.join(dirpath, f"{name}{ext}")
                await aiorename(self.__up_path, new_path)
                self.__up_path = new_path
        return cap_mono, file_

    def __get_input_media(self, subkey, key):
        rlist = []
        for msg in self.__media_dict[key][subkey]:
            if key == 'videos':
                input_media = InputMediaVideo(
                    media=msg.video.file_id, caption=msg.caption)
            else:
                input_media = InputMediaDocument(
                    media=msg.document.file_id, caption=msg.caption)
            rlist.append(input_media)
        return rlist

    async def __switching_client(self):
        LOGGER.info(f'Uploading Media {">" if self.__prm_media else "<"} 2GB by {"User" if self.__prm_media else "Bot"} Client')
        self.__client = user if (self.__prm_media and IS_PREMIUM_USER) else bot

    async def __send_media_group(self, subkey, key, msgs):
        msgs_list = await msgs[0].reply_to_message.reply_media_group(media=self.__get_input_media(subkey, key),
                                                                    quote=True, disable_notification=True)
        for msg in msgs:
            if msg.link in self.__msgs_dict:
                del self.__msgs_dict[msg.link]
            await deleteMessage(msg)
        del self.__media_dict[key][subkey]
        if self.__listener.isSuperGroup or config_dict['LEECH_LOG_ID']:
            for m in msgs_list:
                self.__msgs_dict[m.link] = m.caption
        self.__sent_msg = msgs_list[-1]
        try:
            if self.__bot_pm and (self.__leechmsg and not self.__listener.excep_chat or self.__listener.isSuperGroup):
                await bot.copy_media_group(chat_id=self.__user_id, from_chat_id=self.__sent_msg.chat.id, message_id=self.__sent_msg.id)
        except Exception as err:
            if not self.__is_cancelled:
                LOGGER.error(f"Failed To Send in Bot PM:\n{str(err)}")
        try:
            if self.__upload_dest:
                for channel_id in self.__upload_dest:
                    if dump_chat := (await chat_info(channel_id)):
                        try:
                            await bot.copy_media_group(chat_id=dump_chat.id, from_chat_id=self.__sent_msg.chat.id, message_id=self.__sent_msg.id)
                        except (ChannelInvalid, PeerIdInvalid) as e:
                            LOGGER.error(f"{e.NAME}: {e.MESSAGE} for {channel_id}")
                            continue
        except Exception as err:
            if not self.__is_cancelled:
                LOGGER.error(f"Failed To Send in User Dump:\n{str(err)}")

    async def upload(self, o_files, m_size, size):
        await self.__user_settings()
        res = await self.__msg_to_reply()
        if not res:
            return
        isDeleted = False
        for dirpath, _, files in sorted(await sync_to_async(walk, self.__path)):
            if dirpath.endswith('/yt-dlp-thumb'):
                continue
            for file_ in natsorted(files):
                self.__up_path = ospath.join(dirpath, file_)
                if file_.lower().endswith(tuple(GLOBAL_EXTENSION_FILTER)):
                    await aioremove(self.__up_path)
                    continue
                try:
                    f_size = await aiopath.getsize(self.__up_path)
                    if self.__listener.seed and file_ in o_files and f_size in m_size:
                        continue
                    self.__total_files += 1
                    if f_size == 0:
                        LOGGER.error(f"{self.__up_path} size is zero, telegram don't upload zero size files")
                        self.__corrupted += 1
                        continue
                    if self.__is_cancelled:
                        return
                    self.__prm_media = True if f_size > 2097152000 else False
                    cap_mono, file_ = await self.__prepare_file(file_, dirpath)
                    if self.__last_msg_in_group:
                        group_lists = [x for v in self.__media_dict.values()
                                       for x in v.keys()]
                        if (match := re_match(r'.+(?=\.0*\d+$)|.+(?=\.part\d+\..+)', self.__up_path)) and match.group(0) not in group_lists:
                            for key, value in list(self.__media_dict.items()):
                                for subkey, msgs in list(value.items()):
                                    if len(msgs) > 1:
                                        await self.__send_media_group(subkey, key, msgs)
                    self.__last_msg_in_group = False
                    self.__last_uploaded = 0
                    await self.__switching_client()
                    await self.__upload_file(cap_mono, file_)
                    if self.__leechmsg and not isDeleted and config_dict['CLEAN_LOG_MSG']:
                        await deleteMessage(list(self.__leechmsg.values())[0])
                        isDeleted = True
                    if self.__is_cancelled:
                        return
                    if not self.__is_corrupted and (self.__listener.isSuperGroup or config_dict['LEECH_LOG_ID']):
                        self.__msgs_dict[self.__sent_msg.link] = file_
                    await sleep(1)
                except Exception as err:
                    if isinstance(err, RetryError):
                        LOGGER.info(f"Total Attempts: {err.last_attempt.attempt_number}")
                    else:
                        LOGGER.error(f"{format_exc()}. Path: {self.__up_path}")
                    if self.__is_cancelled:
                        return
                    continue
                finally:
                    if not self.__is_cancelled and await aiopath.exists(self.__up_path) and \
                        (not self.__listener.seed or self.__listener.newDir or
                         dirpath.endswith("/splited_files_mltb") or '/copied_mltb/' in self.__up_path):
                        await aioremove(self.__up_path)
        for key, value in list(self.__media_dict.items()):
            for subkey, msgs in list(value.items()):
                if len(msgs) > 1:
                    await self.__send_media_group(subkey, key, msgs)
        if self.__is_cancelled:
            return
        if self.__listener.seed and not self.__listener.newDir:
            await clean_unwanted(self.__path)
        if self.__total_files == 0:
            await self.__listener.onUploadError("No files to upload. In case you have filled EXTENSION_FILTER, then check if all files have those extensions or not.")
            return
        if self.__total_files <= self.__corrupted:
            await self.__listener.onUploadError('Files Corrupted or unable to upload. Check logs!')
            return
        if self.__retry_error:
            await self.__listener.onUploadError('Unknown Error Occurred. Check logs & Contact Bot Owner!')
            return
        LOGGER.info(f"Leech Completed: {self.name}")
        await self.__listener.onUploadComplete(None, size, self.__msgs_dict, self.__total_files, self.__corrupted, self.name)

    @retry(wait=wait_exponential(multiplier=2, min=4, max=8), stop=stop_after_attempt(3),
           retry=retry_if_exception_type(Exception))
    async def __upload_file(self, cap_mono, file, force_document=False):
        if self.__thumb is not None and not await aiopath.exists(self.__thumb):
            self.__thumb = None
        thumb = self.__thumb
        self.__is_corrupted = False
        try:
            is_video, is_audio, is_image = await get_document_type(self.__up_path)

            if self.__leech_utils['thumb']:
                thumb = await self.get_custom_thumb(self.__leech_utils['thumb'])
            
            if not is_image and thumb is None:
                file_name = ospath.splitext(file)[0]
                thumb_path = f"{self.__path}/yt-dlp-thumb/{file_name}.jpg"
                if await aiopath.isfile(thumb_path):
                    thumb = thumb_path
                elif is_audio and not is_video:
                    thumb = await get_audio_thumb(self.__up_path)

            if self.__as_doc or force_document or (not is_video and not is_audio and not is_image):
                key = 'documents'
                if is_video and thumb is None:
                    thumb = await take_ss(self.__up_path, None)
                if self.__is_cancelled:
                    return
                buttons = await self.__buttons(self.__up_path, is_video)
                nrml_media = await self.__client.send_document(chat_id=self.__sent_msg.chat.id,
                                                                       reply_to_message_id=self.__sent_msg.id,
                                                                       document=self.__up_path,
                                                                       thumb=thumb,
                                                                       caption=cap_mono,
                                                                       force_document=True,
                                                                       disable_notification=True,
                                                                       progress=self.__upload_progress,
                                                                       reply_markup=buttons)
                
                if self.__prm_media and (self.__has_buttons or not self.__leechmsg):
                    try:
                        self.__sent_msg = await bot.copy_message(nrml_media.chat.id, nrml_media.chat.id, nrml_media.id, reply_to_message_id=self.__sent_msg.id, reply_markup=buttons)
                        if self.__sent_msg: await deleteMessage(nrml_media)
                    except:
                        self.__sent_msg = nrml_media
                else:
                    self.__sent_msg = nrml_media
            elif is_video:
                key = 'videos'
                duration = (await get_media_info(self.__up_path))[0]
                if thumb is None:
                    thumb = await take_ss(self.__up_path, duration)
                if thumb is not None:
                    with Image.open(thumb) as img:
                        width, height = img.size
                else:
                    width = 480
                    height = 320
                if not self.__up_path.upper().endswith(("MKV", "MP4")):
                    dirpath, file_ = self.__up_path.rsplit('/', 1)
                    if self.__listener.seed and not self.__listener.newDir and not dirpath.endswith("/splited_files_mltb"):
                        dirpath = f"{dirpath}/copied_mltb"
                        await makedirs(dirpath, exist_ok=True)
                        new_path = ospath.join(
                            dirpath, f"{ospath.splitext(file_)[0]}.mp4")
                        self.__up_path = await copy(self.__up_path, new_path)
                    else:
                        new_path = f"{ospath.splitext(self.__up_path)[0]}.mp4"
                        await aiorename(self.__up_path, new_path)
                        self.__up_path = new_path
                if self.__is_cancelled:
                    return
                buttons = await self.__buttons(self.__up_path, is_video)
                nrml_media = await self.__client.send_video(chat_id=self.__sent_msg.chat.id,
                                                                    reply_to_message_id=self.__sent_msg.id,
                                                                    video=self.__up_path,
                                                                    caption=cap_mono,
                                                                    duration=duration,
                                                                    width=width,
                                                                    height=height,
                                                                    thumb=thumb,
                                                                    supports_streaming=True,
                                                                    disable_notification=True,
                                                                    progress=self.__upload_progress,
                                                                    reply_markup=buttons)
                if self.__prm_media and (self.__has_buttons or not self.__leechmsg):
                    try:
                        self.__sent_msg = await bot.copy_message(nrml_media.chat.id, nrml_media.chat.id, nrml_media.id, reply_to_message_id=self.__sent_msg.id, reply_markup=buttons)
                        if self.__sent_msg: await deleteMessage(nrml_media)
                    except:
                        self.__sent_msg = nrml_media
                else:
                    self.__sent_msg = nrml_media
            elif is_audio:
                key = 'audios'
                duration, artist, title = await get_media_info(self.__up_path)
                if self.__is_cancelled:
                    return
                self.__sent_msg = await self.__client.send_audio(chat_id=self.__sent_msg.chat.id,
                                                                    reply_to_message_id=self.__sent_msg.id,
                                                                    audio=self.__up_path,
                                                                    caption=cap_mono,
                                                                    duration=duration,
                                                                    performer=artist,
                                                                    title=title,
                                                                    thumb=thumb,
                                                                    disable_notification=True,
                                                                    progress=self.__upload_progress,
                                                                    reply_markup=await self.__buttons(self.__up_path))
            else:
                key = 'photos'
                if self.__is_cancelled:
                    return
                self.__sent_msg = await self.__client.send_photo(chat_id=self.__sent_msg.chat.id,
                                                                    reply_to_message_id=self.__sent_msg.id,
                                                                    photo=self.__up_path,
                                                                    caption=cap_mono,
                                                                    disable_notification=True,
                                                                    progress=self.__upload_progress,
                                                                    reply_markup=await self.__buttons(self.__up_path))

            if not self.__is_cancelled and self.__media_group and (self.__sent_msg.video or self.__sent_msg.document):
                key = 'documents' if self.__sent_msg.document else 'videos'
                if match := re_match(r'.+(?=\.0*\d+$)|.+(?=\.part\d+\..+)', self.__up_path):
                    pname = match.group(0)
                    if pname in self.__media_dict[key].keys():
                        self.__media_dict[key][pname].append(self.__sent_msg)
                    else:
                        self.__media_dict[key][pname] = [self.__sent_msg]
                    msgs = self.__media_dict[key][pname]
                    if len(msgs) == 10:
                        await self.__send_media_group(pname, key, msgs)
                    else:
                        self.__last_msg_in_group = True
            if self.__sent_msg:
                await self.__copy_file()

            if self.__thumb is None and thumb is not None and await aiopath.exists(thumb):
                await aioremove(thumb)
                if (dir_name := ospath.dirname(thumb)) and dir_name != "Thumbnails" and await aiopath.exists(dir_name):
                    await rmdir(dir_name)
            self.__retry_error = False
        except FloodWait as f:
            LOGGER.warning(str(f))
            await sleep(f.value)
        except Exception as err:
            self.__retry_error = True
            if self.__thumb is None and thumb is not None and await aiopath.exists(thumb):
                await aioremove(thumb)
                if (dir_name := ospath.dirname(thumb)) and dir_name != "Thumbnails" and await aiopath.exists(dir_name):
                    await rmdir(dir_name)
            LOGGER.error(f"{format_exc()}. Path: {self.__up_path}")
            if 'Telegram says: [400' in str(err) and key != 'documents':
                LOGGER.error(f"Retrying As Document. Path: {self.__up_path}")
                return await self.__upload_file(cap_mono, file, True)
            raise err

    @property
    def speed(self):
        try:
            return self.__processed_bytes / (time() - self.__start_time)
        except:
            return 0

    @property
    def processed_bytes(self):
        return self.__processed_bytes

    async def cancel_download(self):
        self.__is_cancelled = True
        LOGGER.info(f"Cancelling Upload: {self.name}")
        await self.__listener.onUploadError('Your Upload has been Stopped!')
