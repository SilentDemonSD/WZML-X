from bot.helper.ext_utils.bot_utils import EngineStatus, MirrorStatus

class RcloneStatus:
    """Class to represent the status of an rclone operation."""

    def __init__(self, obj, message, gid, status, upload_details):
        self.obj = obj
        self.gid = gid
        self.status = status
        self.message = message
        self.upload_details = upload_details

    @property
    def engine_status(self):
        """Returns the engine status as an EngineStatus object."""
        if self.status == 'completed':
            return EngineStatus.COMPLETED
        elif self.status == 'failed':
            return EngineStatus.FAILED
        else:
            return EngineStatus.IN_PROGRESS

    @property
    def mirror_status(self):
        """Returns the mirror status as a MirrorStatus object."""
        if self.status == 'completed':
            return MirrorStatus.MIRROR_COMPLETED
        elif self.status == 'failed':
            return MirrorStatus.MIRROR_FAILED
        else:
            return MirrorStatus.MIRROR_IN_PROGRESS

    def __str__(self):
        """Returns a string representation of the RcloneStatus object."""
        return f"RcloneStatus(obj={self.obj}, gid={self.gid}, status={self.status}, message={self.message}, upload_details={self.upload_details})"
