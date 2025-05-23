from logging import ERROR, getLogger
from os import path as ospath
from pickle import load as pload
from urllib.parse import parse_qs, urlparse

from google_auth_httplib2 import AuthorizedHttp
from googleapiclient.discovery import build
from googleapiclient.http import build_http
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

LOGGER = getLogger(__name__)
getLogger("googleapiclient.discovery").setLevel(ERROR)


class YouTubeHelper:
    def __init__(self):
        self._OAUTH_SCOPE = [
            "https://www.googleapis.com/auth/youtube.upload",
            "https://www.googleapis.com/auth/youtube",
        ]
        self.token_path = "token.pickle"
        self.is_uploading = False
        self.service = None
        self.total_files = 0
        self.file_processed_bytes = 0
        self.proc_bytes = 0
        self.total_time = 0
        self.status = None
        self.update_interval = 3
        self.upload_progress = 0

    @property
    def speed(self):
        try:
            return self.proc_bytes / self.total_time
        except Exception:
            return 0

    @property
    def processed_bytes(self):
        return self.proc_bytes

    async def progress(self):
        if self.status is not None:
            if hasattr(self.status, "total_size") and hasattr(self.status, "progress"):
                chunk_size = (
                    self.status.total_size * self.status.progress()
                    - self.file_processed_bytes
                )
                self.file_processed_bytes = (
                    self.status.total_size * self.status.progress()
                )
                self.proc_bytes += chunk_size
                self.total_time += self.update_interval
            else:
                # For YouTube uploads, we'll track progress differently
                self.total_time += self.update_interval

    def authorize(self, user_id=""):
        credentials = None
        token_path = self.token_path

        if user_id:
            token_path = f"tokens/{user_id}.pickle"

        if ospath.exists(token_path):
            LOGGER.info(f"Authorize YouTube with {token_path}")
            with open(token_path, "rb") as f:
                credentials = pload(f)
        else:
            LOGGER.error(f"YouTube token file {token_path} not found!")
            raise FileNotFoundError(f"YouTube token file {token_path} not found!")

        authorized_http = AuthorizedHttp(credentials, http=build_http())
        authorized_http.http.disable_ssl_certificate_validation = True
        return build("youtube", "v3", http=authorized_http, cache_discovery=False)

    def get_video_id_from_url(self, url):
        """Extract video ID from YouTube URL"""
        if "youtube.com/watch?v=" in url:
            parsed = urlparse(url)
            return parse_qs(parsed.query)["v"][0]
        if "youtu.be/" in url:
            return url.split("youtu.be/")[1].split("?")[0]
        return url  # Assume it's already a video ID

    @retry(
        wait=wait_exponential(multiplier=2, min=3, max=6),
        stop=stop_after_attempt(3),
        retry=retry_if_exception_type(Exception),
    )
    def get_video_info(self, video_id):
        """Get video information"""
        return (
            self.service.videos()
            .list(part="snippet,statistics,status", id=video_id)
            .execute()
        )

    @retry(
        wait=wait_exponential(multiplier=2, min=3, max=6),
        stop=stop_after_attempt(3),
        retry=retry_if_exception_type(Exception),
    )
    def get_channel_info(self):
        """Get channel information"""
        return (
            self.service.channels().list(part="snippet,statistics", mine=True).execute()
        )

    def escapes(self, estr):
        """Escape special characters in strings"""
        chars = ["\\", "'", '"', r"\a", r"\b", r"\f", r"\n", r"\r", r"\t"]
        for char in chars:
            estr = estr.replace(char, f"\\{char}")
        return estr.strip()

    async def cancel_task(self):
        """Cancel the current upload task"""
        self.listener.is_cancelled = True
        if self.is_uploading:
            LOGGER.info(f"Cancelling YouTube Upload: {self.listener.name}")
            await self.listener.on_upload_error(
                "Your YouTube upload has been cancelled!"
            )
