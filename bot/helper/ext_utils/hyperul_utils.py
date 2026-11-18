from asyncio import sleep

from PIL import Image
from pyrogram import StopTransmission
from pyrogram.errors import FloodWait, PhotoInvalidDimensions
from pyrogram.types import ReplyParameters

try:
    from pyrogram.errors import FloodPremiumWait
except ImportError:
    FloodPremiumWait = FloodWait

from os import path as ospath
from aiofiles.os import path as aiopath, remove

from ... import LOGGER
from ...core.config_manager import Config
from ...core.tg_client import TgClient
from ..telegram_helper.tg_transfer import HypertgTransfer
from ..ext_utils.media_utils import (
    get_audio_thumbnail,
    get_document_type,
    get_media_info,
    get_multiple_frames_thumbnail,
    get_video_thumbnail,
)
from ..ext_utils.bot_utils import parse_dest
from ..ext_utils.tmdb_utils import get_auto_thumbnail


def _upload_log_context(
    listener, chat_id, thread_id, client, transport, file_path, client_slot=None
):
    """Summarize an upload without logging credentials, URLs, or captions."""
    message = getattr(listener, "message", None)
    source_chat = getattr(message, "chat", None)
    uploader = getattr(client, "me", None)
    source_id = getattr(source_chat, "id", None)
    destination_name = ""
    if chat_id == getattr(listener, "up_dest", None):
        destination_name = getattr(listener, "up_dest_name", "")
    elif chat_id == source_id:
        destination_name = (
            getattr(source_chat, "title", None)
            or getattr(source_chat, "username", None)
        )
    # Keep user-controlled Telegram titles on one log line.
    destination_name = str(destination_name or "").replace("\r", " ").replace("\n", " ")[:80]
    filename = ospath.basename(str(file_path or "")).replace("\r", " ").replace("\n", " ")
    username = getattr(uploader, "username", None)
    return (
        f"task={getattr(listener, 'mid', None)} "
        f"request_chat={source_id} request_msg={getattr(message, 'id', None)} "
        f"dest_chat={chat_id} dest_name={destination_name!r} "
        f"thread={thread_id} transport={transport} client_slot={client_slot} "
        f"uploader_id={getattr(uploader, 'id', None)} "
        f"uploader_username={username!r} file={filename!r}"
    )


