from bot.helper.ext_utils.bot_utils import MirrorStatus, get_readable_file_size, get_readable_time, EngineStatus

class CloneStatus:
    def __init__(self, obj, size, message, gid):
        self.__obj = obj
        self.__size = size
        self.__gid = gid
        self.message = message

    def processed_bytes(self):
        return self.__obj.transferred_size

    def size_raw(self):
        return self.__size

    def size(self):
        return get_readable_file_size(self.__size) if self.__size is not None else 'Unknown'

    def status(self):
        return MirrorStatus.STATUS_CLONING

    def name(self):
        return self.__obj.name if self.__obj is not None else 'Unknown'

    def gid(self) -> str:
        return self.__gid

    def progress_raw(self):
        try:
            return self.__obj.transferred_size / self.__size * 100 if self.__size is not None else 0
        except ZeroDivisionError:
            return 0

    def progress(self):
        return f'{round(self.progress_raw(), 2)}%'

    def speed_raw(self):
        """
        :return: Download speed in Bytes/Seconds or 0 if there's an error
        """
        try:
            return self.__obj.cspeed() if self.__obj is not None else 0
        except:
            return 0

    def speed(self):
        return f'{get_readable_file_size(self.speed_raw())}/s' if self.speed_raw() > 0 else 'Unknown'

    def eta(self):
        try:
            if self.__size is not None and self.speed_raw() > 0:
                seconds = (self.__size - self.__obj.transferred_size) / self.speed_raw()
                return f'{get_readable_time(seconds)}'
            return '-'
        except:
            return '-'

    def download(self):
        return self.__obj

    def eng(self):
        return EngineStatus.STATUS_GD
