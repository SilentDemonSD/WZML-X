#!/usr/bin/env python3
from bot.helper.ext_utils.bot_utils import EngineStatus
from bot.helper.ext_utils.fs_utils import get_path_size
from bot.helper.ext_utils.time_utils import get_readable_time
from typing import Optional

class YtDlpDownloadStatus:
    """
    A class representing the status of a youtube-dlp download.
    """
    def __init__(self, obj: Optional[YoutubeDlpObject], listener: Optional[Listener]):
        self.obj = obj
        self.listener = listener
        self.upload_details = getattr(listener, 'upload_details', None)

    @property
    def status(self) -> str:
        """
        Return the status of the download as a string.
        """
        if not self.obj:
            return "Unknown status"

        status = self.obj.get_status()
        if status == EngineStatus.STATUS_QUEUED:
            download_folder = self.obj.get_download_folder()
            if not download_folder:
                return "Unknown status"
            size = get_path_size(download_folder)
            return f"Queued - Size: {self._get_readable_size(size)}"
        elif status == EngineStatus.STATUS_DOWNLOADING:
            speed = self.obj.get_download_speed()
            eta = self.obj.get_eta()
            if eta is None or eta < 0:
                eta_str = "Unknown"
            else:
                eta_str = get_readable_time(eta)
            progress = self.obj.get_progress()
            return f"Downloading - Speed: {speed} - ETA: {eta_str} - Progress: {progress}"
        elif status == EngineStatus.STATUS_COMPLETE:
            download_folder = self.obj.get_download_folder()
            if not download_folder:
                return "Unknown status"
            size = get_path_size(download_folder)
            return f"Complete - Size: {self._get_readable_size(size)}"
        elif status == EngineStatus.STATUS_ERROR:
            error = self.obj.get_error()
            if not error:
                return "Unknown status"
            return f"Error - {error}"
        elif status == EngineStatus.STATUS_CANCELED:
            return "Canceled"
        else:
            return "Unknown status"

    @staticmethod
    def _get_readable_size(size: Union[int, float]) -> str:
        """
        Return a human-readable string representing the size.
        """
        if size is None:
            return "Unknown size"

        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size < 1024:
                break
            size /= 1024.0
        return f"{size:.2f} {unit}"

if __name__ == "__main__":
    # Example usage
    from youtube_dlp import YoutubeDlpObject

    obj = YoutubeDlpObject()
    status = YtDlpDownloadStatus(obj, None)
    print(status.status)
