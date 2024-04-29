from bot.helper.ext_utils.bot_utils import MirrorStatus, get_readable_file_size, get_readable_time

class UploadStatus:
    def __init__(self, obj, size, gid, listener):
        """
        Initialize UploadStatus object

        :param obj: The object being uploaded
        :param size: The total size of the object being uploaded
        :param gid: The global ID of the upload
        :param listener: The listener object
        """
        self.__obj = obj
        self.__size = size
        self.__gid = gid
        self.message = listener.message

