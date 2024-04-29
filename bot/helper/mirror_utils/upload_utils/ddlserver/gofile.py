import asyncio
import os
from typing import Any, Dict, List, Literal, Union

import aiofiles.os as aio_os
import aiohttp
from aiohttp import ClientSession
from contextlib import asynccontextmanager
from typing_extensions import overload

class GoFileHTTP:
    def __init__(self, token: str = None):
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
    ) -> Dict[str, Any]:
        ...

    async def request(
        self,
        method: str,
        url: str,
        json: Union[None, dict] = None,
        **kwargs: Any,
    ) -> Union[Dict[str, Any], None]:
        async with ClientSession(timeout=aiohttp.ClientTimeout(total=10)) as session:
            kwargs["timeout"] = session.timeout
            async with session.request(
                method,
                url,
                json=json,
                **kwargs,
            ) as resp:
                if resp.status == 200:
                    return await resp.json()
                elif resp.status == 401:
                    raise Exception("Invalid token")
                elif resp.status == 404:
                    raise Exception("Resource not found")
                else:
                    raise Exception(f"Request failed with status code {resp.status}")

class GoFileAPI:
    def __init__(self, dl_uploader: Any = None, token: str = None):
        self.http = GoFileHTTP(token=token)
        self.dl_uploader = dl_uploader

