from asyncio import Lock, sleep
from time import time
from secrets import token_hex
from pyrogram.errors import FloodWait, PeerIdInvalid, ChannelInvalid
from pyrogram.enums import MessageMediaType

from bot.helper.ext_utils.hyperdl_utils import HyperTGDownload

try:
    from pyrogram.errors import FloodPremiumWait
except ImportError:
    FloodPremiumWait = FloodWait

from .... import (
    LOGGER,
    task_dict,
    task_dict_lock,
)
from ....core.tg_client import TgClient
from ....core.config_manager import Config
from ...ext_utils.task_manager import check_running_tasks, stop_duplicate_check
from ...mirror_leech_utils.status_utils.queue_status import QueueStatus
from ...mirror_leech_utils.status_utils.telegram_status import TelegramStatus
from ...telegram_helper.message_utils import send_status_message

global_lock = Lock()
GLOBAL_GID = dict()

# Helper function to create downloader with delete option
def create_telegram_downloader(listener, delete_after_download=False):
    """
    Factory function to create TelegramDownloadHelper with delete option
    
    Args:
        listener: The download listener
        delete_after_download (bool): Whether to delete source message after successful download
    
    Returns:
        TelegramDownloadHelper: Configured download helper
    """
    return TelegramDownloadHelper(listener, delete_after_download)


