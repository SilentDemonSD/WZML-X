class DirectDownloadLinkException(Exception):
    """No method found for extracting direct download link from the HTTP link"""

    pass


class NotSupportedExtractionArchive(Exception):
    """The archive format being used for extraction is not supported"""
    
    pass


class RssShutdownException(Exception):
    """This exception should be raised when shutdown is called to stop the monitor"""

    pass


class TgLinkException(Exception):
    """No access granted for this chat"""

    pass
