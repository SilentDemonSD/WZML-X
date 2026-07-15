from asyncio import ensure_future, gather, sleep
from logging import getLogger
from os import path as ospath, walk
from re import match as re_match, sub as re_sub
from time import time

from aioshutil import rmtree
from natsort import natsorted
from pyrogram import StopTransmission
from pyrogram.enums import ChatType
from pyrogram.errors import FloodWait, RPCError

try:
    from pyrogram.errors import FloodPremiumWait
except ImportError:
    FloodPremiumWait = FloodWait

from aiofiles.os import (
    path as aiopath,
    remove,
    rename,
)
from pyrogram.types import (
    InputMediaDocument,
    InputMediaPhoto,
    InputMediaVideo,
    ReplyParameters,
)

from ....core.config_manager import Config
from ....core.tg_client import TgClient
from ...ext_utils.bot_utils import sync_to_async
from ...ext_utils.files_utils import get_base_name, is_archive
from ...ext_utils.status_utils import get_readable_file_size, get_readable_time

from ...ext_utils.media_utils import get_md5_hash, get_media_info
from ...telegram_helper.message_utils import delete_message
from ...ext_utils.hyperul_utils import HypertgUpload

LOGGER = getLogger(__name__)


async def _call_with_flood_retry(method, *args, **kwargs):
    while True:
        try:
            return await method(*args, **kwargs)
        except (FloodWait, FloodPremiumWait) as f:
            LOGGER.warning(f"FloodWait {f.value}s, retrying {method.__name__}")
            await sleep(f.value + 1)


