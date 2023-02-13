from logging import getLogger, ERROR
from traceback import format_exc
from os import remove as osremove, walk, path as ospath, rename as osrename
from time import time
from asyncio import sleep as asleep
from pyrogram.errors import FloodWait, RPCError
from pyrogram.enums import ChatType
from PIL import Image
from threading import RLock
from bot import user_data, GLOBAL_EXTENSION_FILTER, app, tgBotMaxFileSize, premium_session, config_dict, OWNER_ID, main_loop, bot
from bot.helper.telegram_helper.button_build import ButtonMaker
from bot.helper.ext_utils.fs_utils import take_ss, get_media_info, get_media_streams, clean_unwanted, getMediaInfo
from bot.helper.ext_utils.bot_utils import get_readable_file_size, change_filename, get_bot_pm, is_paid, is_sudo
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup

LOGGER = getLogger(__name__)
getLogger("pyrogram").setLevel(ERROR)
IMAGE_SUFFIXES = ("JPG", "JPX", "PNG", "CR2", "TIF", "BMP",
                  "JXR", "PSD", "ICO", "HEIC", "JPEG")


class TgUploader:

    def __init__(self, name=None, path=None, size=0, listener=None):
        self.name = name
        self.uploaded_bytes = 0
        self._last_uploaded = 0
        self.__listener = listener
        self.__path = path
        self.__start_time = time()
        self.__total_files = 0
        self.__is_cancelled = False
        self.__as_doc = config_dict['AS_DOCUMENT']
        self.__thumb = f"Thumbnails/{listener.message.from_user.id}.jpg"
        self.__msgs_dict = {}
        self.__corrupted = 0
        self.__resource_lock = RLock()
        self.__is_corrupted = False
        self.__size = size
        self.__user_settings()
        self.__leech_log = user_data.get('is_leech_log')
        self.__app = app if app is not None else bot
        self.__user_id = listener.message.from_user.id
        self.isPrivate = listener.message.chat.type in [ChatType.PRIVATE, ChatType.GROUP]

    async def upload(self, o_files):
        self.__sent_msg = await bot.get_messages(self.__listener.message.chat.id, self.__listener.uid)
        for dirpath, subdir, files in sorted(walk(self.__path)):
            for file_ in sorted(files):
                if file_ in o_files:
                    continue
                if not file_.lower().endswith(tuple(GLOBAL_EXTENSION_FILTER)):
                    up_path = ospath.join(dirpath, file_)
                    self.__total_files += 1
                    try:
                        if ospath.getsize(up_path) == 0:
                            LOGGER.error(
                                f"{up_path} size is zero, telegram don't upload zero size files")
                            self.__corrupted += 1
                            continue
                    except Exception as e:
                        if self.__is_cancelled:
                            return
                        LOGGER.error(e)
                        continue
                    await self.__upload_file(up_path, file_, dirpath)
                    if self.__is_cancelled:
                        return
                    if not self.__listener.isPrivate and not self.__is_corrupted:
                        self.__msgs_dict[self.__sent_msg.link] = file_
                    self._last_uploaded = 0
                    await asleep(1)
        if self.__listener.seed and not self.__listener.newDir:
            await clean_unwanted(self.__path)
        if self.__total_files == 0:
            await self.__listener.onUploadError('No files to upload. Make sure if you filled USER_SESSION_STRING then you should use supergroup. In case you filled EXTENSION_FILTER then check if all file have this extension')
            return
        if self.__total_files <= self.__corrupted:
            await self.__listener.onUploadError('Files Corrupted. Check logs!')
            return
        LOGGER.info(f"Leech Completed: {self.name}")
        size = get_readable_file_size(self.__size)
        await self.__listener.onUploadComplete(None, size, self.__msgs_dict, self.__total_files, self.__corrupted, self.name)

    async def __upload_file(self, up_path, file_, dirpath):
        fsize = ospath.getsize(up_path)
        user_id_ = self.__listener.message.from_user.id
        self.__sent_msg = await bot.get_messages(self.__listener.message.chat.id, self.__listener.uid)


        client = premium_session if fsize > 2097152000 else app
        up_path, file_, cap_mono = change_filename(
            file_, user_id_, dirpath, up_path)

        dumpid = user_data[user_id_].get(
            'userlog') if user_id_ in user_data and user_data[user_id_].get('userlog') else ''
        LEECH_X = int(dumpid) if len(
            dumpid) != 0 else user_data.get('is_log_leech', [''])[0]

        BOT_PM_X = get_bot_pm(user_id_)

        notMedia = False
        thumb = self.__thumb
        default_thumb = "Thumbnails/default.jpg"
        self.__is_corrupted = False
        try:
            is_video, is_audio = get_media_streams(up_path)
            if not self.__as_doc:
                if is_video:
                    duration = get_media_info(up_path)[0]
                    if thumb is None:
                        if user_id_ != OWNER_ID and not is_sudo(user_id_) and not is_paid(user_id_) and ospath.lexists(default_thumb):
                            thumb = default_thumb
                        else:
                            thumb = take_ss(up_path, duration)
                        if self.__is_cancelled:
                            if self.__thumb is None and thumb is not None and thumb != default_thumb and ospath.lexists(thumb):
                                osremove(thumb)
                            return
                    if thumb is not None:
                        with Image.open(thumb) as img:
                            width, height = img.size
                    else:
                        width = 480
                        height = 320
                    if not file_.upper().endswith(("MKV", "MP4")):
                        file_ = f"{ospath.splitext(file_)[0]}.mp4"
                        new_path = ospath.join(dirpath, file_)
                        osrename(up_path, new_path)
                        up_path = new_path
                    if 'is_leech_log' in user_data and user_data.get('is_leech_log'):
                        for leechchat in self.__leech_log:
                            if ospath.getsize(up_path) > tgBotMaxFileSize:
                                usingclient = premium_session
                            else:
                                usingclient = self.__app
                            self.__sent_msg = await usingclient.send_video(chat_id=int(leechchat), video=up_path,
                                                                           caption=cap_mono,
                                                                           duration=duration,
                                                                           width=width,
                                                                           height=height,
                                                                           thumb=thumb,
                                                                           supports_streaming=True,
                                                                           disable_notification=True,
                                                                           progress=self.__upload_progress)
                            if self.__sent_msg and (config_dict['SAVE_MSG'] or self.__mediainfo):
                                await self.__sent_msg.edit_reply_markup(self.__buttons(up_path))
                            if BOT_PM_X:
                                try:
                                    await bot.copy_message(chat_id=self.__user_id, from_chat_id=self.__sent_msg.chat.id, message_id=self.__sent_msg.id)
                                except Exception as err:
                                    LOGGER.error(
                                        f"Failed To Send Video in PM:\n{err}")
                            if len(dumpid) != 0:
                                try:
                                    await bot.copy_message(chat_id=LEECH_X, from_chat_id=self.__sent_msg.chat.id, message_id=self.__sent_msg.id)
                                except Exception as err:
                                    LOGGER.error(
                                        f"Failed To Send Video in dump:\n{err}")

                    else:
                        self.__sent_msg = await self.__sent_msg.reply_video(video=up_path,
                                                                            quote=True,
                                                                            caption=cap_mono,
                                                                            duration=duration,
                                                                            width=width,
                                                                            height=height,
                                                                            thumb=thumb,
                                                                            supports_streaming=True,
                                                                            disable_notification=True,
                                                                            progress=self.__upload_progress)
                        if self.__sent_msg and (config_dict['SAVE_MSG'] or self.__mediainfo):
                            await self.__sent_msg.edit_reply_markup(self.__buttons(up_path))
                        if not self.isPrivate and BOT_PM_X:
                            try:
                                await bot.copy_message(chat_id=self.__user_id, from_chat_id=self.__sent_msg.chat.id, message_id=self.__sent_msg.id)
                            except Exception as err:
                                LOGGER.error(
                                    f"Failed To Send Vedio in PM:\n{err}")
                elif is_audio:
                    duration, artist, title = get_media_info(up_path)
                    if 'is_leech_log' in user_data and user_data.get('is_leech_log'):
                        for leechchat in self.__leech_log:
                            if ospath.getsize(up_path) > tgBotMaxFileSize:
                                usingclient = premium_session
                            else:
                                usingclient = self.__app
                            self.__sent_msg = await usingclient.send_audio(chat_id=int(leechchat), audio=up_path,
                                                                           caption=cap_mono,
                                                                           duration=duration,
                                                                           performer=artist,
                                                                           title=title,
                                                                           thumb=thumb,
                                                                           disable_notification=True,
                                                                           progress=self.__upload_progress)
                            if self.__sent_msg and (config_dict['SAVE_MSG'] or self.__mediainfo):
                                await self.__sent_msg.edit_reply_markup(self.__buttons(up_path))
                            if BOT_PM_X:
                                try:
                                    await bot.copy_message(chat_id=self.__user_id, from_chat_id=self.__sent_msg.chat.id, message_id=self.__sent_msg.id)
                                except Exception as err:
                                    LOGGER.error(
                                        f"Failed To Send Audio in PM:\n{err}")
                            if len(dumpid) != 0:
                                try:
                                    await bot.copy_message(chat_id=LEECH_X, from_chat_id=self.__sent_msg.chat.id, message_id=self.__sent_msg.id)
                                except Exception as err:
                                    LOGGER.error(
                                        f"Failed To Send Audio in dump:\n{err}")
                    else:
                        self.__sent_msg = await self.__sent_msg.reply_audio(audio=up_path,
                                                                            quote=True,
                                                                            caption=cap_mono,
                                                                            duration=duration,
                                                                            performer=artist,
                                                                            title=title,
                                                                            thumb=thumb,
                                                                            disable_notification=True,
                                                                            progress=self.__upload_progress)
                        if self.__sent_msg and (config_dict['SAVE_MSG'] or self.__mediainfo):
                            await self.__sent_msg.edit_reply_markup(self.__buttons(up_path))
                        if not self.isPrivate and BOT_PM_X:
                            try:
                                await bot.copy_message(chat_id=self.__user_id, from_chat_id=self.__sent_msg.chat.id, message_id=self.__sent_msg.id)
                            except Exception as err:
                                LOGGER.error(
                                    f"Failed To Send Audio in PM:\n{err}")

                elif file_.upper().endswith(IMAGE_SUFFIXES):
                    if 'is_leech_log' in user_data and user_data.get('is_leech_log'):
                        for leechchat in self.__leech_log:
                            if ospath.getsize(up_path) > tgBotMaxFileSize:
                                usingclient = premium_session
                            else:
                                usingclient = self.__app
                            self.__sent_msg = await usingclient.send_photo(chat_id=int(leechchat),
                                                                           photo=up_path,
                                                                           caption=cap_mono,
                                                                           disable_notification=True,
                                                                           progress=self.__upload_progress)
                            if BOT_PM_X:
                                try:
                                    await bot.copy_message(chat_id=self.__user_id, from_chat_id=self.__sent_msg.chat.id, message_id=self.__sent_msg.id)
                                except Exception as err:
                                    LOGGER.error(
                                        f"Failed To Send Image in PM:\n{err}")
                            if len(dumpid) != 0:
                                try:
                                    await bot.copy_message(chat_id=LEECH_X, from_chat_id=self.__sent_msg.chat.id, message_id=self.__sent_msg.id)
                                except Exception as err:
                                    LOGGER.error(
                                        f"Failed To Send Image in dump:\n{err}")
                    else:
                        self.__sent_msg = await self.__sent_msg.reply_photo(photo=up_path,
                                                                            quote=True,
                                                                            caption=cap_mono,
                                                                            disable_notification=True,
                                                                            progress=self.__upload_progress)
                        if not self.isPrivate and BOT_PM_X:
                            try:
                                await bot.copy_message(chat_id=self.__user_id, from_chat_id=self.__sent_msg.chat.id, message_id=self.__sent_msg.id)
                            except Exception as err:
                                LOGGER.error(
                                    f"Failed To Send Image in PM:\n{err}")
                else:
                    notMedia = True
            if self.__as_doc or notMedia:
                if is_video and thumb is None:
                    if user_id_ != OWNER_ID and not is_sudo(user_id_) and not is_paid(user_id_) and ospath.lexists(default_thumb):
                        thumb = default_thumb
                    else:
                        thumb = take_ss(up_path, None)
                    if self.__is_cancelled:
                        if self.__thumb is None and thumb is not None and thumb != default_thumb and ospath.lexists(thumb):
                            osremove(thumb)
                        return
                if 'is_leech_log' in user_data and user_data.get('is_leech_log'):
                    for leechchat in self.__leech_log:
                        if ospath.getsize(up_path) > tgBotMaxFileSize:
                            usingclient = premium_session
                        else:
                            usingclient = self.__app
                        self.__sent_msg = await usingclient.send_document(chat_id=int(leechchat),
                                                                          document=up_path,
                                                                          thumb=thumb,
                                                                          caption=cap_mono,
                                                                          disable_notification=True,
                                                                          progress=self.__upload_progress)
                        if self.__sent_msg and (config_dict['SAVE_MSG'] or self.__mediainfo):
                            await self.__sent_msg.edit_reply_markup(self.__buttons(up_path))
                        if len(dumpid) != 0:
                            try:
                                await bot.copy_message(chat_id=LEECH_X, from_chat_id=self.__sent_msg.chat.id, message_id=self.__sent_msg.id)
                            except Exception as err:
                                LOGGER.error(
                                    f"Failed To Send Document in dump:\n{err}")
                        if BOT_PM_X:
                            try:
                                await bot.copy_message(chat_id=self.__user_id, from_chat_id=self.__sent_msg.chat.id, message_id=self.__sent_msg.id)
                            except Exception as err:
                                LOGGER.error(
                                    f"Failed To Send Document in PM:\n{err}")
                else:
                    self.__sent_msg = await self.__sent_msg.reply_document(document=up_path,
                                                                           quote=True,
                                                                           thumb=thumb,
                                                                           caption=cap_mono,
                                                                           disable_notification=True,
                                                                           progress=self.__upload_progress)
                    if self.__sent_msg and (config_dict['SAVE_MSG'] or self.__mediainfo):
                        await self.__sent_msg.edit_reply_markup(self.__buttons(up_path))
                    if not self.isPrivate and BOT_PM_X:
                        try:
                            await bot.copy_message(chat_id=self.__user_id, from_chat_id=self.__sent_msg.chat.id, message_id=self.__sent_msg.id)
                        except Exception as err:
                            LOGGER.error(
                                f"Failed To Send Document in PM:\n{err}")
        except FloodWait as f:
            LOGGER.warning(str(f))
            await asleep(f.value)
        except RPCError as e:
            LOGGER.error(f"RPCError: {e} | Path: {up_path}")
            self.__corrupted += 1
            self.__is_corrupted = True
        except Exception as err:
            LOGGER.error(f"{format_exc()} | Path: {up_path}")
            self.__corrupted += 1
            self.__is_corrupted = True
        if self.__thumb is None and thumb is not None and thumb != default_thumb and ospath.lexists(thumb):
            osremove(thumb)
        if not self.__is_cancelled and \
                (not self.__listener.seed or self.__listener.newDir or dirpath.endswith("splited_files_mltb")):
            try:
                osremove(up_path)
            except:
                pass

    def __upload_progress(self, current, total):
        if self.__is_cancelled:
            self.__app.stop_transmission()
            return
        with self.__resource_lock:
            chunk_size = current - self._last_uploaded
            self._last_uploaded = current
            self.uploaded_bytes += chunk_size

    def __user_settings(self):
        user_id = self.__listener.message.from_user.id
        user_dict = user_data.get(user_id, False)
        if user_dict:
            self.__as_doc = user_dict.get('as_doc', config_dict['AS_DOCUMENT'])
            self.__mediainfo = user_dict.get('mediainfo', config_dict['MEDIAINFO_MODE'])
        if not ospath.lexists(self.__thumb):
            self.__thumb = None

    def __buttons(self, up_path):
        bn = ButtonMaker()
        if self.__mediainfo:
            bn.buildbutton('MediaInfo', getMediaInfo(up_path))
        if config_dict['SAVE_MSG']:
            bn.sbutton('Save Message', 'save', 'footer')
        return bn.build_menu(1)

    @property
    def speed(self):
        with self.__resource_lock:
            try:
                return self.uploaded_bytes / (time() - self.__start_time)
            except:
                return 0

    def cancel_download(self):
        self.__is_cancelled = True
        LOGGER.info(f"Cancelling Upload: {self.name}")
        main_loop.create_task(self.__listener.onUploadError(
            'Your upload has been stopped!'))
