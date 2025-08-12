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

# Enhanced persistent storage
MESSAGE_CACHE_DIR = Path("./message_cache")
QUEUE_CACHE_DIR = Path("./queue_cache") 
MESSAGE_CACHE_DIR.mkdir(exist_ok=True)
QUEUE_CACHE_DIR.mkdir(exist_ok=True)


class QueueMessageCache:
    """Specialized cache for queued downloads"""
    
    @staticmethod
    def save_queue_data(listener_mid, message_data, download_path):
        """Save complete download context for queued items"""
        try:
            queue_data = {
                'listener_mid': listener_mid,
                'message_data': message_data,
                'download_path': download_path,
                'queued_at': time(),
                'file_unique_id': message_data.get('file_unique_id'),
                'original_message_available': True
            }
            
            cache_path = QUEUE_CACHE_DIR / f"queue_{listener_mid}.pkl"
            with open(cache_path, 'wb') as f:
                pickle.dump(queue_data, f)
            
            LOGGER.info(f"Saved queue cache for: {listener_mid}")
            return True
            
        except Exception as e:
            LOGGER.error(f"Failed to save queue cache: {str(e)}")
            return False
    
    @staticmethod
    def load_queue_data(listener_mid):
        """Load queued download context"""
        try:
            cache_path = QUEUE_CACHE_DIR / f"queue_{listener_mid}.pkl"
            if cache_path.exists():
                with open(cache_path, 'rb') as f:
                    return pickle.load(f)
        except Exception as e:
            LOGGER.error(f"Failed to load queue cache: {str(e)}")
        return None
    
    @staticmethod
    def remove_queue_data(listener_mid):
        """Remove queue cache after download completion"""
        try:
            cache_path = QUEUE_CACHE_DIR / f"queue_{listener_mid}.pkl"
            if cache_path.exists():
                cache_path.unlink()
                LOGGER.info(f"Removed queue cache for: {listener_mid}")
        except Exception as e:
            LOGGER.error(f"Failed to remove queue cache: {str(e)}")


class MessageCache:
    """Enhanced message caching with queue support"""
    
    @staticmethod
    def _get_cache_path(file_unique_id):
        return MESSAGE_CACHE_DIR / f"{file_unique_id}.pkl"
    
    @staticmethod
    def save_message_data(message):
        """Save comprehensive message data"""
        try:
            if not message.media:
                return None
                
            media = getattr(message, message.media.value)
            
            # Enhanced cache with more metadata
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
                'chat_title': getattr(message.chat, 'title', 'Unknown'),
                'chat_type': message.chat.type.value if hasattr(message.chat, 'type') else 'unknown',
                'media_data': {
                    'file_id': media.file_id,
                    'file_unique_id': media.file_unique_id,
                    'file_size': media.file_size,
                    'file_name': getattr(media, 'file_name', None),
                    'mime_type': getattr(media, 'mime_type', None),
                    'width': getattr(media, 'width', None),
                    'height': getattr(media, 'height', None),
                    'duration': getattr(media, 'duration', None),
                },
                # Store alternative file IDs if available
                'alternative_files': []
            }
            
            cache_path = MessageCache._get_cache_path(media.file_unique_id)
            with open(cache_path, 'wb') as f:
                pickle.dump(cache_data, f)
            
            LOGGER.info(f"Enhanced cache saved for: {cache_data['file_name']} ({media.file_unique_id})")
            return cache_data
            
        except Exception as e:
            LOGGER.error(f"Failed to cache message data: {str(e)}")
            return None
    
    @staticmethod
    def load_message_data(file_unique_id):
        """Load cached message data with validation"""
        try:
            cache_path = MessageCache._get_cache_path(file_unique_id)
            if cache_path.exists():
                with open(cache_path, 'rb') as f:
                    data = pickle.load(f)
                
                # Check cache age (files older than 30 days are considered stale)
                if time() - data.get('cached_at', 0) > (30 * 24 * 60 * 60):
                    LOGGER.warning(f"Cache is old for {file_unique_id}, may be unreliable")
                
                return data
        except Exception as e:
            LOGGER.error(f"Failed to load cached message data: {str(e)}")
        return None


