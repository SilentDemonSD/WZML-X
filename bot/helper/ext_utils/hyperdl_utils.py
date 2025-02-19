from asyncio import create_task, gather, sleep
from datetime import datetime
from math import ceil, floor
from mimetypes import MimeTypes
from os import path as ospath
from pathlib import Path
from re import sub
from shutil import move
from sys import argv

from aiofiles import open as aiopen
from aiofiles.os import makedirs, remove
from pyrogram import raw, utils
from pyrogram.errors import AuthBytesInvalid
from pyrogram.file_id import PHOTO_TYPES, FileId, FileType, ThumbnailSource
from pyrogram.session import Auth, Session
from pyrogram.session.internals import MsgId
from pyrogram.types import Message

from ... import LOGGER
from ...core.tg_client import TgClient


class HyperTGDownload:
    def __init__(self, part_count=None):
        self.clients = TgClient.helper_bots
        self.work_loads = TgClient.helper_loads
        self.message = None
        self.dump_chat = None
        self.download_dir = "downloads/"
        self.directory = None
        self.num_parts = part_count or max(6, len(self.clients))
        self.cache_file_ref = {}
        self._processed_bytes = 0
        self.file_size = 0
        self.file_name = ""
        create_task(self._clean_cache())

    @staticmethod
    async def get_media_type(message):
        media_types = (
            "audio",
            "document",
            "photo",
            "sticker",
            "animation",
            "video",
            "voice",
            "video_note",
            "new_chat_photo",
        )
        for attr in media_types:
            if media := getattr(message, attr, None):
                return media
        raise ValueError("This message doesn't contain any downloadable media")

    async def get_specific_file_ref(self, mid, client):
        try:
            media = await client.get_messages(self.dump_chat, mid)
        except Exception:
            LOGGER.error(
                f"Failed to get message {mid} from {self.dump_chat} with Client {client}"
            )
            raise ValueError(
                "Make sure Bot is Admin in the Chat and the Message is not Deleted"
            )
        return FileId.decode(getattr(await self.get_media_type(media), "file_id", ""))

    async def get_file_id(self, client, index) -> FileId:
        if index not in self.cache_file_ref:
            self.cache_file_ref[index] = await self.get_specific_file_ref(
                self.message.id, client
            )
        return self.cache_file_ref[index]

    async def _clean_cache(self):
        for _ in range(6):
            await sleep(30 * 60)
            self.cache_file_ref.clear()

    async def generate_media_session(self, client, file_id):
        media_session = client.media_sessions.get(file_id.dc_id, None)

        if media_session is None:
            if file_id.dc_id != await client.storage.dc_id():
                media_session = Session(
                    client,
                    file_id.dc_id,
                    await Auth(
                        client, file_id.dc_id, await client.storage.test_mode()
                    ).create(),
                    await client.storage.test_mode(),
                    is_media=True,
                )
                await media_session.start()

                for _ in range(6):
                    exported_auth = await client.invoke(
                        raw.functions.auth.ExportAuthorization(dc_id=file_id.dc_id)
                    )

                    try:
                        await media_session.invoke(
                            raw.functions.auth.ImportAuthorization(
                                id=exported_auth.id, bytes=exported_auth.bytes
                            )
                        )
                        break
                    except AuthBytesInvalid:
                        continue
                else:
                    await media_session.stop()
                    raise AuthBytesInvalid
            else:
                media_session = Session(
                    client,
                    file_id.dc_id,
                    await client.storage.auth_key(),
                    await client.storage.test_mode(),
                    is_media=True,
                )
                await media_session.start()
            client.media_sessions[file_id.dc_id] = media_session

        return media_session

    @staticmethod
    async def get_location(
        file_id: FileId,
    ):
        file_type = file_id.file_type

        if file_type == FileType.CHAT_PHOTO:
            if file_id.chat_id > 0:
                peer = raw.types.InputPeerUser(
                    user_id=file_id.chat_id, access_hash=file_id.chat_access_hash
                )
            else:
                peer = (
                    raw.types.InputPeerChat(chat_id=-file_id.chat_id)
                    if file_id.chat_access_hash == 0
                    else raw.types.InputPeerChannel(
                        channel_id=utils.get_channel_id(file_id.chat_id),
                        access_hash=file_id.chat_access_hash,
                    )
                )
            return raw.types.InputPeerPhotoFileLocation(
                peer=peer,
                volume_id=file_id.volume_id,
                local_id=file_id.local_id,
                big=file_id.thumbnail_source == ThumbnailSource.CHAT_PHOTO_BIG,
            )
        elif file_type == FileType.PHOTO:
            return raw.types.InputPhotoFileLocation(
                id=file_id.media_id,
                access_hash=file_id.access_hash,
                file_reference=file_id.file_reference,
                thumb_size=file_id.thumbnail_size,
            )
        else:
            return raw.types.InputDocumentFileLocation(
                id=file_id.media_id,
                access_hash=file_id.access_hash,
                file_reference=file_id.file_reference,
                thumb_size=file_id.thumbnail_size,
            )

    async def get_file(
        self,
        offset_bytes: int,
        first_part_cut: int,
        last_part_cut: int,
        part_count: int,
        chunk_size: int,
    ):
        index = min(self.work_loads, key=self.work_loads.get)
        client = self.clients[index]

        self.work_loads[index] += 1

        file_id = await self.get_file_id(client, index)

        media_session, location = await gather(
            self.generate_media_session(client, file_id), self.get_location(file_id)
        )

        current_part = 1

        try:
            r = await media_session.invoke(
                raw.functions.upload.GetFile(
                    location=location, offset=offset_bytes, limit=chunk_size
                ),
            )
            if isinstance(r, raw.types.upload.File):
                while True:
                    chunk = r.bytes

                    if not chunk:
                        break
                    elif part_count == 1:
                        yield chunk[first_part_cut:last_part_cut]
                    elif current_part == 1:
                        yield chunk[first_part_cut:]
                    elif current_part == part_count:
                        yield chunk[:last_part_cut]
                    else:
                        yield chunk

                    current_part += 1
                    offset_bytes += chunk_size
                    self._processed_bytes += chunk_size

                    if current_part > part_count:
                        break

                    r = await media_session.invoke(
                        raw.functions.upload.GetFile(
                            location=location, offset=offset_bytes, limit=chunk_size
                        ),
                    )
        except (TimeoutError, AttributeError):
            pass
        finally:
            self.work_loads[index] -= 1

    async def progress_callback(self, progress, progress_args):
        if progress:
            await sleep(2)
            while 1:
                try:
                    await progress(
                        min(self._processed_bytes, self.file_size)
                        if self.file_size != 0
                        else self._processed_bytes,
                        self.file_size,
                        *progress_args,
                    )
                    await sleep(0.5)
                except Exception as e:
                    LOGGER.error(str(e))

    async def single_part(self, start, end):
        chunk_size = 1024 * 1024
        until_bytes, from_bytes = min(end, self.file_size - 1), start

        offset = from_bytes - (from_bytes % chunk_size)
        first_part_cut = from_bytes - offset
        last_part_cut = until_bytes % chunk_size + 1

        part_count = ceil(until_bytes / chunk_size) - floor(offset / chunk_size)

        chunks = []
        async for chunk in self.get_file(
            offset, first_part_cut, last_part_cut, part_count, chunk_size
        ):
            chunks.append(chunk)
        return start, chunks

    async def handle_download(self, progress, progress_args):
        await makedirs(self.directory, exist_ok=True)
        temp_file_path = (
            ospath.abspath(
                sub("\\\\", "/", ospath.join(self.directory, self.file_name))
            )
            + ".temp"
        )

        part_size = self.file_size // self.num_parts
        ranges = [
            (i * part_size, (i + 1) * part_size - 1) for i in range(self.num_parts)
        ]

        ranges[-1] = (ranges[-1][0], self.file_size - 1)

        try:
            tasks = [create_task(self.single_part(start, end)) for start, end in ranges]

            prog = create_task(self.progress_callback(progress, progress_args))
            results = await gather(*tasks)

            results.sort(key=lambda x: x[0])

            async with aiopen(temp_file_path, "wb") as file:
                for _, result in results:
                    for chunk in result:
                        await file.write(chunk)
            if not prog.done():
                prog.cancel()
        except BaseException as e:
            await remove(temp_file_path)

            LOGGER.error(f"FASTDL: {e}")
            for task in tasks:
                if not task.done():
                    task.cancel()
            raise e
        else:
            file_path = ospath.splitext(temp_file_path)[0]
            move(temp_file_path, file_path)
            return file_path

    @staticmethod
    async def get_extension(file_type, mime_type):
        if file_type in PHOTO_TYPES:
            return ".jpg"
        guessed_extension = MimeTypes().guess_extension(mime_type)
        if file_type == FileType.VOICE:
            return guessed_extension or ".ogg"
        elif file_type in (FileType.VIDEO, FileType.ANIMATION, FileType.VIDEO_NOTE):
            return guessed_extension or ".mp4"
        elif file_type == FileType.DOCUMENT:
            return guessed_extension or ".zip"
        elif file_type == FileType.STICKER:
            return guessed_extension or ".webp"
        elif file_type == FileType.AUDIO:
            return guessed_extension or ".mp3"
        else:
            return ".unknown"

    async def download_media(
        self,
        message: Message,
        file_name="downloads/",
        progress=None,
        progress_args=(),
        dump_chat=None,
    ):
        if dump_chat:
            await TgClient.bot.copy_message(
                chat_id=dump_chat,
                from_chat_id=message.chat.id,
                message_id=message.id,
                disable_notification=True,
            )

        self.dump_chat =  dump_chat or message.chat.id
        self.message = message
        media = await self.get_media_type(self.message)

        file_id_str = media if isinstance(media, str) else media.file_id
        file_id_obj = FileId.decode(file_id_str)

        file_type = file_id_obj.file_type
        media_file_name = getattr(media, "file_name", "")
        self.file_size = getattr(media, "file_size", 0)
        mime_type = getattr(media, "mime_type", "image/jpeg")
        date = getattr(media, "date", None)

        self.directory, self.file_name = ospath.split(file_name)
        self.file_name = self.file_name or media_file_name or ""

        if not ospath.isabs(self.file_name):
            self.directory = Path(argv[0]).parent / (
                self.directory or self.download_dir
            )

        if not self.file_name:
            extension = await self.get_extension(file_type, mime_type)
            self.file_name = f"{FileType(file_id_obj.file_type).name.lower()}_{(date or datetime.now()).strftime('%Y-%m-%d_%H-%M-%S')}_{MsgId()}{extension}"

        return await self.handle_download(progress, progress_args)
