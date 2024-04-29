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
        file_info: object,
        file_global_id: str,
        listener: object,
        upload_details: object,
    ):
        """
        Initialize the DirectStatus class.

        :param file_info: The object containing the file information
        :param file_global_id: The global ID of the file
        :param listener: The listener object
        :param upload_details: The upload details
        """
        self.file_global_id = file_global_id
        self.listener = listener
        self.file_info = file_info
        self.upload_details = upload_details
        self.message = listener.message

    @property
    def file_global_id(self) -> str:
        """
        Get the global ID of the file.

        :return: The global ID of the file
        """
        return self.__file_global_id

    @file_global_id.setter
    def file_global_id(self, value: str):
        self.__file_global_id = value

    @property
    def progress(self) -> float:
        """
        Get the progress of the file in percentage.

        :return: The progress of the file in percentage
        """
        try:
            return self.file_info.processed_bytes / self.file_info.total_size * 100
        except:
            return 0

    @property
    def progress_str(self) -> str:
        """
        Get the progress of the file in percentage as a formatted string.

        :return: The progress of the file in percentage as a formatted string
        """
        return f"{self.progress:.2f}%"

    @property
    def speed(self) -> str:
        """
        Get the speed of the file transfer.

        :return: The speed of the file transfer
        """
        return f"{get_readable_file_size(self.file_info.speed)}/s"

    @property
    def name(self) -> str:
        """
        Get the name of the file.

        :return: The name of the file
        """
        return self.file_info.name

    @property
    def size(self) -> str:
        """
        Get the size of the file.

        :return: The size of the file
        """
        return get_readable_file_size(self.file_info.total_size)

    @property
    def eta(self) -> str:
        """
        Get the estimated time of arrival.

        :return: The estimated time of arrival
        """
        try:
            time_left = (self.file_info.total_size - self.file_info.processed_bytes) / self.file_info.speed
            return get_readable_time(time_left)
        except:
            return "-"

    @property
    def status(self) -> MirrorStatus:
        """
        Get the status of the file transfer.

        :return: The status of the file transfer
        """
        if self.file_info.task and self.file_info.task.is_waiting:
            return MirrorStatus.STATUS_QUEUED
        return MirrorStatus.STATUS_DOWNLOADING

    @property
    def processed_bytes(self) -> str:
        """
        Get the number of processed bytes.

        :return: The number of processed bytes
        """
        return get_readable_file_size(self.file_info.processed_bytes)

    @property
    def file_obj(self) -> object:
        """
        Get the file object.

        :return: The file object
        """
        return self.file_info

    @property
    def engine_status(self) -> EngineStatus:
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
            f"    file_global_id={self.file_global_id},\n"
            f"    listener={self.listener},\n"
            f"    file_info={self.file_info},\n"
            f"    upload_details={self.upload_details},\n"
            f"    message={self.message},\n"
            f"    progress={self.progress_str},\n"
            f"    speed={self.speed},\n"
            f"    name={self.name},\n"
            f"    size={self.size},\n"
            f"    eta={self.eta},\n"
            f"    status={self.status},\n"
            f"    processed_bytes={self.processed_bytes},\n"
            f"    file_obj={self.file_obj},\n"
            f"    engine_status={self.engine_status}\n"
            f")"
        )
