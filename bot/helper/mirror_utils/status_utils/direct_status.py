#!/usr/bin/env python3

from bot.helper.ext_utils.bot_utils import (EngineStatus, MirrorStatus,
                                            get_readable_file_size,
                                            get_readable_time)



class DirectStatus:
    def __init__(self, obj, gid, listener, upload_details):
        self.__gid = gid
        self.__listener = listener
        self.__obj = obj
        self.__name = self.__obj.name
        self.upload_details = upload_details
        self.message = self.__listener.message

    def gid(self):
        return self.__gid

    def speed_raw(self):
        return self.__obj.speed

    def progress_raw(self):
        try:
            return self.processed_raw() / self.__obj.total_size * 100
        except:
            return 0

    def progress(self):
        return f'{round(self.progress_raw(), 2)}%'

    def speed(self):
        return f'{get_readable_file_size(self.speed_raw())}/s'

    def name(self):
        return self.__name

    def size(self):
        return get_readable_file_size(self.__obj.total_size)

    def eta(self):
        try:
            seconds = (self.__obj.total_size - self.processed_raw()) / self.speed_raw()
            return get_readable_time(seconds)
        except:
            return '-'

    def status(self):
        return MirrorStatus.STATUS_DOWNLOADING

    def processed_bytes(self):
        return get_readable_file_size(self.processed_raw())

    def processed_raw(self):
        return self.__obj.processed_bytes

    def download(self):
        return self.__obj

    def eng(self):
        return EngineStatus().STATUS_ARIA
