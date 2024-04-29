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
    ) -> dict[str, Any]:
        ...

    @overload
    async def request(
        self,
        method: Literal["PUT"],
        url: str,
        json_data: Any,
        **kwargs: Any,
    ) -> dict[str, Any]:
        ...

    @overload
    async def request(
        self,
        method: Literal["DELETE"],
        url: str,
        json_data: Any,
        **kwargs: Any,
    ) -> None:
        ...

    async def request(self, method: str, url: str, **kwargs) -> Union[dict[str, Any], None]:
        headers = {"Authorization": f"Bearer {self.token}"} if self.token else {}
        async with ClientSession() as session:
            async with session.request(
                method=method,
                url=f"{self.api_url}{url}",
                headers=headers,
                **kwargs,
            ) as response:
                if method in ["PUT", "DELETE"]:
                    return None
                response_data = await response.json()
                return response_data
