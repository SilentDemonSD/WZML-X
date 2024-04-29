class DownloadLinkError(Exception):
    """Base class for exceptions related to download link errors."""
    pass

class DirectDownloadLinkNotFoundError(DownloadLinkError):
    """Raised when a method for extracting a direct download link from an HTTP link cannot be found."""
    pass

class UnsupportedArchiveFormatError(Exception):
    """Raised when the archive format is not supported by the application."""
    pass
