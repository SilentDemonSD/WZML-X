import asyncio
import os
from typing import Any, Dict, List, Literal, Union

import aiofiles
import aiohttp
from aiohttp import ClientSession
from contextlib import asynccontextmanager
from typing_extensions import overload

class GoFileHTTP:
    """
    A class for making requests to the GoFile API.

    This class provides a convenient way to interact with the GoFile API by abstracting
    away the details of making HTTP requests and handling responses. It supports GET,
    PUT, and DELETE methods and automatically includes the API token in the request
    headers for authentication.

    Attributes:
        api_url (str): The base URL for the GoFile API.
        token (str): The API token to use for authentication.
    """

    def __init__(self, token: str = None):
        """
        Initializes a new `GoFileHTTP` instance.

        :param token: The API token to use for authentication. If not provided,
            requests will be made without authentication.
        """
        self.api_url = "https://api.gofile.io/"
        self.token = token

    @overload
    async def request(
        self,
        method: Literal["GET"],
        url: str,
        **kwargs: Any,
    ) -> dict[str, Any]:
        ...

    @overload

