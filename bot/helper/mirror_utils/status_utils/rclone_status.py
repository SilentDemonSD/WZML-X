from bot.helper.ext_utils.bot_utils import EngineStatus, MirrorStatus

class RcloneStatus:
    """Class to represent the status of an rclone operation."""

    def __init__(self, obj, gid, status, upload_details, message=None):
        self.obj = obj
        self.gid = gid
        self.status = status
        self.upload_details = upload_details
        self.message = message

    @property
    def engine_status(self) -> EngineStatus:
        """Return the engine status as an EngineStatus object."""
        if self.status == 'completed':
            return EngineStatus.COMPLETED
        elif self.status == 'failed':
            return EngineStatus.FAILED
        else:
            return EngineStatus.IN_PROGRESS

    @property
    def mirror_status(self) -> MirrorStatus:
        """Return the mirror status as a MirrorStatus object."""
        if self.status == 'completed':
            return MirrorStatus.MIRROR_COMPLETED
        elif self.status == 'failed':
            return MirrorStatus.MIRROR_FAILED
        else:
            return MirrorStatus.MIRROR_IN_PROGRESS

    def get_engine_status(self) -> str:
        """Return the engine status as a string."""
        engine_status = self.engine_status
        return engine_status.name if engine_status else 'UNKNOWN'

    def get_mirror_status(self) -> str:
        """Return the mirror status as a string."""
        mirror_status = self.mirror_status
        return mirror_status.name if mirror_status else 'UNKNOWN'

    def __str__(self):
        """Return a readable string representation of the RcloneStatus object."""
        return (
            f"RcloneStatus("
            f"obj={self.obj}, "
            f"gid={self.gid}, "
            f"status={self.status}, "
            f"message={self.message}, "
            f"upload_details={self.upload_details}"
            f")"
        )
