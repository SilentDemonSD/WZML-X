#!/usr/bin/env python3

import bot.helper.ext_utils.bot_utils as bot_utils  # Importing the bot_utils module
from bot import LOGGER  # Importing the logger from bot module
from typing import Any, Dict, Final, NamedTuple, Optional

class QueueStatus:
    """
    Represents the status of a queue.

    Attributes:
        name (str): The name of the queue.
        gid (int): The group id of the queue.
        listener (object): The listener object associated with the queue.
        status (str): The status of the queue ('dl' for download, 'up' for upload).
        upload_details (dict): The upload details associated with the queue.
        message (object): The message object associated with the queue.
    """

    name: Final = 'name'
    gid: Final = 'gid'
    status: Final = 'status'
    upload_details: Final = 'upload_details'
    message: Final = 'message'
    total_size: Final = 'total_size'

    def __init__(self, name: str, gid: int, listener, status: str):
        self.name_: str = name
        self.gid_: int = gid
        self.listener_: Any = listener
        self.upload_details_: Dict[str, Any] = listener.upload_details
        self.status_: str = status
        self.message_: Any = listener.message
        self.total_size_: int = sum(item.size for item in listener.queue)

    @property
    def name(self) -> str:
        """Return the name of the queue."""
        return self.name_

    @property
    def size(self) -> int:
        """Return the size of the queue."""
        return self.total_size_

    @property
    def gid(self) -> int:
        """Return the group id of the queue."""
        return self.gid_

    @property
    def status(self) -> str:
        """Return the status of the queue."""
        return self.status_

    @property
    def processed_bytes(self) -> int:
        """Always return 0 for processed bytes."""
        return 0

    @property
    def progress(self) -> str:

