#!/usr/bin/env python3
from bot.helper.ext_utils.bot_utils import EngineStatus, MirrorStatus, get_readable_file_size, get_readable_time

class GDriveStatus:
    def __init__(self, obj, size, message, gid, status, upload_details):
        self.obj = obj
        self.size = size
        self.message = message
        self.gid = gid
        self.status = status
        self.upload_details = upload_details

    def processed_bytes(self):
        return get_readable_file_size(self.obj.processed_bytes)

    def status(self):
        match self.status:
            case 'up':
                return MirrorStatus.STATUS_UPLOADING
            case 'dl':
              