class TelegramUploader:
    def __init__(self, listener, path):
        self._processed_bytes = 0
        self._listener = listener
        self._path = path
        self._start_time = time()
        self._total_files = 0
        self._thumb = self._listener.thumb or f"thumbnails/{listener.user_id}.jpg"
        self._msgs_dict = {}
        self._corrupted = 0
        self._is_corrupted = False
        self._media_dict = {"videos": {}, "documents": {}}
        self._last_msg_in_group = False
        self._lprefix = ""
        self._lsuffix = ""
        self._lcaption = ""
        self._lfont = ""
        self._bot_pm = False
        self._media_group = False
        self._is_private = False
        self._sent_msg = None
        self._user_session = self._listener.transmission_mode in ("user", "both")
        self._hu: HypertgUpload | None = None
        self._error = ""
        self._upload_seq = []
        self._msg_to_seq = {}

    async def _user_settings(self):
        settings_map = {
            "MEDIA_GROUP": ("_media_group", False),
            "BOT_PM": ("_bot_pm", False),
            "LEECH_PREFIX": ("_lprefix", ""),
            "LEECH_SUFFIX": ("_lsuffix", ""),
            "LEECH_CAPTION": ("_lcaption", ""),
            "LEECH_FONT": ("_lfont", ""),
        }

        for key, (attr, default) in settings_map.items():
            setattr(
                self,
                attr,
                self._listener.user_dict.get(key) or getattr(Config, key, default),
            )

        if self._thumb != "none" and not await aiopath.exists(self._thumb):
            self._thumb = None

    async def _msg_to_reply(self):
        if self._user_session and TgClient.user is None:
            self._user_session = False

        if self._user_session:
            try:
                self._sent_msg = await _call_with_flood_retry(
                    self._listener.client.get_messages,
                    chat_id=self._listener.message.chat.id,
                    message_ids=self._listener.mid,
                )
            except Exception:
                self._sent_msg = None
            if self._sent_msg is None or self._sent_msg.chat is None:
                try:
                    self._sent_msg = await _call_with_flood_retry(
                        self._listener.client.send_message,
                        chat_id=self._listener.message.chat.id,
                        text="Deleted Cmd Message! Don't delete the cmd message again!",
                        disable_web_page_preview=True,
                        disable_notification=True,
                    )
                except Exception:
                    self._sent_msg = self._listener.message
            if self._sent_msg is None or self._sent_msg.chat is None:
                self._sent_msg = self._listener.message
            self._is_private = self._sent_msg.chat.type == ChatType.PRIVATE
        else:
            self._sent_msg = self._listener.message
            self._is_private = self._sent_msg.chat.type == ChatType.PRIVATE

        return True

    async def _prepare_file(self, pre_file_, dirpath):
        cap_file_ = file_ = pre_file_
        lprefix = self._lprefix
        lsuffix = self._lsuffix
        lcaption = self._lcaption

        if lprefix:
            cap_file_ = lprefix.replace(r"\s", " ") + file_
            lprefix = re_sub(r"<.*?>", "", lprefix).replace(r"\s", " ")
            if not file_.startswith(lprefix):
                file_ = f"{lprefix}{file_}"

        if lsuffix:
            name, ext = ospath.splitext(cap_file_)
            cap_file_ = name + lsuffix.replace(r"\s", " ") + ext
            lsuffix = re_sub(r"<.*?>", "", lsuffix).replace(r"\s", " ")

        cap_mono = (
            f"<{Config.LEECH_FONT}>{cap_file_}</{Config.LEECH_FONT}>"
            if Config.LEECH_FONT
            else cap_file_
        )
        if lcaption:
            lcaption = re_sub(
                r"(\\\||\\\{|\\\}|\\s)",
                lambda m: {r"\|": "%%", r"\{": "&%&", r"\}": "$%$", r"\s": " "}[
                    m.group(0)
                ],
                lcaption,
            )

            parts = lcaption.split("|")
            parts[0] = re_sub(
                r"\{([^}]+)\}", lambda m: f"{{{m.group(1).lower()}}}", parts[0]
            )
            up_path = ospath.join(dirpath, pre_file_)
            dur, qual, lang, subs = await get_media_info(up_path, True)
            cap_mono = parts[0].format(
                filename=cap_file_,
                size=get_readable_file_size(await aiopath.getsize(up_path)),
                duration=get_readable_time(dur),
                quality=qual,
                languages=lang,
                subtitles=subs,
                md5_hash=await sync_to_async(get_md5_hash, up_path),
                mime_type=self._listener.file_details.get("mime_type", "text/plain"),
                prefilename=self._listener.file_details.get("filename", ""),
                precaption=self._listener.file_details.get("caption", ""),
            )

            for part in parts[1:]:
                args = part.split(":")
                cap_mono = cap_mono.replace(
                    args[0],
                    args[1] if len(args) > 1 else "",
                    int(args[2]) if len(args) == 3 else -1,
                )
            cap_mono = re_sub(
                r"%%|&%&|\$%\$",
                lambda m: {"%%": "|", "&%&": "{", "$%$": "}"}[m.group()],
                cap_mono,
            )

        if len(file_) > 60:
            if is_archive(file_):
                name = get_base_name(file_)
                ext = file_.split(name, 1)[1]
            elif match := re_match(r".+(?=\..+\.0*\d+$)|.+(?=\.part\d+\..+$)", file_):
                name = match.group(0)
                ext = file_.split(name, 1)[1]
            elif len(fsplit := ospath.splitext(file_)) > 1:
                name = fsplit[0]
                ext = fsplit[1]
            else:
                name = file_
                ext = ""
            if lsuffix:
                ext = f"{lsuffix}{ext}"
            name = name[: 64 - len(ext)]
            file_ = f"{name}{ext}"
        elif lsuffix:
            name, ext = ospath.splitext(file_)
            file_ = f"{name}{lsuffix}{ext}"

        old_path = ospath.join(dirpath, pre_file_)
        new_path = ospath.join(dirpath, file_)
        if old_path != new_path:
            await rename(old_path, new_path)

        return new_path, cap_mono

    def _get_input_media(self, subkey, key):
        rlist = []
        for msg in self._media_dict[key][subkey]:
            if key == "videos":
                input_media = InputMediaVideo(
                    media=msg.video.file_id, caption=msg.caption
                )
            else:
                input_media = InputMediaDocument(
                    media=msg.document.file_id, caption=msg.caption
                )
            rlist.append(input_media)
        return rlist

    async def _send_screenshots(self, dirpath, outputs):
        inputs = [
            InputMediaPhoto(ospath.join(dirpath, p), p.rsplit("/", 1)[-1])
            for p in outputs
        ]
        for i in range(0, len(inputs), 10):
            batch = inputs[i : i + 10]
            if Config.BOT_PM:
                await _call_with_flood_retry(
                    TgClient.bot.send_media_group,
                    chat_id=self._listener.user_id,
                    media=batch,
                    disable_notification=True,
                )
            self._sent_msg = (
                await _call_with_flood_retry(
                    self._sent_msg.reply_media_group,
                    media=batch,
                    reply_parameters=ReplyParameters(message_id=self._sent_msg.id),
                    disable_notification=True,
                )
            )[-1]

    async def _send_media_group(self, subkey, key, msgs):
        old_ids = [(msg[0], msg[1]) for msg in msgs]
        for index, msg in enumerate(msgs):
            if self._listener.transmission_mode == "both" or not self._user_session:
                msgs[index] = await _call_with_flood_retry(
                    self._listener.client.get_messages,
                    chat_id=msg[0],
                    message_ids=msg[1],
                )
            else:
                msgs[index] = await _call_with_flood_retry(
                    TgClient.user.get_messages, chat_id=msg[0], message_ids=msg[1]
                )
        msgs_list = await _call_with_flood_retry(
            msgs[0].reply_to_message.reply_media_group,
            media=self._get_input_media(subkey, key),
            reply_parameters=ReplyParameters(message_id=msgs[0].reply_to_message.id),
            disable_notification=True,
        )
        for msg in msgs:
            if msg.link in self._msgs_dict:
                del self._msgs_dict[msg.link]
            await delete_message(msg)
        del self._media_dict[key][subkey]
        if self._listener.is_super_chat or self._listener.up_dest:
            for m in msgs_list:
                self._msgs_dict[m.link] = m.caption
        for i, (old_cid, old_mid) in enumerate(old_ids):
            old_key = (old_cid, old_mid)
            if old_key in self._msg_to_seq:
                seq_idx = self._msg_to_seq.pop(old_key)
                new_msg = msgs_list[i]
                self._upload_seq[seq_idx] = {
                    "chat_id": new_msg.chat.id,
                    "msg_id": new_msg.id,
                    "link": new_msg.link,
                    "file_": self._upload_seq[seq_idx]["file_"],
                }
                self._msg_to_seq[(new_msg.chat.id, new_msg.id)] = seq_idx
        self._sent_msg = msgs_list[-1]

    async def _copy_media(self):
        try:
            if self._bot_pm:
                await _call_with_flood_retry(
                    TgClient.bot.copy_message,
                    chat_id=self._listener.user_id,
                    from_chat_id=self._sent_msg.chat.id,
                    message_id=self._sent_msg.id,
                    reply_to_message_id=(
                        self._listener.pm_msg.id if self._listener.pm_msg else None
                    ),
                )
        except Exception as err:
            if not self._listener.is_cancelled:
                err_msg = str(err)
                if "Can't copy" in err_msg:
                    LOGGER.warning(
                        f"BotPM copy skipped (restricted content): {err_msg}"
                    )
                else:
                    LOGGER.error(f"Failed To Send in BotPM:\n{err_msg}")

    async def _sequence_copies(self, src_chat):
        for entry in self._upload_seq:
            if entry is None:
                continue
            chat_id = entry["chat_id"]
            msg_id = entry["msg_id"]
            copy_from_chat = chat_id
            copy_from_msg = msg_id
            in_dump = chat_id != src_chat.id and not self._listener.up_dest
            if in_dump:
                try:
                    bot_copy = await _call_with_flood_retry(
                        TgClient.bot.copy_message,
                        chat_id=src_chat.id,
                        from_chat_id=chat_id,
                        message_id=msg_id,
                    )
                    copy_from_chat = src_chat.id
                    copy_from_msg = bot_copy.id
                    entry["chat_id"] = src_chat.id
                    entry["msg_id"] = bot_copy.id
                    entry["link"] = bot_copy.link
                except Exception as e:
                    LOGGER.error(f"Failed to copy from dump_chat: {e}")
                    continue
            elif chat_id == src_chat.id and self._user_session and not self._is_private:
                try:
                    bot_copy = await _call_with_flood_retry(
                        TgClient.bot.copy_message,
                        chat_id=src_chat.id,
                        from_chat_id=src_chat.id,
                        message_id=msg_id,
                    )
                    copy_from_chat = src_chat.id
                    copy_from_msg = bot_copy.id
                    entry["chat_id"] = src_chat.id
                    entry["msg_id"] = bot_copy.id
                    entry["link"] = bot_copy.link
                    try:
                        await TgClient.bot.delete_messages(
                            chat_id=chat_id, message_ids=msg_id
                        )
                    except Exception:
                        LOGGER.warning(
                            "Delete Permission not given. "
                            "Bot can't delete ghost mode original."
                        )
                except Exception as e:
                    LOGGER.error(
                        f"Failed to copy for ghost mode. "
                        f"Make sure bot has message delete permission: {e}"
                    )
                    continue
            if self._bot_pm:
                try:
                    await _call_with_flood_retry(
                        TgClient.bot.copy_message,
                        chat_id=self._listener.user_id,
                        from_chat_id=copy_from_chat,
                        message_id=copy_from_msg,
                        reply_to_message_id=(
                            self._listener.pm_msg.id if self._listener.pm_msg else None
                        ),
                    )
                except Exception as err:
                    if not self._listener.is_cancelled:
                        err_msg = str(err)
                        if "Can't copy" in err_msg:
                            LOGGER.warning(
                                f"BotPM copy skipped (restricted content): {err_msg}"
                            )
                        else:
                            LOGGER.error(f"Failed To Send in BotPM:\n{err_msg}")
            for dest_attr in ("cmd_up_dest", "leech_dest"):
                dest = getattr(self._listener, dest_attr, None)
                if not dest or dest == self._listener.up_dest:
                    continue
                if not isinstance(dest, int):
                    if "|" in str(dest):
                        dest, _ = str(dest).split("|", 1)
                    if str(dest).lstrip("-").isdigit():
                        dest = int(dest)
                try:
                    await _call_with_flood_retry(
                        TgClient.bot.copy_message,
                        chat_id=dest,
                        from_chat_id=copy_from_chat,
                        message_id=copy_from_msg,
                    )
                except Exception as e:
                    if not self._listener.is_cancelled:
                        LOGGER.error(f"Failed to forward to {dest_attr}: {e}")

    async def _upload_file_task(self, file_, f_path, dirpath, user_session, seq_idx):
        up_path = None
        try:
            up_path, cap_mono = await self._prepare_file(file_, dirpath)
            sent = await self._upload_file(
                cap_mono, up_path, file_, seq_idx, user_session=user_session
            )
            if sent and not self._is_corrupted:
                if self._listener.is_super_chat or self._listener.up_dest:
                    if not self._is_private:
                        entry = self._upload_seq[seq_idx]
                        if entry["msg_id"] == sent.id:
                            self._msgs_dict[sent.link] = file_
            return sent
        except StopTransmission:
            return None
        except Exception as err:
            LOGGER.error(f"{err}. Path: {f_path}", exc_info=True)
            self._error = str(err)
            self._corrupted += 1
            return None
        finally:
            path_to_clean = up_path or f_path
            if not self._listener.is_cancelled and await aiopath.exists(path_to_clean):
                await remove(path_to_clean)

    async def upload(self):
        await self._user_settings()
        res = await self._msg_to_reply()
        if not res:
            return
        upload_tasks = []
        seq_idx = 0
        for dirpath, _, files in natsorted(await sync_to_async(walk, self._path)):
            if dirpath.strip().endswith("/yt-dlp-thumb"):
                continue
            if dirpath.strip().endswith("_mltbss"):
                await self._send_screenshots(dirpath, files)
                await rmtree(dirpath, ignore_errors=True)
                continue
            for file_ in natsorted(files):
                self._error = ""
                f_path = ospath.join(dirpath, file_)
                if not await aiopath.exists(f_path):
                    LOGGER.error(f"{f_path} not exists! Continue uploading!")
                    continue
                try:
                    f_size = await aiopath.getsize(f_path)
                    self._total_files += 1
                    if f_size == 0:
                        LOGGER.warning(f"{f_path} size is zero, skipping")
                        self._corrupted += 1
                        if not self._listener.is_cancelled:
                            await remove(f_path)
                        continue
                    if self._listener.is_cancelled:
                        return
                    if self._last_msg_in_group:
                        group_lists = [
                            x for v in self._media_dict.values() for x in v.keys()
                        ]
                        match = re_match(r".+(?=\.0*\d+$)|.+(?=\.part\d+\..+$)", f_path)
                        if not match or match and match.group(0) not in group_lists:
                            for key, value in list(self._media_dict.items()):
                                for subkey, msgs in list(value.items()):
                                    if len(msgs) > 1:
                                        await self._send_media_group(subkey, key, msgs)
                    if self._listener.transmission_mode == "both":
                        self._user_session = f_size > 2097152000
                    elif (
                        not self._user_session
                        and f_size > 2097152000
                        and TgClient.user is not None
                    ):
                        self._user_session = True
                    self._last_msg_in_group = False
                    self._upload_seq.append(None)
                    task = ensure_future(
                        self._upload_file_task(
                            file_, f_path, dirpath, self._user_session, seq_idx
                        )
                    )
                    upload_tasks.append(task)
                    seq_idx += 1
                    if self._listener.is_cancelled:
                        return
                except Exception as err:
                    LOGGER.error(f"{err}. Path: {f_path}", exc_info=True)
                    self._error = str(err)
                    self._corrupted += 1
                    if self._listener.is_cancelled:
                        return
        if upload_tasks:
            results = await gather(*upload_tasks, return_exceptions=True)
            for r in results:
                if isinstance(r, Exception):
                    LOGGER.error(f"Upload task error: {r}")
            await sleep(1)
        for key, value in list(self._media_dict.items()):
            for subkey, msgs in list(value.items()):
                if len(msgs) > 1:
                    try:
                        await self._send_media_group(subkey, key, msgs)
                    except Exception as e:
                        LOGGER.info(
                            f"While sending media group at the end of task. Error: {e}"
                        )
        if self._upload_seq:
            src_chat = self._listener.message.chat
            await self._sequence_copies(src_chat)
            self._msgs_dict = {
                e["link"]: e["file_"] for e in self._upload_seq if e is not None
            }
        if self._listener.is_cancelled:
            return
        if self._total_files == 0:
            await self._listener.on_upload_error(
                "No files to upload. In case you have filled EXCLUDED_EXTENSIONS, then check if all files have those extensions or not."
            )
            return
        if self._total_files <= self._corrupted:
            await self._listener.on_upload_error(
                f"Files Corrupted or unable to upload. {self._error or 'Check logs!'}"
            )
            return
        LOGGER.info(f"Leech Completed: {self._listener.name}")
        await self._listener.on_upload_complete(
            None, self._msgs_dict, self._total_files, self._corrupted
        )
        return

    async def _upload_file(
        self, cap_mono, o_path, file_, seq_idx, force_document=False, user_session=False
    ):
        if self._sent_msg is None:
            LOGGER.error("Cannot upload: _sent_msg is None")
            await self._listener.on_upload_error(
                "Upload failed: Message not initialized"
            )
            return

        if not hasattr(self._sent_msg, "chat") or self._sent_msg.chat is None:
            LOGGER.error("Cannot upload: _sent_msg.chat is None")
            await self._listener.on_upload_error(
                "Upload failed: Invalid message object"
            )
            return

        if (
            self._thumb is not None
            and not await aiopath.exists(self._thumb)
            and self._thumb != "none"
        ):
            self._thumb = None
        self._is_corrupted = False
        try:
            if self._hu is None:
                self._hu = HypertgUpload(self)

            sent_msg = await self._hu.upload(
                file_path=o_path,
                cap_mono=cap_mono,
                reply_target=self._sent_msg,
                reply_to_message_id=self._sent_msg.id,
                force_document=force_document,
                user_session=user_session,
                user_thumb=self._thumb,
            )

            if self._listener.is_cancelled:
                return

            self._sent_msg = sent_msg

            self._upload_seq[seq_idx] = {
                "chat_id": sent_msg.chat.id,
                "msg_id": sent_msg.id,
                "link": sent_msg.link,
                "file_": file_,
            }
            self._msg_to_seq[(sent_msg.chat.id, sent_msg.id)] = seq_idx

            if (
                not self._listener.is_cancelled
                and self._media_group
                and (sent_msg.video or sent_msg.document)
            ):
                key = "documents" if sent_msg.document else "videos"
                if match := re_match(r".+(?=\.0*\d+$)|.+(?=\.part\d+\..+$)", o_path):
                    pname = match.group(0)
                    if pname in self._media_dict[key].keys():
                        self._media_dict[key][pname].append(
                            [sent_msg.chat.id, sent_msg.id]
                        )
                    else:
                        self._media_dict[key][pname] = [[sent_msg.chat.id, sent_msg.id]]
                    msgs = self._media_dict[key][pname]
                    if len(msgs) == 10:
                        await self._send_media_group(pname, key, msgs)
                    else:
                        self._last_msg_in_group = True

            return sent_msg
        except StopTransmission:
            raise
        except Exception as err:
            err_type = "RPCError: " if isinstance(err, RPCError) else ""
            LOGGER.error(f"{err_type}{err}. Path: {o_path}", exc_info=True)
            raise err

    @property
    def speed(self):
        try:
            return self._processed_bytes / (time() - self._start_time)
        except ZeroDivisionError:
            return 0

    @property
    def processed_bytes(self):
        return self._processed_bytes

    async def cancel_task(self):
        self._listener.is_cancelled = True
        LOGGER.info(f"Cancelling Upload: {self._listener.name}")
        await self._listener.on_upload_error("your upload has been stopped!")
