class DirectDownloadLinkException(Exception):
    """Raised when a method for extracting a direct download link from an HTTP link cannot be found.

    This exception is used to indicate that there was an issue with extracting a direct download link
    from an HTTP link, typically because the method for extracting the link was not found.
    """
    pass

class NotSupportedExtractionArchive(Exception):
    """Raised when the archive format being extracted is not supported.

    This exception is used to indicate that the archive format being extracted is not supported
    by the current system or module.
    """
    pass

class RssShutdownException(Exception):
    """Raised when shutdown is called to stop the monitor.

    This exception is used to indicate that the shutdown method was called to stop the monitor.
    """
    pass

class TgLinkException(Exception):
    """Raised when no access is granted for a chat in Telegram.

    This exception is used to indicate that there was an issue with accessing a chat in Telegram,
    typically because no access was granted for that chat.
    """
    pass
