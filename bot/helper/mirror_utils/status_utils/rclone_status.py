from bot.helper.ext_utils.bot_utils import EngineStatus, MirrorStatus

class RcloneStatus:
    """Class to represent the status of an rclone operation."""

    def __init__(self, obj, message, gid, status, upload_details):
        self.__obj = obj
        self.__gid = gid
        self.__status = status
        self.message = message
        self.upload_details = upload_details

    @property

