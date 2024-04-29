from bot import DOWNLOAD_DIR
from bot.helper.ext_utils.bot_utils import MirrorStatus, get_readable_file_size, get_readable_time, EngineStatus
from bot.helper.ext_utils.fs_utils import get_path_size

class YtDlpDownloadStatus:
    def __init__(self, obj, listener, gid):
        self.__obj = obj
        self.__uid = listener.uid
        self.__gid = gid
        self.message = listener.message

