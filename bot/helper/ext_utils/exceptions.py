class DownloadLinkError(Exception):
    """
    This is the base class for exceptions related to download link errors.
    When a more specific download link error occurs, this class should be used as the base class.
    """
    pass

class DirectDownloadLinkNotFoundError(DownloadLinkError):
    """
    This class is raised when a method for extracting a direct download link from an HTTP link cannot be found.
    It inherits from DownloadLinkError, indicating that it is a specific type of download link error.
    """
    pass

class UnsupportedArchiveFormatError(Exception):
    """
    This class is raised when the archive format is not supported by the application.
    It does not inherit from DownloadLinkError, as it is not a type of download link error.
    """
    pass
