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
        async with ClientSession() as session:
            async with session.request(
                method,
                url,
                json=json,
                **kwargs,
            ) as resp:
                if resp.status == 200:
                    return await resp.json()
                return None

class GoFileAPI:
    def __init__(self, dl_uploader: Any = None, token: str = None):
        self.http = GoFileHTTP(token=token)
        self.dl_uploader = dl_uploader

    @staticmethod
    async def is_goapi_valid(token: str) -> bool:
        if not token:
            return False

        response = await http.request(
            "GET",
            f"{token.split(':')[0]}?token={token.split(':')[1]}&allDetails=true",
        )
        data = await response.json()
        return data["status"] == "ok"

    async def __response_handler(self, response: Dict[str, Any]) -> Dict[str, Any]:
        api_resp = response.get("status", "")
        if api_resp == "ok":
            return response["data"]
        raise Exception(api_resp.split("-")[1] if "error-" in api_resp else "Response Status is not ok and Reason is Unknown")

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        pass

    async def __get_server(self) -> Dict[str, Any]:
        response = await self.http.request("GET", self.http.api_url + "servers")
        return await self.__response_handler(response)

    async def __get_account(self, check_account: bool = False) -> Dict[str, Any]:
        if not self.token:
            raise Exception()

        api_url = f"{self.http.api_url}accounts/{self.token.split(':')[0]}?token={self.token.split(':')[1]}&allDetails=true"
        response = await self.http.request("GET", api_url)
        data = await response.json()
        if check_account:
            return data["status"] == "ok" if True else await self.__response_handler(data)
        else:
            return await self.__response_handler(data)

    async def upload_folder(self, path: str, folder_id: str = None) -> str:
        if not await aio_os.isdir(path):
            raise Exception(f"Path: {path} is not a valid directory")

        folder_data = await self.create_folder((await self.__get_account())["rootFolder"], os.path.basename(path))
        await self.__set_options(content_id=folder_data["id"], option="public", value="true")

        folder_ids = {".": folder_data["id"]}
        for root, _, files in await asyncio.to_thread(os.walk, path):
            rel_path = os.path.relpath(root, path)
            parent_folder_id = folder_ids.get(os.path.dirname(rel_path), folder_id)
            folder_name = os.path.basename(rel_path)
            curr_folder_id = await self.create_folder(parent_folder_id, folder_name)["id"]
            await self.__set_options(content_id=curr_folder_id, option="public", value="true")
            folder_ids[rel_path] = curr_folder_id

            for file in files:
                file_path = os.path.join(root, file)
                upload_result = await self.upload_file(file_path, curr_folder_id)

        return folder_data["code"]

    async def upload_file(self, path: str, folder_id: str = "", description: str = "", password: str = "", tags: str = "", expire: str = "") -> Dict[str, Any]:
        if password and len(password) < 4:
            raise ValueError("Password Length must be greater than 4")

        server = (await self.__get_server())["servers"][0]["name"]
        token = self.token if self.token else ""
        req_dict = {}
        if token:
            req_dict["token"] = token.split(':')[1]
        if folder_id:
            req_dict["folderId"] = folder_id
        if description:
            req_dict["description"] = description
        if password:
            req_dict["password"] = password
        if tags:
            req_dict["tags"] = tags
        if expire:
            req_dict["expire"] = expire

        if self.dl_uploader.is_cancelled:
            return

        new_path = os.path.join(os.path.dirname(path), os.path.basename(path).replace(' ', '.'))
        await aio_os.rename(path, new_path)
        self.dl_uploader.last_uploaded = 0

        upload_file = await self.dl_uploader.upload_aiohttp(
            f"https://{server}.gofile.io/contents/uploadfile", new_path, "file", req_dict
        )
        return await self.__response_handler(upload_file)

    async def upload(self, file_path: str) -> str:
        if not await aio_os.isfile(file_path):
            raise Exception("File not found")

        if not await self.is_goapi_valid(self.token):
            raise Exception("Invalid Gofile API Key, Recheck your account !!")

        if await aio_os.isfile(file_path):
            result = await self.upload_file(path=file_path)
            if result.get("downloadPage", False):
                return result['downloadPage']
        elif await aio_os.isdir(file_path):
            result = await self.upload_folder(path=file_path)
            return f"https://gofile.io/d/{result}"
        if self.dl_uploader.is_cancelled:
            return
        raise Exception("Failed to upload file/folder to Gofile API, Retry or Try after sometimes...")

    async def create_folder(self, parent_folder_id: str, folder_name: str) -> Dict[str, Any]:
        if not self.token:
            raise Exception()

        response = await self.http.request(
            "PUT",
            self.http.api_url + "contents/createFolder",
            json={
                "parentFolderId": parent_folder_id,
                "folderName": folder_name,
                "token": self.token.split(':')[1]
            },
        )
        return await self.__response_handler(response)

    async def __set_options(self, content_id: str, option: Literal["public", "password", "description", "expire", "tags"], value: str) -> Dict[str, Any]:
        if not self.token:
            raise Exception()

        response = await self.http.request(
            "PUT",
            self.http.api_url + f"contents/{content_id}/update",
            json={
                "token": self.token.split(':')[1],
                "attribute": option,
                "attributevalue": value
            },
        )
        return await self.__response_handler(response)

    async def get_content(self, content_id: str) -> Dict[str, Any]:
        if not self.token:
            raise Exception()

        response = await self.http.request("GET", self.http.api_url + f"contents/{content_id}&token={self.token}")
        return await self.__response_handler(response)

    async def copy_content(self, content_ids: List[str], folder_id_dest: str) -> Dict[str, Any]:
        if not self.token:
            raise Exception()

        response = await self.http.request(
            "PUT",
            self.http.api_url + "contents/copy",
            json={
                "token": self.token.split(':')[1],
                "contentsId": content_ids,
                "folderId": folder_id_dest
            },
        )
        return await self.__response_handler(response)

    async def delete_content(self, content_id: str) -> Dict[str, Any]:
        if not self.token:
            raise Exception()

        response = await self.http.request("DELETE", self.http.api_url + f"contents/{content_id}", json={
            "token": self.token.split(':')[1]
        })
        return await self.__response_handler(response)
