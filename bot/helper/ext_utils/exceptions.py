class DownloadLinkException(Exception):
    """Base class for exceptions related to download link errors."""
    pass

class DirectDownloadLinkException(DownloadLinkException):
    """Raised when a method for extracting a direct download link from an HTTP link cannot be found.

    This exception is used to indicate that there was an issue with extracting a direct download link
    from an HTTP link, typically because the method for extracting the link was not found.
    """
    pass

class NotSupportedExtractionArchive(DownloadLinkException):

