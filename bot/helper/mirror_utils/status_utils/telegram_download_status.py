from bot.helper.ext_utils.bot_utils import (
    MirrorStatus,
    get_readable_file_size,
    get_readable_time,
    EngineStatus,
)

class TelegramDownloadStatus:
    def __init__(self, obj: any, listener, gid: int):
        self.__obj = obj
        self.__gid = gid
        self.message = listener.message

