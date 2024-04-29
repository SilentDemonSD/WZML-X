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
    async def request(
        self,
        method: Literal["PUT"],
        url: str,
        data: Union[bytes, str],
        **kwargs: Any,
    ) -> dict[str, Any]:
        ...

    @overload
    async def request(
        self,
        method: Literal["DELETE"],
        url: str,
        **kwargs: Any,
    ) -> dict[str, Any]:
        ...

    async def request(
        self,
        method: str,
        url: str,
        data: Any = None,
        headers: dict[str, str] = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """
        Sends an HTTP request to the GoFile API.

        :param method: The HTTP method to use for the request.
        :param url: The URL to send the request to.
        :param data: The data to send with the request. Only used for PUT requests.
        :param headers: The headers to include in the request. If not provided,
            default headers will be used.
        :param \**kwargs: Additional keyword arguments to pass to the `aiohttp.ClientSession.request` method.

        :return: A dictionary containing the response data and status code.
        """
        if headers is None:
            headers = {}

        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"

        async with ClientSession() as session:
            async with session.request(
                method=method,
                url=url,
                data=data,
                headers=headers,
                **kwargs,
            ) as response:
                response_data = await response.json()
                return {
                    "status_code": response.status,
                    "data": response_data,
                }

    async def get_file_info(self, file_id: str) -> dict[str, Any]:
        """
        Gets information about a file by its ID.

        :param file_id: The ID of the file to get information about.

        :return: A dictionary containing the file information.
        """
        url = f"{self.api_url}file/info/{file_id}"
        return await self.request("GET", url)

    async def upload_file(self, file_path: str) -> dict[str, Any]:
        """
        Uploads a file to the GoFile API.

        :param file_path: The path to the file to upload.

        :return: A dictionary containing the uploaded file information.
        """
        async with aiofiles.open(file_path, "rb") as file:
            data = await file.read()

        url = f"{self.api_url}file/upload"
        return await self.request("PUT", url, data=data)

    async def delete_file(self, file_id: str) -> dict[str, Any]:
        """
        Deletes a file by its ID.

        :param file_id: The ID of the file to delete.

        :return: A dictionary containing the deletion status.
        """
        url = f"{self.api_url}file/delete/{file_id}"
        return await self.request("DELETE", url)
