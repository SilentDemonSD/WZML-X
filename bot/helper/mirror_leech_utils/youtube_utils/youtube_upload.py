import contextlib
import os
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
        self.path = path
        self._is_errored = False
        super().__init__()
        self.is_uploading = True
        self.is_folder_upload = False
        self.video_files = []
        self.total_files = 0
        self.size = 0

        if ospath.isdir(self.path):
            self.is_folder_upload = True
            self.name = ospath.basename(self.path)
            for root, _, files in os.walk(self.path):
                for file in files:
                    file_path = ospath.join(root, file)
                    self.video_files.append(file_path)
                    self.size += ospath.getsize(file_path)
            self.total_files = len(self.video_files)
            if not self.video_files:
                LOGGER.warning(f"No video files found in folder: {self.path}")
        elif ospath.isfile(self.path):
            self.is_folder_upload = False
            self.name = listener.name
            self.size = ospath.getsize(self.path)
            self.video_files = []
            self.total_files = 1
        else:
            raise ValueError(f"Invalid path: {self.path} is not a file or directory.")

        self._path = self.path

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

        LOGGER.info(f"Uploading to YouTube: {self.name}")
        self._updater = SetInterval(self.update_interval, self.progress)
        video_url = None
        playlist_url = None

        try:
            if self.is_folder_upload:
                if not self.video_files:
                    raise ValueError(
                        f"No video files found to upload in folder: {self.name}"
                    )

                playlist_id = self._create_playlist(
                    self.name, Config.YT_PRIVACY_STATUS, Config.YT_DESP
                )
                if not playlist_id:
                    raise ValueError("Failed to create playlist.")

                playlist_url = f"https://www.youtube.com/playlist?list={playlist_id}"
                LOGGER.info(f"Created playlist: {self.name} - {playlist_url}")

                for video_path in self.video_files:
                    if self.listener.is_cancelled:
                        LOGGER.info("Upload cancelled by user during folder upload.")
                        break

                    video_title = ospath.splitext(ospath.basename(video_path))[0]
                    current_video_url = self._upload_video(
                        video_path, video_title, get_mime_type(video_path), playlist_id
                    )
                    if not current_video_url:
                        LOGGER.error(f"Failed to upload video: {video_path}")
                        self._is_errored = True
                    else:
                        LOGGER.info(
                            f"Uploaded video to playlist: {video_title} - {current_video_url}"
                        )

                if self.listener.is_cancelled:
                    return

                if not self._is_errored and not self.video_files:
                    raise ValueError(
                        f"No compatible video files were uploaded from folder: {self.name}"
                    )

            elif ospath.isfile(self.path):
                mime_type = get_mime_type(self.path) or "Video"
                video_url = self._upload_video(self.path, self.name, mime_type)

                if self.listener.is_cancelled:
                    return

                if video_url is None and not self.listener.is_cancelled:
                    raise ValueError(
                        "Upload failed or was cancelled, no video URL returned."
                    )

                if video_url:
                    LOGGER.info(f"Uploaded To YouTube: {self.name} - {video_url}")
            else:

                raise ValueError(f"Invalid path type for upload: {self.path}")

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
            LOGGER.info("Upload process cancelled.")
            return

        if self._is_errored and not self.is_folder_upload:
            return

        if self._is_errored and self.is_folder_upload:

            pass

        if self.is_folder_upload:
            if not self.video_files and not playlist_url:
                async_to_sync(
                    self.listener.on_upload_error,
                    f"No video files found in {self.name}",
                )
                return

            if (
                self._is_errored
                and playlist_url
                and not any(ospath.exists(v_path) for v_path in self.video_files)
            ):

                pass

            async_to_sync(
                self.listener.on_upload_complete,
                playlist_url,
                self.total_files,
                0,
                "Folder/Playlist",
            )
        elif video_url:
            async_to_sync(
                self.listener.on_upload_complete,
                video_url,
                1,
                0,
                mime_type,
            )

        return

    def _create_playlist(self, title, privacy_status="public", description=""):
        """Creates a YouTube playlist."""
        try:
            body = {
                "snippet": {
                    "title": title,
                    "description": description,
                },
                "status": {"privacyStatus": privacy_status},
            }
            response = (
                self.service.playlists()
                .insert(part="snippet,status", body=body)
                .execute()
            )
            LOGGER.info(f"Playlist created: {response['id']}")
            return response["id"]
        except HttpError as e:
            LOGGER.error(f"Failed to create playlist: {e}")
            return None
        except Exception as e:
            LOGGER.error(f"An unexpected error occurred while creating playlist: {e}")
            return None

    @retry(
        wait=wait_exponential(multiplier=2, min=3, max=6),
        stop=stop_after_attempt(3),
        retry=retry_if_exception_type(Exception),
    )
    def _upload_video(self, file_path, file_name, mime_type, playlist_id=None):
        """Upload video to YouTube and optionally add to a playlist."""

        title = file_name
        description = Config.YT_DESP
        tags = Config.YT_TAGS
        category_id = Config.YT_CATEGORY_ID
        privacy_status = Config.YT_PRIVACY_STATUS

        video_body = {
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

        media_body = MediaFileUpload(
            file_path, mimetype=mime_type, resumable=True, chunksize=1024 * 1024 * 4
        )

        insert_request = self.service.videos().insert(
            part=",".join(video_body.keys()), body=video_body, media_body=media_body
        )

        video_response = None
        retries = 0
        current_chunk_uploaded_bytes = 0

        while video_response is None and not self.listener.is_cancelled:
            try:
                prev_progress_bytes = current_chunk_uploaded_bytes
                self.status, video_response = insert_request.next_chunk()

                if self.status:
                    current_video_total_size = ospath.getsize(file_path)
                    current_chunk_uploaded_bytes = self.status.resumable_progress

                    if current_video_total_size > 0:
                        self.upload_progress = int(
                            (current_chunk_uploaded_bytes / current_video_total_size)
                            * 100
                        )
                    else:
                        self.upload_progress = (
                            100 if current_chunk_uploaded_bytes > 0 else 0
                        )

                    LOGGER.info(f"Uploading '{title}': {self.upload_progress}%")

            except HttpError as err:

                if err.resp.status in [500, 502, 503, 504, 429] and retries < 5:
                    retries += 1
                    LOGGER.warning(
                        f"HTTP error {err.resp.status} for '{title}', retrying... ({retries}/5)"
                    )
                    continue
                error_content = (
                    err.content.decode("utf-8") if err.content else "Unknown error"
                )
                LOGGER.error(f"YouTube upload failed for '{title}': {error_content}")
                raise err
            except Exception as e:
                LOGGER.error(f"Unexpected error during upload of '{title}': {e}")
                raise e

        if self.listener.is_cancelled:
            LOGGER.info(f"Upload of '{title}' cancelled by user.")
            return None

        if video_response:
            video_id = video_response["id"]
            video_url = f"https://www.youtube.com/watch?v={video_id}"
            LOGGER.info(f"Video '{title}' uploaded successfully: {video_url}")

            if playlist_id:
                try:
                    playlist_item_body = {
                        "snippet": {
                            "playlistId": playlist_id,
                            "resourceId": {
                                "kind": "youtube#video",
                                "videoId": video_id,
                            },
                        }
                    }
                    self.service.playlistItems().insert(
                        part="snippet", body=playlist_item_body
                    ).execute()
                    LOGGER.info(f"Video '{title}' added to playlist.")
                except HttpError as e:
                    LOGGER.error(f"Failed to add video '{title}' to playlist: {e}")

                except Exception as e:
                    LOGGER.error(
                        f"An unexpected error occurred while adding video '{title}' to playlist: {e}"
                    )

            with contextlib.suppress(Exception):
                remove(file_path)

            return video_url

        if not self.listener.is_cancelled:
            LOGGER.error(
                f"Upload of '{title}' completed but no response received and not cancelled."
            )
            raise ValueError(
                f"Upload of '{title}' gave no response and was not cancelled."
            )
        return None

    def get_upload_status(self):
        return {
            "progress": self.upload_progress,
            "speed": self.speed,
            "processed_bytes": self.processed_bytes,
            "total_files": self.total_files,
            "is_uploading": self.is_uploading,
        }
