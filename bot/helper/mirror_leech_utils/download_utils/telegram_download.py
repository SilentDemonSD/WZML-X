from asyncio import Lock, sleep
from time import time
from secrets import token_hex
import json
import pickle
from pathlib import Path
from pyrogram.errors import FloodWait, PeerIdInvalid, ChannelInvalid, MessageIdInvalid
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

# Persistent storage for message data
MESSAGE_CACHE_DIR = Path("./message_cache")
MESSAGE_CACHE_DIR.mkdir(exist_ok=True)


class MessageCache:
    """Handles caching of message data for persistent downloads"""
    
    @staticmethod
    def _get_cache_path(file_unique_id):
        return MESSAGE_CACHE_DIR / f"{file_unique_id}.pkl"
    
    @staticmethod
    def save_message_data(message):
        """Save essential message data for later retrieval"""
        try:
            if not message.media:
                return None
                
            media = getattr(message, message.media.value)
            cache_data = {
                'chat_id': message.chat.id,
                'message_id': message.id,
                'file_unique_id': media.file_unique_id,
                'file_id': media.file_id,
                'file_size': media.file_size,
                'file_name': getattr(media, 'file_name', None),
                'mime_type': getattr(media, 'mime_type', None),
                'media_type': message.media.value,
                'date': message.date.timestamp() if message.date else None,
                'cached_at': time(),
                # Store the complete media object for reconstruction
                'media_data': {
                    'file_id': media.file_id,
                    'file_unique_id': media.file_unique_id,
                    'file_size': media.file_size,
                    'file_name': getattr(media, 'file_name', None),
                    'mime_type': getattr(media, 'mime_type', None),
                }
            }
            
            cache_path = MessageCache._get_cache_path(media.file_unique_id)
            with open(cache_path, 'wb') as f:
                pickle.dump(cache_data, f)
            
            LOGGER.info(f"Cached message data for: {media.file_unique_id}")
            return cache_data
            
        except Exception as e:
            LOGGER.error(f"Failed to cache message data: {str(e)}")
            return None
    
    @staticmethod
    def load_message_data(file_unique_id):
        """Load cached message data"""
        try:
            cache_path = MessageCache._get_cache_path(file_unique_id)
            if cache_path.exists():
                with open(cache_path, 'rb') as f:
                    return pickle.load(f)
        except Exception as e:
            LOGGER.error(f"Failed to load cached message data: {str(e)}")
        return None
    
    @staticmethod
    def cleanup_old_cache(max_age_days=7):
        """Clean up old cached files"""
        try:
            max_age = max_age_days * 24 * 60 * 60  # Convert to seconds
            current_time = time()
            
            for cache_file in MESSAGE_CACHE_DIR.glob("*.pkl"):
                try:
                    with open(cache_file, 'rb') as f:
                        cache_data = pickle.load(f)
                    
                    if current_time - cache_data.get('cached_at', 0) > max_age:
                        cache_file.unlink()
                        LOGGER.info(f"Cleaned up old cache file: {cache_file.name}")
                        
                except Exception as e:
                    LOGGER.error(f"Error cleaning cache file {cache_file}: {str(e)}")
                    
        except Exception as e:
            LOGGER.error(f"Failed to cleanup cache: {str(e)}")


