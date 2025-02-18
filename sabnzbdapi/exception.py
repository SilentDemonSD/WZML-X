from httpx import RequestError, DecodingError
from json import JSONDecodeError


class APIError(Exception):
    """Base error for all exceptions from this Client."""


class APIConnectionError(RequestError, APIError):
    """Base class for all communications errors including HTTP errors."""

class APIResponseError(APIError, JSONDecodeError):
    """Base class for all errors from the API response."""


class LoginFailed(DecodingError, APIConnectionError, JSONDecodeError):
    """This can technically be raised with any request since log in may be attempted for
    any request and could fail."""


class NotLoggedIn(APIConnectionError):
    """Raised when login is not successful."""
