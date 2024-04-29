from bot.helper.ext_utils.bot_utils import MirrorStatus, get_readable_file_size, get_readable_time, EngineStatus

class GDDownloadStatus:
    def __init__(self, obj, size, listener, gid):
        self.obj = obj

