import asyncio
import os
from typing import Any, Dict, List, Literal, Union

import aiofiles.os as aio_os
import aiohttp
from aiohttp import ClientSession
from contextlib import asynccontextmanager
from typing_extensions import overload

class GoFileHTTP:
    """
    A class for making requests to the GoFile API.
    """
    def __init__(self, token: str = None):
        """
        Initializes a new `GoFileHTTP` instance.

        :param token: The API token to use for authentication.
        """
        self.api_url = "https://api.gofile.io/"
        self.token = token

    @overload
    async def request(
        self,
        method: Literal["GET"],
        url: str,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        ...

    @overload
    async def request(
        self,
        method: Literal["PUT"],
        url: str,
        json: Any,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        ...

    @overload
    async def request(
        self,
        method: Literal["DELETE"],
        url: str,
        json: Any,
        **kwargs: Any,

