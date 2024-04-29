#!/usr/bin/env python3
# This is a Python script that defines a class called DDLStatus.

from bot.helper.ext_utils.bot_utils import MirrorStatus, get_readable_file_size, get_readable_time
# Importing the necessary modules and functions from the bot_utils file.
# MirrorStatus is an enumeration that represents the status of a mirror.
# get_readable_file_size is a function that converts a file size in bytes to a human-readable format.
# get_readable_time is a function that converts a number of seconds to a human-readable time format.

class DDLStatus:
    # The DDLStatus class is defined here.
    def __init__(self, obj, size, message, gid, upload_details):
        # The constructor for the DDLStatus class.
        # It takes five arguments: obj, size, message, gid, and upload_details.
        # obj is an object that contains information about the file being uploaded.
        # size is the size of the file in bytes.
        # message is a message associated with the upload.
        # gid is a globally unique identifier for the upload.
        # upload_details is additional details about the upload.
        self.__obj = obj
        self.__size = size
        self.__gid = gid
        self.upload_details = upload_details
        self.message = message

    def processed_bytes(self):
        # A method that returns the number of bytes that have been processed
        # during the upload in a human-readable format.
        return get_readable_file_size(self.__obj.processed_bytes)

    def size(self):
        # A method that returns the size of the file in a human-readable format.
        return get_readable_file_size(self.__size)

    def status(self):
        # A method that returns the status of the upload.
        return MirrorStatus.STATUS_UPLOADING

    def name(self):
        # A method that returns the name of the file being uploaded.
        return self.__obj.name

    def progress(self):
        # A method that returns the progress of the upload as a percentage.
        try:
            progress_raw = self.__obj.processed_bytes / self.__size * 100
        except:
            progress_raw = 0
        return f'{round(progress_raw, 2)}%'

    def speed(self):
        # A method that returns the current upload speed in a human-readable format.
        return f'{get_readable_file_size(self.__obj.speed)}/s'

    def eta(self):
        # A method that returns the estimated time of arrival for the upload.
        try:
            seconds = (self.__size - self.__obj.processed_bytes) / self.__obj.speed
            return get_readable_time(seconds)
        except:
            return '-'

    def gid(self) -> str:
        # A method that returns the globally unique identifier for the upload.
        return self.__gid

    def download(self):
        # A method that returns the object that contains information about the file being uploaded.
        return self.__obj

    def eng(self):
        # A method that returns the engine associated with the upload.
        return self.__obj.engine