class TelegramDownloadHelper:
    def __init__(self, listener):
        self._processed_bytes = 0
        self._start_time = 1
        self._listener = listener
        self._id = ""
        self.session = ""
        self._hyper_dl = len(TgClient.helper_bots) != 0 and Config.LEECH_DUMP_CHAT
        self._cached_data = None

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

    async def _get_message_by_file_id(self, file_id, chat_id=None, message_id=None):
        """Try to retrieve message using file_id or cached data"""
        try:
            # First try to get the original message if we have the details
            if chat_id and message_id:
                try:
                    if self.session == "user":
                        message = await TgClient.user.get_messages(chat_id, message_id)
                    else:
                        message = await TgClient.bot.get_messages(chat_id, message_id)
                    
                    if message and self._is_downloadable_media(message):
                        return message
                except (MessageIdInvalid, Exception) as e:
                    LOGGER.warning(f"Original message not found: {str(e)}")
            
            # If original message is not available, try to find it in recent messages
            # This is a fallback method - search recent messages for the same file
            if chat_id:
                try:
                    client = TgClient.user if self.session == "user" else TgClient.bot
                    async for message in client.get_chat_history(chat_id, limit=100):
                        if (message.media and 
                            hasattr(getattr(message, message.media.value, None), 'file_id') and
                            getattr(message, message.media.value).file_id == file_id):
                            LOGGER.info(f"Found message with same file_id in recent history")
                            return message
                except Exception as e:
                    LOGGER.warning(f"Failed to search chat history: {str(e)}")
            
            return None
            
        except Exception as e:
            LOGGER.error(f"Failed to retrieve message: {str(e)}")
            return None

    async def _download_from_cache(self, cached_data, path):
        """Attempt to download using cached message data"""
        try:
            LOGGER.info(f"Attempting download from cached data: {cached_data['file_name']}")
            
            # Try to reconstruct the message or find alternative download method
            message = await self._get_message_by_file_id(
                cached_data['media_data']['file_id'],
                cached_data['chat_id'],
                cached_data['message_id']
            )
            
            if message:
                LOGGER.info("Found message from cache data, proceeding with download")
                return await self._download_message(message, path)
            
            # If we can't find the message, try direct file_id download (if supported)
            try:
                # Some bots/clients support downloading directly by file_id
                # This is implementation-specific and may not work in all cases
                from pyrogram.types import Message
                from pyrogram.types.messages_and_media.document import Document
                
                # Create a mock message object with the cached data
                # Note: This is experimental and may not work in all cases
                LOGGER.warning("Attempting direct file_id download (experimental)")
                
                # This approach may not work as Pyrogram typically requires
                # a full message object for downloads
                return None
                
            except Exception as e:
                LOGGER.error(f"Direct file_id download failed: {str(e)}")
                return None
                
        except Exception as e:
            LOGGER.error(f"Failed to download from cache: {str(e)}")
            return None

    async def _download_message(self, message, path):
        """Download from a message object"""
        if self._hyper_dl:
            try:
                return await HyperTGDownload().download_media(
                    message,
                    file_name=path,
                    progress=self._on_download_progress,
                    dump_chat=Config.LEECH_DUMP_CHAT,
                )
            except Exception:
                if getattr(Config, "USER_TRANSMISSION", False):
                    try:
                        user_message = await TgClient.user.get_messages(
                            chat_id=message.chat.id, message_ids=message.id
                        )
                        return await user_message.download(
                            file_name=path, progress=self._on_download_progress
                        )
                    except Exception:
                        return await message.download(
                            file_name=path, progress=self._on_download_progress
                        )
                else:
                    return await message.download(
                        file_name=path, progress=self._on_download_progress
                    )
        else:
            return await message.download(
                file_name=path, progress=self._on_download_progress
            )

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
        async with global_lock:
            GLOBAL_GID.pop(self._id)
        return

    async def _download(self, message, path):
        try:
            # Pre-download validation
            if not self._is_downloadable_media(message):
                # Try to use cached data if original message doesn't have media
                if self._cached_data:
                    LOGGER.info("Original message unavailable, trying cached data")
                    download = await self._download_from_cache(self._cached_data, path)
                    if download is not None:
                        if not self._listener.is_cancelled:
                            await self._on_download_complete()
                        return
                
                await self._on_download_error("Message doesn't contain downloadable media and no valid cache found")
                return
            
            download = await self._download_message(message, path)
            
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
                
                # Try cached download as fallback
                if self._cached_data:
                    LOGGER.info("Attempting download from cached data due to media unavailability")
                    download = await self._download_from_cache(self._cached_data, path)
                    if download is not None:
                        if not self._listener.is_cancelled:
                            await self._on_download_complete()
                        return
                
                await self._on_download_error(f"Message doesn't contain downloadable media and cache unavailable: {self._listener.name}")
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

    async def add_download(self, message, path, session):
        self.session = session
        
        # Cache the message data immediately when download is requested
        self._cached_data = MessageCache.save_message_data(message)
        
        if not self.session:
            if self._hyper_dl:
                self.session = "hbots"
            elif self._listener.user_transmission and self._listener.is_super_chat:
                self.session = "user"
                try:
                    message = await TgClient.user.get_messages(
                        chat_id=message.chat.id, message_ids=message.id
                    )
                    # Update cache with user session message if different
                    if message and self._is_downloadable_media(message):
                        self._cached_data = MessageCache.save_message_data(message)
                except (PeerIdInvalid, ChannelInvalid):
                    LOGGER.warning(
                        "User session is not in this chat!, Downloading with bot session"
                    )
                    self.session = "bot"
            else:
                self.session = "bot"
        
        # Enhanced media validation with cache fallback
        if not self._is_downloadable_media(message):
            if self._cached_data:
                LOGGER.info(f"Message media unavailable but cache exists for: {self._listener.name}")
                # We'll proceed with cached data
            else:
                error_msg = (
                    f"No downloadable media found and no cache available for: {self._listener.name}. "
                    f"Message type: {message.media if message.media else 'None'}. "
                    f"Use SuperGroup in case you are trying to download with User session!"
                )
                LOGGER.error(error_msg)
                await self._on_download_error(error_msg)
                return
        
        # Use cached data if original media is unavailable
        if self._cached_data and not self._is_downloadable_media(message):
            media_info = self._cached_data['media_data']
            file_unique_id = media_info['file_unique_id']
            file_size = media_info['file_size']
            file_name = media_info['file_name']
        else:
            media = getattr(message, message.media.value) if message.media else None
            if media is None:
                await self._on_download_error(f"No media object available for: {self._listener.name}")
                return
            
            file_unique_id = media.file_unique_id
            file_size = media.file_size
            file_name = getattr(media, 'file_name', None)

        async with global_lock:
            download = file_unique_id not in GLOBAL_GID

        if download:
            if not self._listener.name:
                if file_name:
                    if "/" in file_name:
                        self._listener.name = file_name.rsplit("/", 1)[-1]
                        path = path + self._listener.name
                    else:
                        self._listener.name = file_name
                else:
                    self._listener.name = "None"
            else:
                path = path + self._listener.name
                
            self._listener.size = file_size
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
                
                # Try to refresh message after queue wait
                try:
                    if self.session == "bot":
                        fresh_message = await self._listener.client.get_messages(
                            chat_id=message.chat.id, message_ids=message.id
                        )
                    else:
                        try:
                            fresh_message = await TgClient.user.get_messages(
                                chat_id=message.chat.id, message_ids=message.id
                            )
                        except (PeerIdInvalid, ChannelInvalid):
                            fresh_message = await self._listener.client.get_messages(
                                chat_id=message.chat.id, message_ids=message.id
                            )
                    
                    # Use fresh message if available, otherwise keep the original
                    if fresh_message and self._is_downloadable_media(fresh_message):
                        message = fresh_message
                    else:
                        LOGGER.warning("Fresh message unavailable, using cached data")
                        
                except Exception as e:
                    LOGGER.warning(f"Failed to refresh message: {str(e)}, using cached data")
                
                if self._listener.is_cancelled:
                    async with global_lock:
                        if self._id in GLOBAL_GID:
                            GLOBAL_GID.pop(self._id)
                    return
                        
            self._start_time = time()
            await self._on_download_start(file_unique_id, gid, add_to_queue)
            await self._download(message, path)
        else:
            await self._on_download_error("File already being downloaded!")

    async def cancel_task(self):
        self._listener.is_cancelled = True
        LOGGER.info(
            f"Cancelling download on user request: name: {self._listener.name} id: {self._id}"
        )
        await self._on_download_error("Stopped by user!")

# Utility function to clean up old cache periodically
async def cleanup_message_cache():
    """Clean up old cached message data"""
    MessageCache.cleanup_old_cache(max_age_days=7)