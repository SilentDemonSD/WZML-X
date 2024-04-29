#!/usr/bin/env python3
from bot.helper.ext_utils.bot_utils import EngineStatus, MirrorStatus
from bot.helper.ext_utils.fs_utils import get_path_size
from bot.helper.ext_utils.time_utils import get_readable_time
from typing import Union

class YtDlpDownloadStatus:
    def __init__(self, obj, listener, gid, message=None):
        self.obj = obj
        self.listener = listener
        self.upload_details = getattr(listener, 'upload_details', None)
        self.gid = gid
        self.message = message if message else listener.message

    def get_status(self):
        """
        Return the status of the download as a string.
        """
        status = self.obj.get_status()
        if status == EngineStatus.STATUS_QUEUED:
            return f"Queued - Size: {get_readable_size(get_path_size(self.obj.get_download_folder()))}"
        elif status == EngineStatus.STATUS_DOWNLOADING:
            return f"Downloading - Speed: {self.obj.get_download_speed()} - ETA: {self.obj.get_eta()} - Progress: {self.obj.get_progress()}"
        elif status == EngineStatus.STATUS_COMPLETE:
            return f"Complete - Size: {get_readable_size(get_path_size(self.obj.get_download_folder()))}"
        elif status == EngineStatus.STATUS_ERROR:
            return f"Error - {self.obj.get_error()}"
        elif status == EngineStatus.STATUS_CANCELED:
            return "Canceled"
        else:
            return "Unknown status"

def get_readable_size(size):
    """
    Return a human-readable string representing the size.
    """
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size < 1024:
            break
        size /= 1024.0
    return f"{size:.2f} {unit}"