class TelegramDownloadHelper:
    def __init__(self, listener, delete_after_download=False):
        self._processed_bytes = 0
        self._start_time = 1
        self._listener = listener
        self._id = ""
        self.session = ""
        self._hyper_dl = len(TgClient.helper_bots) != 0 and Config.LEECH_DUMP_CHAT
        self._delete_after_download = delete_after_download
        self._source_message = None

    @property
    def speed(self):
        return self._processed_bytes / (time() - self._start_time)

    @property
    def processed_bytes(self):
        return self._processed_bytes

    def _is_downloadable_media(self, message):
        """Check if message contains downloadable media"""
        if not message.media:
            return False
        
        # List of downloadable media types
        downloadable_types = [
            MessageMediaType.DOCUMENT,
            MessageMediaType.VIDEO,
            MessageMediaType.AUDIO,
            MessageMediaType.VOICE,
            MessageMediaType.VIDEO_NOTE,
            MessageMediaType.ANIMATION,
            MessageMediaType.PHOTO,
            MessageMediaType.STICKER
        ]
        
        return message.media in downloadable_types

    async def _can_delete_message(self, message):
        """Check if we have permission to delete the message"""
        try:
            # Check if message is from a private chat (we can always delete our own messages there)
            if message.chat.type in ['private', 'bot']:
                return True
                
            # For groups and channels, check if we're admin
            if self.session == "user":
                try:
                    chat_member = await TgClient.user.get_chat_member(
                        chat_id=message.chat.id,
                        user_id="me"
                    )
                    return chat_member.status in ['administrator', 'creator'] and chat_member.privileges.can_delete_messages
                except:
                    pass
            
            # Check bot permissions
            try:
                chat_member = await TgClient.bot.get_chat_member(
                    chat_id=message.chat.id,
                    user_id="me"
                )
                return chat_member.status in ['administrator', 'creator'] and chat_member.privileges.can_delete_messages
            except:
                pass
                
            return False
        except Exception as e:
            LOGGER.warning(f"Error checking delete permissions: {e}")
            return False

    async def _on_download_start(self, file_id, gid, from_queue):
        async with global_lock:
            GLOBAL_GID[file_id] = gid
        self._id = file_id
        async with task_dict_lock:
            task_dict[self._listener.mid] = TelegramStatus(
                self._listener, self, gid, "dl", self._hyper_dl
            )
        if not from_queue:
            await self._listener.on_download_start()
            if self._listener.multi <= 1:
                await send_status_message(self._listener.message)
            LOGGER.info(f"Download from Telegram: {self._listener.name}")
        else:
            LOGGER.info(f"Start Queued Download from Telegram: {self._listener.name}")

    async def _on_download_progress(self, current, _):
        if self._listener.is_cancelled:
            if self.session == "user":
                TgClient.user.stop_transmission()
            elif self.session == "hbots":
                for hbot in TgClient.helper_bots.values():
                    hbot.stop_transmission()
            else:
                TgClient.bot.stop_transmission()
        self._processed_bytes = current

    async def _on_download_error(self, error):
        async with global_lock:
            if self._id in GLOBAL_GID:
                GLOBAL_GID.pop(self._id)
        await self._listener.on_download_error(error)

    async def _on_download_complete(self):
        await self._listener.on_download_complete()
        
        # Delete source message if requested
        if self._delete_after_download and self._source_message:
            try:
                await self._delete_source_message()
            except Exception as e:
                LOGGER.warning(f"Failed to delete source message after download: {e}")
        
        async with global_lock:
            GLOBAL_GID.pop(self._id)
        return

    async def _delete_source_message(self):
        """Delete the source message after successful download"""
        if not self._source_message:
            LOGGER.warning("No source message to delete")
            return
            
        # Check permissions first
        if not await self._can_delete_message(self._source_message):
            LOGGER.warning(f"No permission to delete message {self._source_message.id} in chat {self._source_message.chat.id}")
            return
            
        try:
            # Check if we have permission to delete
            if self.session == "user":
                # Try with user session first
                try:
                    await TgClient.user.delete_messages(
                        chat_id=self._source_message.chat.id,
                        message_ids=self._source_message.id
                    )
                    LOGGER.info(f"Successfully deleted source message {self._source_message.id} using user session")
                except Exception as user_error:
                    LOGGER.warning(f"User session delete failed: {user_error}, trying bot session")
                    # Fallback to bot session
                    await TgClient.bot.delete_messages(
                        chat_id=self._source_message.chat.id,
                        message_ids=self._source_message.id
                    )
                    LOGGER.info(f"Successfully deleted source message {self._source_message.id} using bot session")
            else:
                # Use bot session
                await TgClient.bot.delete_messages(
                    chat_id=self._source_message.chat.id,
                    message_ids=self._source_message.id
                )
                LOGGER.info(f"Successfully deleted source message {self._source_message.id} using bot session")
                
        except Exception as e:
            error_msg = f"Failed to delete source message {self._source_message.id}: {e}"
            LOGGER.error(error_msg)
            # Don't fail the entire download process just because deletion failed
            # Just log the error and continue
            raise Exception(error_msg)

    async def _download(self, message, path):
        try:
            # Pre-download validation
            if not self._is_downloadable_media(message):
                await self._on_download_error("Message doesn't contain downloadable media")
                return
                
            # TODO : Add support for user session ( Huh ??)
            if self._hyper_dl:
                try:
                    download = await HyperTGDownload().download_media(
                        message,
                        file_name=path,
                        progress=self._on_download_progress,
                        dump_chat=Config.LEECH_DUMP_CHAT,
                    )
                except Exception as hyper_error:
                    LOGGER.warning(f"HyperTGDownload failed: {hyper_error}")
                    if getattr(Config, "USER_TRANSMISSION", False):
                        try:
                            user_message = await TgClient.user.get_messages(
                                chat_id=message.chat.id, message_ids=message.id
                            )
                            if not self._is_downloadable_media(user_message):
                                await self._on_download_error("User message doesn't contain downloadable media")
                                return
                            download = await user_message.download(
                                file_name=path, progress=self._on_download_progress
                            )
                        except Exception as user_error:
                            LOGGER.warning(f"User download failed: {user_error}")
                            download = await message.download(
                                file_name=path, progress=self._on_download_progress
                            )
                    else:
                        download = await message.download(
                            file_name=path, progress=self._on_download_progress
                        )
            else:
                download = await message.download(
                    file_name=path, progress=self._on_download_progress
                )
            if self._listener.is_cancelled:
                return
        except (FloodWait, FloodPremiumWait) as f:
            LOGGER.warning(str(f))
            await sleep(f.value)
            await self._download(message, path)
            return
        except ValueError as ve:
            if "doesn't contain any downloadable media" in str(ve):
                LOGGER.error(f"No downloadable media in message: {self._listener.name}")
                await self._on_download_error(f"Message doesn't contain downloadable media: {self._listener.name}")
            else:
                LOGGER.error(f"Download error: {str(ve)}", exc_info=True)
                await self._on_download_error(f"Download failed: {str(ve)}")
            return
        except Exception as e:
            LOGGER.error(str(e), exc_info=True)
            await self._on_download_error(str(e))
            return
        if download is not None:
            await self._on_download_complete()
        elif not self._listener.is_cancelled:
            await self._on_download_error("Internal error occurred")
        return

    async def add_download(self, message, path, session, delete_after_download=False):
        self.session = session
        self._delete_after_download = delete_after_download
        self._source_message = message  # Store reference for potential deletion
        
        if not self.session:
            if self._hyper_dl:
                self.session == "hbots"
            elif self._listener.user_transmission and self._listener.is_super_chat:
                self.session = "user"
                try:
                    message = await TgClient.user.get_messages(
                        chat_id=message.chat.id, message_ids=message.id
                    )
                except (PeerIdInvalid, ChannelInvalid):
                    LOGGER.warning(
                        "User session is not in this chat!, Downloading with bot session"
                    )
                    self.session = "bot"
            else:
                self.session = "bot"
        
        # Enhanced media validation
        if not self._is_downloadable_media(message):
            error_msg = (
                f"No downloadable media found in message for: {self._listener.name}. "
                f"Message type: {message.media if message.media else 'None'}. "
                f"Use SuperGroup in case you are trying to download with User session!"
            )
            LOGGER.error(error_msg)
            await self._on_download_error(error_msg)
            return
            
        media = getattr(message, message.media.value) if message.media else None

        if media is not None:
            # Additional validation for media object
            if not hasattr(media, 'file_unique_id') or not hasattr(media, 'file_size'):
                await self._on_download_error(f"Invalid media object for: {self._listener.name}")
                return
                
            async with global_lock:
                download = media.file_unique_id not in GLOBAL_GID

            if download:
                if not self._listener.name:
                    if hasattr(media, "file_name") and media.file_name:
                        if "/" in media.file_name:
                            self._listener.name = media.file_name.rsplit("/", 1)[-1]
                            path = path + self._listener.name
                        else:
                            self._listener.name = media.file_name
                    else:
                        self._listener.name = "None"
                else:
                    path = path + self._listener.name
                self._listener.size = media.file_size
                gid = token_hex(5)

                msg, button = await stop_duplicate_check(self._listener)
                if msg:
                    await self._listener.on_download_error(msg, button)
                    return

                add_to_queue, event = await check_running_tasks(self._listener)
                if add_to_queue:
                    LOGGER.info(f"Added to Queue/Download: {self._listener.name}")
                    async with task_dict_lock:
                        task_dict[self._listener.mid] = QueueStatus(
                            self._listener, gid, "dl"
                        )
                    await self._listener.on_download_start()
                    if self._listener.multi <= 1:
                        await send_status_message(self._listener.message)
                    await event.wait()
                    if self.session == "bot":
                        message = await self._listener.client.get_messages(
                            chat_id=message.chat.id, message_ids=message.id
                        )
                    else:
                        try:
                            message = await TgClient.user.get_messages(
                                chat_id=message.chat.id, message_ids=message.id
                            )
                        except (PeerIdInvalid, ChannelInvalid):
                            message = await self._listener.client.get_messages(
                                chat_id=message.chat.id, message_ids=message.id
                            )
                    if self._listener.is_cancelled:
                        async with global_lock:
                            if self._id in GLOBAL_GID:
                                GLOBAL_GID.pop(self._id)
                        return
                        
                    # Update source message reference after getting from queue
                    self._source_message = message if self._delete_after_download else None
                        
                    # Re-validate message after queue wait
                    if not self._is_downloadable_media(message):
                        await self._on_download_error(f"Media no longer available for: {self._listener.name}")
                        return
                        
                self._start_time = time()
                await self._on_download_start(media.file_unique_id, gid, add_to_queue)
                await self._download(message, path)
            else:
                await self._on_download_error("File already being downloaded!")
        else:
            await self._on_download_error(
                "No document in the replied message! Use SuperGroup incase you are trying to download with User session!"
            )

    async def cancel_task(self):
        self._listener.is_cancelled = True
        LOGGER.info(
            f"Cancelling download on user request: name: {self._listener.name} id: {self._id}"
        )
        await self._on_download_error("Stopped by user!")