import contextlib
from logging import getLogger
from os import path as ospath
from os import remove

from bot.core.config_manager import Config
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload
from tenacity import (
    RetryError,
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from bot.helper.ext_utils.bot_utils import SetInterval, async_to_sync
from bot.helper.ext_utils.files_utils import get_mime_type
from bot.helper.mirror_leech_utils.youtube_utils.youtube_helper import YouTubeHelper

LOGGER = getLogger(__name__)


class YouTubeUpload(YouTubeHelper):
    def __init__(self, listener, path):
        self.listener = listener
        self._updater = None
        self._path = path
        self._is_errored = False
        super().__init__()
        self.is_uploading = True

    def user_setting(self):
        """Handle user-specific YouTube token settings"""
        if self.listener.up_dest.startswith("yt:"):
            self.token_path = f"tokens/{self.listener.user_id}.pickle"
            self.listener.up_dest = self.listener.up_dest.replace("yt:", "", 1)
        elif hasattr(self.listener, "user_id") and self.listener.user_id:
            self.token_path = f"tokens/{self.listener.user_id}.pickle"

    def upload(self):
        """Main upload function"""
        self.user_setting()
        try:
            self.service = self.authorize(
                self.listener.user_id if hasattr(self.listener, "user_id") else ""
            )
        except Exception as e:
            LOGGER.error(f"YouTube authorization failed: {e}")
            async_to_sync(
                self.listener.on_upload_error, f"YouTube authorization failed: {e!s}"
            )
            return

        LOGGER.info(f"Uploading to YouTube: {self._path}")
        self._updater = SetInterval(self.update_interval, self.progress)
        video_url = None

        try:
            if ospath.isfile(self._path):
                mime_type = get_mime_type(self._path)

                # Check if file is a video
                if not mime_type.startswith("video/"):
                    raise ValueError(f"File is not a video. MIME type: {mime_type}")

                video_url = self._upload_video(
                    self._path, self.listener.name, mime_type
                )

                if self.listener.is_cancelled:
                    return

                if video_url is None:
                    raise ValueError("Upload has been manually cancelled")

                LOGGER.info(f"Uploaded To YouTube: {self._path}")
            else:
                raise ValueError("YouTube only supports single video file uploads")

        except Exception as err:
            if isinstance(err, RetryError):
                LOGGER.info(f"Total Attempts: {err.last_attempt.attempt_number}")
                err = err.last_attempt.exception()
            err = str(err).replace(">", "").replace("<", "")
            LOGGER.error(err)
            async_to_sync(self.listener.on_upload_error, err)
            self._is_errored = True
        finally:
            self._updater.cancel()

        if self.listener.is_cancelled and not self._is_errored:
            return

        if self._is_errored:
            return

        async_to_sync(
            self.listener.on_upload_complete,
            video_url,
            1,  # total_files
            0,  # total_folders
            "Video",  # mime_type
        )
        return

    @retry(
        wait=wait_exponential(multiplier=2, min=3, max=6),
        stop=stop_after_attempt(3),
        retry=retry_if_exception_type(Exception),
    )
    def _upload_video(self, file_path, file_name, mime_type):
        """Upload video to YouTube"""

        # Default video metadata
        title = file_name
        description = Config.YT_DESP
        tags = Config.YT_TAGS
        category_id = Config.YT_CATEGORY_ID
        privacy_status = Config.YT_PRIVACY_STATUS

        body = {
            "snippet": {
                "title": title,
                "description": description,
                "tags": tags,
                "categoryId": category_id,
            },
            "status": {
                "privacyStatus": privacy_status,
                "selfDeclaredMadeForKids": False,
            },
        }

        # Create media upload object
        media_body = MediaFileUpload(
            file_path,
            mimetype=mime_type,
            resumable=True,
            chunksize=1024 * 1024 * 4,  # 4MB chunks
        )

        # Create the upload request
        insert_request = self.service.videos().insert(
            part=",".join(body.keys()), body=body, media_body=media_body
        )

        response = None
        retries = 0

        while response is None and not self.listener.is_cancelled:
            try:
                self.status, response = insert_request.next_chunk()
                if self.status:
                    self.upload_progress = int(self.status.progress() * 100)
                    LOGGER.info(f"Upload progress: {self.upload_progress}%")

            except HttpError as err:
                if err.resp.status in [500, 502, 503, 504, 429] and retries < 5:
                    retries += 1
                    LOGGER.warning(
                        f"HTTP error {err.resp.status}, retrying... ({retries}/5)"
                    )
                    continue
                error_content = (
                    err.content.decode("utf-8") if err.content else "Unknown error"
                )
                LOGGER.error(f"YouTube upload failed: {error_content}")
                raise err
            except Exception as e:
                LOGGER.error(f"Unexpected error during upload: {e}")
                raise e

        if self.listener.is_cancelled:
            return None

        # Clean up the file after successful upload
        with contextlib.suppress(Exception):
            remove(file_path)

        self.file_processed_bytes = 0
        self.total_files += 1

        if response:
            video_id = response["id"]
            video_url = f"https://www.youtube.com/watch?v={video_id}"
            LOGGER.info(f"Video uploaded successfully: {video_url}")
            return video_url
        raise ValueError("Upload completed but no response received")

    def get_upload_status(self):
        return {
            "progress": self.upload_progress,
            "speed": self.speed,
            "processed_bytes": self.processed_bytes,
            "total_files": self.total_files,
            "is_uploading": self.is_uploading,
        }
