#!/usr/bin/env python3

from bot.helper.ext_utils.bot_utils import (
    EngineStatus,
    MirrorStatus,
    get_readable_file_size,
    get_readable_time,
)

class DirectStatus:
    def __init__(
        self,
        obj,
        gid: str,
        listener,
        upload_details,
    ):
        """
        Initialize the DirectStatus class.

        :param obj: The object containing the file information
        :param gid: The global ID of the file
        :param listener: The listener object
        :param upload_details: The upload details
        """
        self.gid = gid
        self.listener = listener
        self.obj = obj
        self.upload_details = upload_details
        self.message = self.listener.message

    def gid(self) -> str:
        """
        Get the global ID of the file.

        :return: The global ID of the file
        """
        return self.__gid

    def progress_raw(self) -> float:
        """
        Get the progress of the file in percentage.

        :return: The progress of the file in percentage
        """
        try:
            return self.obj.processed_bytes / self.obj.total_size * 100
        except:
            return 0

    def progress(self) -> str:
        """
        Get the progress of the file in percentage as a formatted string.

        :return: The progress of the file in percentage as a formatted string
        """
        return f"{round(self.progress_raw(), 2)}%"

    def speed(self) -> str:
        """
        Get the speed of the file transfer.

        :return: The speed of the file transfer
        """
        return f"{get_readable_file_size(self.obj.speed)}/s"

    def name(self) -> str:
        """
        Get the name of the file.

        :return: The name of the file
        """
        return self.obj.name

    def size(self) -> str:
        """
        Get the size of the file.

        :return: The size of the file
        """
        return get_readable_file_size(self.obj.total_size)

    def eta(self) -> str:
        """
        Get the estimated time of arrival.

        :return: The estimated time of arrival
        """
        try:
            seconds = (self.obj.total_size - self.obj.processed_bytes) / self.obj.speed
            return get_readable_time(seconds)
        except:
            return "-"

    def status(self) -> MirrorStatus:
        """
        Get the status of the file transfer.

        :return: The status of the file transfer
        """
        if self.obj.task and self.obj.task.is_waiting:
            return MirrorStatus.STATUS_QUEUED
        return MirrorStatus.STATUS_DOWNLOADING

    def processed_bytes(self) -> str:
        """
        Get the number of processed bytes.

        :return: The number of processed bytes
        """
        return get_readable_file_size(self.obj.processed_bytes)

    def download(self) -> object:
        """
        Get the file object.

        :return: The file object
        """
        return self.obj

    def eng(self) -> EngineStatus:
        """
        Get the engine status.

        :return: The engine status
        """
        return EngineStatus().STATUS_ARIA

    def __str__(self):
        """
        Get a string representation of the object.

        :return: A string representation of the object
        """
        return (
            f"DirectStatus(\n"
            f"gid={self.gid()},\n"
            f"listener={self.listener},\n"
            f"obj={self.obj},\n"
            f"upload_details={self.upload_details},\n"
            f"message={self.message},\n"
            f"progress={self.progress()},\n"
            f"speed={self.speed()},\n"
            f"name={self.name()},\n"
            f"size={self.size()},\n"
            f"eta={self.eta()},\n"
            f"status={self.status()},\n"
            f"processed_bytes={self.processed_bytes()},\n"
            f"download={self.download()},\n"
            f"eng={self.eng()}\n"
            f")"
        )
