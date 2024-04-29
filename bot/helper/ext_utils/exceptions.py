class DownloadError(Exception):
    """Base class for all download-related errors"""
    pass

class DirectDownloadLinkError(DownloadError):
    """Raised when there is a problem extracting the direct download link"""
    pass

class UnsupportedExtractionArchiveError(DownloadError):
    """Raised when the archive format is not supported"""
    pass
