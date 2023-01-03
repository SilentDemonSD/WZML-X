from bot.helper.ext_utils.bot_utils import MirrorStatus, get_readable_file_size, EngineStatus


class ConvertStatus:
    def __init__(self, name, size, gid, listener):
        self.__name = name
        self.__gid = gid
        self.__size = size
        self.__listener = listener
        self.message = self.__listener.message

    def gid(self):
        return self.__gid

    def progress(self):
        return '0'

    def speed(self):
        return '0'

    def name(self):
        return self.__name

    def size(self):
        return get_readable_file_size(self.__size)

    def eta(self):
        return '0s'

    def status(self):
        return MirrorStatus.STATUS_CONVERTING

    def processed_bytes(self):
        return 0

    def download(self):
        return self

    def eng(self):
        return EngineStatus.STATUS_SPLIT_MERGE

    def source(self):
        reply_to = self.message.reply_to_message
        return reply_to.from_user.username or reply_to.from_user.id if reply_to and \
            not reply_to.from_user.is_bot else self.message.from_user.username \
                or self.message.from_user.id

    def mode(self):
        return self.__listener.mode