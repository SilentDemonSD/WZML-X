from bot.helper.ext_utils.bot_utils import EngineStatus, MirrorStatus

class RcloneStatus:
    def __init__(self, obj, message, gid, status, upload_details):
        """
        Initialize RcloneStatus object with required parameters

        :param obj: Object containing rclone transfer information
        :param message: Message object for sending updates
        :param gid: Group id for the transfer
        :param status: Status of the transfer (dl/up/cloning)
        :param upload_details: Details of the upload
        """
        self.__obj = obj
        self.__gid = gid
        self.__status = status
        self.message = message
        self.upload_details = upload_details

    @property
    def gid(self):
        """
        Get the group id for the transfer

        :return: Group id
        """
        return self.__gid

    @property
    def progress(self):
        """
        Get the progress of the transfer as a percentage

        :return: Progress percentage
        """
        return self.__obj.percentage

    @property
    def speed(self):
        """
        Get the speed of the transfer

        :return: Transfer speed
        """
        return self.__obj.speed

    @property
    def name(self):
        """
        Get the name of the transfer

        :return: Name of the transfer
        """
        return self.__obj.name

    @property
    def size(self):
        """
        Get the size of the transfer

        :return: Size of the transfer
        """
        return self.__obj.size

    @property
    def eta(self):
        """
        Get the estimated time of arrival for the transfer

        :return: ETA for the transfer
        """
        return self.__obj.eta

    @property
    def status(self):
        """
        Get the status of the transfer

        :return: Status of the transfer
        """
        if self.__status == 'dl':
            return MirrorStatus.STATUS_DOWNLOADING
        elif self.__status == 'up':
            return MirrorStatus.STATUS_UPLOADING
        else:
            return MirrorStatus.STATUS_CLONING

    @property
    def processed_bytes(self):
        """
        Get the number of bytes processed in the transfer

        :return: Number of processed bytes
        """
        return self.__obj.transferred_size

    @property
    def obj(self):
        """
        Get the rclone transfer object

        :return: Rclone transfer object
        """
        return self.__obj

    @property
    def eng(self):
        """
        Get the engine status for rclone

        :return: Engine status
        """
        return EngineStatus().STATUS_RCLONE