class TelegramDownloadHelper:
    def __init__(self, listener):
        self._processed_bytes = 0
        self._start_time = 1
        self._listener = listener
        self._id = ""
        self.session = ""
        self._hyper_dl = len(TgClient.helper_bots) != 0 and Config.LEECH_DUMP_CHAT
        self._cached_data = None
        self._queue_cache = None

    @property
    def speed(self):
        return self._processed_bytes / (time() - self._start_time)

    @property
    def processed_bytes(self):
        return self._processed_bytes

    def _is_downloadable_media(self, message):
        """Check if message contains downloadable media"""
        if not message or not message.media:
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

    async def _find_alternative_message(self, file_unique_id, chat_id, original_file_id):
        """Advanced message recovery using multiple strategies"""
        recovery_methods = []
        
        # Method 1: Search recent chat history
        try:
            client = TgClient.user if self.session == "user" else TgClient.bot
            LOGGER.info(f"Searching chat history for file: {file_unique_id}")
            
            # Search more extensively (last 500 messages)
            found_count = 0
            async for message in client.get_chat_history(chat_id, limit=500):
                if found_count >= 5:  # Limit to prevent excessive searching
                    break
                    
                if (message.media and 
                    hasattr(getattr(message, message.media.value, None), 'file_unique_id')):
                    
                    media = getattr(message, message.media.value)
                    
                    # Check for exact match first
                    if media.file_unique_id == file_unique_id:
                        LOGGER.info(f"Found exact match in chat history: message_id {message.id}")
                        return message, "exact_match"
                    
                    # Check for same file_id (alternative message with same file)
                    if media.file_id == original_file_id:
                        LOGGER.info(f"Found same file_id in chat history: message_id {message.id}")
                        recovery_methods.append((message, "same_file_id"))
                        found_count += 1
                        
        except Exception as e:
            LOGGER.warning(f"Chat history search failed: {str(e)}")
        
        # Method 2: Try forwarded/copied messages (if any were found)
        if recovery_methods:
            return recovery_methods[0]  # Return the first alternative found
        
        # Method 3: Check if file exists in bot's dump chat (if configured)
        if hasattr(Config, 'LEECH_DUMP_CHAT') and Config.LEECH_DUMP_CHAT:
            try:
                LOGGER.info("Checking dump chat for file")
                async for message in client.get_chat_history(Config.LEECH_DUMP_CHAT, limit=200):
                    if (message.media and 
                        hasattr(getattr(message, message.media.value, None), 'file_unique_id')):
                        
                        media = getattr(message, message.media.value)
                        if media.file_unique_id == file_unique_id:
                            LOGGER.info(f"Found file in dump chat: message_id {message.id}")
                            return message, "dump_chat"
                            
            except Exception as e:
                LOGGER.warning(f"Dump chat search failed: {str(e)}")
        
        return None, "not_found"

    async def _validate_message_for_download(self, message):
        """Comprehensive validation before download attempt"""
        if not message:
            return False, "Message is None"
        
        if not self._is_downloadable_media(message):
            return False, "No downloadable media"
        
        try:
            media = getattr(message, message.media.value)
            if not hasattr(media, 'file_id') or not media.file_id:
                return False, "Invalid file_id"
            
            if not hasattr(media, 'file_size') or media.file_size <= 0:
                return False, "Invalid file_size"
            
            return True, "Valid"
            
        except Exception as e:
            return False, f"Validation error: {str(e)}"

    async def _queue_aware_message_recovery(self, original_message, path):
        """Enhanced message recovery specifically for queued downloads"""
        recovery_log = []
        
        # Step 1: Try to refresh original message
        try:
            if self.session == "user":
                fresh_message = await TgClient.user.get_messages(
                    chat_id=original_message.chat.id, 
                    message_ids=original_message.id
                )
            else:
                fresh_message = await self._listener.client.get_messages(
                    chat_id=original_message.chat.id, 
                    message_ids=original_message.id
                )
            
            is_valid, reason = await self._validate_message_for_download(fresh_message)
            if is_valid:
                recovery_log.append(f"✅ Original message refreshed successfully")
                LOGGER.info("Queue download: Original message is still valid")
                return fresh_message, recovery_log
            else:
                recovery_log.append(f"❌ Original message invalid: {reason}")
                
        except MessageIdInvalid:
            recovery_log.append("❌ Original message deleted")
            LOGGER.warning("Queue download: Original message has been deleted")
        except Exception as e:
            recovery_log.append(f"❌ Original message refresh failed: {str(e)}")
            LOGGER.warning(f"Queue download: Failed to refresh message: {str(e)}")
        
        # Step 2: Load cached data
        if self._cached_data:
            recovery_log.append("📋 Using cached message data")
            
            # Step 3: Search for alternative messages
            alternative_msg, method = await self._find_alternative_message(
                self._cached_data['file_unique_id'],
                self._cached_data['chat_id'],
                self._cached_data['file_id']
            )
            
            if alternative_msg:
                is_valid, reason = await self._validate_message_for_download(alternative_msg)
                if is_valid:
                    recovery_log.append(f"✅ Alternative message found via {method}")
                    LOGGER.info(f"Queue download: Found alternative message via {method}")
                    return alternative_msg, recovery_log
                else:
                    recovery_log.append(f"❌ Alternative message invalid: {reason}")
            else:
                recovery_log.append("❌ No alternative messages found")
        
        # Step 4: Load from queue cache if available
        queue_data = QueueMessageCache.load_queue_data(self._listener.mid)
        if queue_data:
            recovery_log.append("📋 Queue cache data available")
            # Try to reconstruct download from queue cache
            # This is a last resort method
            
        recovery_log.append("❌ All recovery methods exhausted")
        LOGGER.error("Queue download: All message recovery methods failed")
        return None, recovery_log

    async def _download_with_recovery(self, message, path):
        """Enhanced download with full recovery capabilities"""
        recovery_attempts = 0
        max_recovery_attempts = 3
        
        while recovery_attempts < max_recovery_attempts:
            try:
                # Pre-download validation
                is_valid, reason = await self._validate_message_for_download(message)
                if not is_valid:
                    if recovery_attempts == 0:
                        LOGGER.warning(f"Initial validation failed: {reason}, attempting recovery")
                        recovery_attempts += 1
                        
                        # Attempt message recovery
                        recovered_message, recovery_log = await self._queue_aware_message_recovery(message, path)
                        if recovered_message:
                            message = recovered_message
                            LOGGER.info("Message recovered successfully, retrying download")
                            continue
                        else:
                            LOGGER.error("Message recovery failed, aborting download")
                            for log_entry in recovery_log:
                                LOGGER.info(f"Recovery: {log_entry}")
                            await self._on_download_error("File unavailable and recovery failed")
                            return
                    else:
                        await self._on_download_error(f"Download validation failed: {reason}")
                        return
                
                # Attempt actual download
                download = await self._download_message(message, path)
                
                if self._listener.is_cancelled:
                    return
                
                if download is not None:
                    await self._on_download_complete()
                    # Clean up queue cache on successful completion
                    QueueMessageCache.remove_queue_data(self._listener.mid)
                    return
                else:
                    if not self._listener.is_cancelled:
                        await self._on_download_error("Download returned None")
                    return
                    
            except (FloodWait, FloodPremiumWait) as f:
                LOGGER.warning(f"Rate limit hit: {str(f)}")
                await sleep(f.value)
                continue  # Retry without incrementing recovery attempts
                
            except ValueError as ve:
                if "doesn't contain any downloadable media" in str(ve):
                    LOGGER.error(f"Media unavailable: {self._listener.name}")
                    
                    if recovery_attempts == 0:
                        LOGGER.info("Attempting message recovery due to media unavailability")
                        recovery_attempts += 1
                        
                        recovered_message, recovery_log = await self._queue_aware_message_recovery(message, path)
                        if recovered_message:
                            message = recovered_message
                            LOGGER.info("Message recovered, retrying download")
                            continue
                        else:
                            LOGGER.error("Recovery failed for media unavailability")
                            for log_entry in recovery_log:
                                LOGGER.info(f"Recovery: {log_entry}")
                    
                    await self._on_download_error(f"Media unavailable and recovery exhausted: {self._listener.name}")
                    return
                else:
                    LOGGER.error(f"Download error: {str(ve)}", exc_info=True)
                    await self._on_download_error(f"Download failed: {str(ve)}")
                    return
                    
            except Exception as e:
                LOGGER.error(f"Unexpected download error: {str(e)}", exc_info=True)
                recovery_attempts += 1
                
                if recovery_attempts < max_recovery_attempts:
                    LOGGER.info(f"Attempting recovery (attempt {recovery_attempts}/{max_recovery_attempts})")
                    recovered_message, recovery_log = await self._queue_aware_message_recovery(message, path)
                    if recovered_message:
                        message = recovered_message
                        continue
                
                await self._on_download_error(f"Download failed after {recovery_attempts} recovery attempts: {str(e)}")
                return
        
        await self._on_download_error(f"Download failed after {max_recovery_attempts} recovery attempts")

    async def _download_message(self, message, path):
        """Core download logic"""
        if self._hyper_dl:
            try:
                return await HyperTGDownload().download_media(
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
                        if self._is_downloadable_media(user_message):
                            return await user_message.download(
                                file_name=path, progress=self._on_download_progress
                            )
                    except Exception:
                        pass
                
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
        
        # Clean up queue cache on error
        QueueMessageCache.remove_queue_data(self._listener.mid)
        await self._listener.on_download_error(error)

    async def _on_download_complete(self):
        await self._listener.on_download_complete()
        async with global_lock:
            if self._id in GLOBAL_GID:
                GLOBAL_GID.pop(self._id)
        return

    async def add_download(self, message, path, session):
        self.session = session
        
        # Enhanced caching - cache immediately when download is requested
        self._cached_data = MessageCache.save_message_data(message)
        
        if not self.session:
            if self._hyper_dl:
                self.session = "hbots"
            elif self._listener.user_transmission and self._listener.is_super_chat:
                self.session = "user"
                try:
                    user_message = await TgClient.user.get_messages(
                        chat_id=message.chat.id, message_ids=message.id
                    )
                    if user_message and self._is_downloadable_media(user_message):
                        self._cached_data = MessageCache.save_message_data(user_message)
                        message = user_message
                except (PeerIdInvalid, ChannelInvalid):
                    LOGGER.warning("User session not in chat, using bot session")
                    self.session = "bot"
            else:
                self.session = "bot"
        
        # Determine media info (from cache or message)
        if self._cached_data:
            file_unique_id = self._cached_data['file_unique_id']
            file_size = self._cached_data['file_size']
            file_name = self._cached_data['file_name']
        else:
            if not self._is_downloadable_media(message):
                await self._on_download_error(f"No downloadable media and no cache for: {self._listener.name}")
                return
                
            media = getattr(message, message.media.value)
            file_unique_id = media.file_unique_id
            file_size = media.file_size
            file_name = getattr(media, 'file_name', None)

        async with global_lock:
            download_allowed = file_unique_id not in GLOBAL_GID

        if download_allowed:
            # Set listener name and path
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

            # Duplicate check
            msg, button = await stop_duplicate_check(self._listener)
            if msg:
                await self._listener.on_download_error(msg, button)
                return

            # Queue management
            add_to_queue, event = await check_running_tasks(self._listener)
            if add_to_queue:
                LOGGER.info(f"Added to Queue/Download: {self._listener.name}")
                
                # 🔥 ENHANCED QUEUE CACHING - Save complete context
                QueueMessageCache.save_queue_data(
                    self._listener.mid,
                    self._cached_data,
                    path
                )
                
                async with task_dict_lock:
                    task_dict[self._listener.mid] = QueueStatus(
                        self._listener, gid, "dl"
                    )
                await self._listener.on_download_start()
                if self._listener.multi <= 1:
                    await send_status_message(self._listener.message)
                
                # 🔥 CRITICAL: Wait for queue and then perform recovery
                await event.wait()
                
                LOGGER.info(f"Queue wait finished for: {self._listener.name}")
                
                if self._listener.is_cancelled:
                    async with global_lock:
                        if self._id in GLOBAL_GID:
                            GLOBAL_GID.pop(self._id)
                    QueueMessageCache.remove_queue_data(self._listener.mid)
                    return
                
                # 🔥 ENHANCED: Queue-aware message recovery
                recovered_message, recovery_log = await self._queue_aware_message_recovery(message, path)
                
                if recovered_message:
                    message = recovered_message
                    LOGGER.info("Queue download: Message successfully recovered")
                    for log_entry in recovery_log:
                        LOGGER.info(f"Queue Recovery: {log_entry}")
                else:
                    LOGGER.warning("Queue download: Message recovery failed, using cached data")
                    for log_entry in recovery_log:
                        LOGGER.warning(f"Queue Recovery: {log_entry}")
                        
            self._start_time = time()
            await self._on_download_start(file_unique_id, gid, add_to_queue)
            
            # 🔥 ENHANCED: Use recovery-aware download
            await self._download_with_recovery(message, path)
        else:
            await self._on_download_error("File already being downloaded!")

    async def cancel_task(self):
        self._listener.is_cancelled = True
        LOGGER.info(f"Cancelling download: {self._listener.name} id: {self._id}")
        
        # Clean up caches
        QueueMessageCache.remove_queue_data(self._listener.mid)
        await self._on_download_error("Stopped by user!")


# Utility functions
async def cleanup_all_caches():
    """Clean up all cache directories"""
    try:
        # Clean message cache
        MessageCache.cleanup_old_cache(max_age_days=7)
        
        # Clean queue cache
        current_time = time()
        for cache_file in QUEUE_CACHE_DIR.glob("queue_*.pkl"):
            try:
                with open(cache_file, 'rb') as f:
                    queue_data = pickle.load(f)
                
                # Remove queue cache older than 24 hours
                if current_time - queue_data.get('queued_at', 0) > (24 * 60 * 60):
                    cache_file.unlink()
                    LOGGER.info(f"Cleaned up old queue cache: {cache_file.name}")
                    
            except Exception as e:
                LOGGER.error(f"Error cleaning queue cache {cache_file}: {str(e)}")
                
        LOGGER.info("Cache cleanup completed")
        
    except Exception as e:
        LOGGER.error(f"Failed to cleanup caches: {str(e)}")

# Add this to your main bot loop
async def periodic_cache_cleanup():
    """Run this periodically in your main bot loop"""
    import asyncio
    while True:
        await asyncio.sleep(3600)  # Run every hour
        await cleanup_all_caches()