class HypertgUpload(HypertgTransfer):
    def __init__(self, obj):
        super().__init__(obj)
        self._file_progress = {}

    async def _progress(self, current, total, file_path):
        if self._listener.is_cancelled:
            raise StopTransmission()
        self._file_progress[file_path] = current
        self._obj._processed_bytes = sum(self._file_progress.values())

    async def upload(
        self,
        file_path,
        cap_mono,
        reply_target,
        reply_msg_id,
        force_document=False,
        user_thumb=None,
        user_session=False,
    ):
        self._cancel.clear()
        up_file = ospath.basename(file_path)

        is_video, is_audio, is_image = await get_document_type(file_path)

        thumb = user_thumb or None

        if not is_image and thumb is None:
            file_name = ospath.splitext(up_file)[0]
            base_path = getattr(self._obj, "_path", "")
            thumb_path = f"{base_path}/yt-dlp-thumb/{file_name}.jpg"
            if await aiopath.isfile(thumb_path):
                thumb = thumb_path
            elif await aiopath.isfile(thumb_path.replace("/yt-dlp-thumb", "")):
                thumb = thumb_path.replace("/yt-dlp-thumb", "")
            elif is_audio and not is_video:
                thumb = await get_audio_thumbnail(file_path)

        if not is_image and thumb is None and user_thumb is None:
            user_dict = self._listener.user_dict
            if user_dict.get("AUTO_THUMBNAIL") or (
                "AUTO_THUMBNAIL" not in user_dict and Config.AUTO_THUMBNAIL
            ):
                try:
                    thumb = await get_auto_thumbnail(
                        up_file or self._listener.name,
                        force_document or self._listener.as_doc,
                    )
                except Exception as e:
                    LOGGER.warning(f"Auto thumbnail failed: {e}")

        duration = 0
        width = 480
        height = 320
        artist = ""
        title = ""

        if (
            force_document
            or self._listener.as_doc
            or (not is_video and not is_audio and not is_image)
        ):
            key = "documents"
            if is_video and thumb is None:
                thumb = await get_video_thumbnail(file_path, None)
        elif is_video:
            key = "videos"
            duration = (await get_media_info(file_path))[0]
            if thumb is None and self._listener.thumbnail_layout:
                thumb = await get_multiple_frames_thumbnail(
                    file_path,
                    self._listener.thumbnail_layout,
                    self._listener.screen_shots,
                )
            if thumb is None:
                thumb = await get_video_thumbnail(file_path, duration)
            if thumb is not None and thumb != "none":
                with Image.open(thumb) as img:
                    width, height = img.size
        elif is_audio:
            key = "audios"
            duration, artist, title = await get_media_info(file_path)
        else:
            key = "photos"

        if thumb == "none":
            thumb = None

        up_size = ospath.getsize(file_path)
        hyper_user_only = False
        if up_size > 2097152000 and any(k < 0 for k in self.clients):
            if TgClient.user:
                use_hyper = False
                user_session = True
            else:
                use_hyper = True
                hyper_user_only = True
                user_session = False
        else:
            use_hyper = Config.USE_HYPER and self.clients and up_size > 10 * 1024 * 1024
        if self._listener.up_dest:
            upload_chat_id = self._listener.up_dest
            thread_id = self._listener.chat_thread_id
        elif Config.LEECH_LOG_CHAT:
            upload_chat_id, thread_id = parse_dest(Config.LEECH_LOG_CHAT)
        else:
            upload_chat_id, thread_id = reply_target.chat.id, None
        try:
            if use_hyper:
                hyper_rply = (
                    reply_msg_id if upload_chat_id == reply_target.chat.id else None
                )
                sent = await self._hyper_send(
                    file_path,
                    key,
                    thumb,
                    cap_mono,
                    upload_chat_id,
                    hyper_rply,
                    thread_id,
                    duration=duration,
                    width=width,
                    height=height,
                    artist=artist,
                    title=title,
                    user_only=hyper_user_only,
                )
            else:
                direct_rply = (
                    reply_msg_id if upload_chat_id == reply_target.chat.id else None
                )
                sent = await self._direct_send(
                    file_path,
                    key,
                    thumb,
                    cap_mono,
                    upload_chat_id,
                    direct_rply,
                    thread_id,
                    duration=duration,
                    width=width,
                    height=height,
                    artist=artist,
                    title=title,
                    user_session=user_session,
                )

            LOGGER.info(f"HypertgUL uploaded {up_file}")
            return sent

        except StopTransmission:
            LOGGER.warning(f"HypertgUL cancelled {up_file}")
            raise
        except Exception as e:
            LOGGER.error(f"HypertgUL fail {up_file}: {type(e).__name__}: {e}")
            raise
        finally:
            if user_thumb is None and thumb is not None and await aiopath.exists(thumb):
                try:
                    await remove(thumb)
                except Exception:
                    pass

    async def _send_with_retry(self, send_func, **kwargs):
        while True:
            try:
                return await send_func(**kwargs)
            except (FloodWait, FloodPremiumWait) as f:
                LOGGER.warning(
                    f"HypertgUL flood {f.value}s on {ospath.basename(kwargs['progress_args'][0])}"
                )
                await sleep(f.value + 1)

    async def _try_send(
        self, key, client, kwargs, transport="direct", client_slot=None
    ):
        context = _upload_log_context(
            self._listener,
            kwargs.get("chat_id"),
            kwargs.get("message_thread_id"),
            client,
            transport,
            kwargs.get("progress_args", (None,))[0],
            client_slot,
        )
        LOGGER.info("Telegram upload attempt %s media=%s", context, key)
        method = {
            "videos": "send_video",
            "audios": "send_audio",
            "photos": "send_photo",
        }.get(key, "send_document")
        send_func = getattr(client, method)
        try:
            try:
                sent = await self._send_with_retry(send_func, **kwargs)
            except PhotoInvalidDimensions:
                kwargs.pop("thumb", None)
                kwargs.pop("video_cover", None)
                sent = await self._send_with_retry(send_func, **kwargs)
            LOGGER.info("Telegram upload succeeded %s media=%s", context, key)
            return sent
        except Exception as e:
            LOGGER.error(
                "Telegram upload failed %s media=%s error_type=%s "
                "telegram_code=%s telegram_id=%s error=%s",
                context,
                key,
                type(e).__name__,
                getattr(e, "CODE", getattr(e, "code", None)),
                getattr(e, "ID", None),
                e,
            )
            raise

    async def _hyper_send(
        self,
        file_path,
        key,
        thumb,
        cap_mono,
        chat_id,
        reply_msg_id,
        thread_id=None,
        duration=0,
        width=0,
        height=0,
        artist="",
        title="",
        user_only=False,
    ):
        if user_only:
            candidates = {
                k: self.work_loads.get(k, 0) for k in self.clients if k < 0
            }
            if not candidates:
                idx = self._pick_client()
            else:
                idx = min(candidates, key=candidates.get)
        else:
            idx = self._pick_client()
        client = self.clients[idx]
        self.work_loads[idx] += 1

        try:
            kwargs = {
                "chat_id": chat_id,
                "disable_notification": True,
                "progress": self._progress,
                "progress_args": (file_path,),
            }
            if cap_mono:
                kwargs["caption"] = cap_mono
            if reply_msg_id:
                kwargs["reply_parameters"] = ReplyParameters(message_id=reply_msg_id)
            elif thread_id:
                kwargs["message_thread_id"] = thread_id

            if key == "videos":
                if duration:
                    kwargs["duration"] = duration
                if width:
                    kwargs["width"] = width
                if height:
                    kwargs["height"] = height
                if thumb:
                    kwargs["video_cover"] = thumb
                    kwargs["thumb"] = thumb
            elif key == "audios":
                if duration:
                    kwargs["duration"] = duration
                if artist:
                    kwargs["performer"] = artist
                if title:
                    kwargs["title"] = title
                if thumb:
                    kwargs["thumb"] = thumb
            elif key == "documents" and thumb:
                kwargs["thumb"] = thumb

            if key == "videos":
                kwargs["video"] = file_path
            elif key == "audios":
                kwargs["audio"] = file_path
            elif key == "photos":
                kwargs["photo"] = file_path
            else:
                kwargs["document"] = file_path

            sent = await self._try_send(
                key, client, kwargs, transport="hyper", client_slot=idx
            )
            return sent
        finally:
            self.work_loads[idx] -= 1

    async def _direct_send(
        self,
        file_path,
        key,
        thumb,
        cap_mono,
        chat_id,
        reply_msg_id,
        thread_id=None,
        duration=0,
        width=0,
        height=0,
        artist="",
        title="",
        user_session=False,
    ):
        client = (
            TgClient.user if user_session and TgClient.user else self._listener.client
        )
        kwargs = {
            "chat_id": chat_id,
            "disable_notification": True,
            "progress": self._progress,
            "progress_args": (file_path,),
        }
        if cap_mono:
            kwargs["caption"] = cap_mono
        if reply_msg_id:
            kwargs["reply_parameters"] = ReplyParameters(message_id=reply_msg_id)
        elif thread_id:
            kwargs["message_thread_id"] = thread_id

        if key == "videos":
            if thumb:
                kwargs["thumb"] = thumb
                kwargs["video_cover"] = thumb
            if duration:
                kwargs["duration"] = duration
            if width:
                kwargs["width"] = width
            if height:
                kwargs["height"] = height
        elif key == "audios":
            if thumb:
                kwargs["thumb"] = thumb
            if duration:
                kwargs["duration"] = duration
            if artist:
                kwargs["performer"] = artist
            if title:
                kwargs["title"] = title
        elif key == "documents" and thumb:
            kwargs["thumb"] = thumb

        if key == "videos":
            kwargs["video"] = file_path
        elif key == "audios":
            kwargs["audio"] = file_path
        elif key == "photos":
            kwargs["photo"] = file_path
        else:
            kwargs["document"] = file_path

        return await self._try_send(
            key,
            client,
            kwargs,
            transport="direct-user" if client is TgClient.user else "direct-bot",
        )

    async def cancel(self):
        await super().cancel()
