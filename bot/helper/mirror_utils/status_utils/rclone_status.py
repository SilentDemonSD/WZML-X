from bot.helper.ext_utils.bot_utils import EngineStatus, MirrorStatus

class RcloneStatus:
    """Class to represent the status of an rclone operation."""

    def __init__(self, obj, gid, status, upload_details, message=None):
        """
        Initialize the RcloneStatus class with the following parameters:
        - obj: The object being operated on by rclone.
        - gid: The group ID associated with the operation.
        - status: The current status of the operation (e.g. 'completed', 'failed', or 'in_progress').
        - upload_details: Details about the upload, if applicable.
        - message: An optional message associated with the operation.
        """
        self.obj = obj
        self.gid = gid
        self.status = status
        self.upload_details = upload_details
        self.message = message

    @property
    def engine_status(self) -> EngineStatus:
        """
        Return the engine status as an EngineStatus object. This method maps the current status to an EngineStatus object.
        """
        if self.status == 'completed':
            return EngineStatus.COMPLETED
        elif self.status == 'failed':
            return EngineStatus.FAILED
        else:
            return EngineStatus.IN_PROGRESS

    @property
    def mirror_status(self) -> MirrorStatus:
        """
        Return the mirror status as a MirrorStatus object. This method maps the current status to a MirrorStatus object.
        """
        if self.status == 'completed':
            return MirrorStatus.MIRROR_COMPLETED
        elif self.status == 'failed':
            return MirrorStatus.MIRROR_FAILED
        else:
            return MirrorStatus.MIRROR_IN_PROGRESS

    def get_engine_status(self) -> str:
        """
        Return the engine status as a string. This method maps the EngineStatus object to a string representation.
        """
        engine_status = self.engine_status
        return engine_status.name if engine_status else 'UNKNOWN'

    def get_mirror_status(self) -> str:
        """
        Return the mirror status as a string. This method maps the MirrorStatus object to a string representation.
        """
        mirror_status = self.mirror_status
        return mirror_status.name if mirror_status else 'UNKNOWN'

    def __str__(self):
        """
        Return a readable string representation of the RcloneStatus object.
        """
        return (
            f"RcloneStatus("
            f"obj={self.obj}, "
            f"gid={self.gid}, "
            f"status={self.status}, "
            f"message={self.message}, "
            f"upload_details={self.upload_details}"
            f")"
        )
