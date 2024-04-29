import os
from typing import Dict, Any, Union, Optional

import aiofiles.os
import aiohttp
from aiohttp import ClientSession
from bot.helper.ext_utils.bot_utils import sync_to_async

class Gofile:
    def __init__(self, dluploader: Any = None, token: Optional[str] = None):
        self.api_url = "https://api.gofile.io/"
        self.dluploader = dluploader
        self.token = token
        self._session: Optional[ClientSession] = None

    async def __aenter__(self):
        self._session = ClientSession()
        return self

    async def __aexit__(self, exc_type, exc, tb):
        if self._session:
            await self._session.close()

    @staticmethod
    async def is_goapi(token: str) -> bool:
        """Check if the token is a valid GoAPI token."""
        if not token:
            return False

        async with ClientSession() as session:
            async with session.get(f"https://api.gofile.io/getAccountDetails?token={token}&allDetails=true") as resp:
                return (await resp.json())["status"] == "ok"

    async def __resp_handler(self, response: Dict[str, Any]) -> Any:
        api_resp = response.get("status", "")
        if api_resp == "ok":
            return response["data"]
        raise Exception(api_resp.split("-")[1] if "error-" in api_resp else "Response Status is not ok and Reason is Unknown")

    async def __get_server(self) -> str:
        async with ClientSession() as session:
            async with session.get(f"{self.api_url}getServer") as resp:
                return await self.__resp_handler(await resp.json())

    async def __get_account(self, check_account: bool = False) -> Union[bool, Dict[str, Any]]:
        if not self.token:
            raise Exception()

        api_url = f"{self.api_url}getAccountDetails?token={self.token}&allDetails=true"
        async with ClientSession() as session:
            resp = await (await session.get(url=api_url)).json()
            if check_account:
                return resp["status"] == "ok" if True else await self.__resp_handler(resp)
            else:
                return await self.__resp_handler(resp)

    async def upload_folder(self, path: str, folder_id: Optional[str] = None) -> str:
        """Upload a folder to GoFile."""
        if not os.path.isdir(path):
            raise Exception(f"Path: {path} is not a valid directory")

        folder_data = await self.create_folder((await self.__get_account())["rootFolder"], os.path.basename(path))
        await self.__set_options(content_id=folder_data["id"], option="public", value="true")

        folder_ids = {".": folder_data["id"]}
        for root, _, files in await sync_to_async(os.walk, path):
            rel_path = os.path.relpath(root, path)
            parent_folder_id = folder_ids.get(os.path.dirname(rel_path), folder_id)
            folder_name = os.path.basename(rel_path)
            curr_folder_id = (await self.create_folder(parent_folder_id, folder_name))["id"]
            await self.__set_options(content_id=curr_folder_id, option="public", value="true")
            folder_ids[rel_path] = curr_folder_id

            for file in files:
                file_path = os.path.join(root, file)
                await self.upload_file(file_path, curr_folder_id)

        return folder_data["code"]

    async def upload_file(self, path: str, folder_id: str = "", description: str = "", password: str = "", tags: str = "", expire: str = ""):
        """Upload a file to GoFile."""
        if not os.path.isfile(path):
            raise Exception(f"Path: {path} is not a valid file")

        server = (await self.__get_server())["server"]
        token = self.token if self.token else ""
        req_dict = {}
        if token:
            req_dict["token"] = token
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

        new_path = os.path.join(os.path.dirname(path), os.path.basename(path).replace(' ', '.'))
        await aiofiles.os.rename(path, new_path)
        self.dluploader.last_uploaded = 0

        upload_file = await self.dluploader.upload_aiohttp(
            f"https://{server}.gofile.io/uploadFile", new_path, "file", req_dict
        )
        return await self.__resp_handler(upload_file)

    async def upload(self, file_path: str) -> Optional[str]:
        """Upload a file or folder to GoFile."""
        if not self.token or not (await self.is_goapi(self.token)):
            raise Exception("Invalid Gofile API Key, Recheck your account !!")

        if os.path.isfile(file_path):
            result = await self.upload_file(path=file_path)
            return result.get("downloadPage", False)
        elif os.path.isdir(file_path):
            result = await self.upload_folder(path=file_path)
            return f"https://gofile.io/d/{result}"
        if self.dluploader.is_cancelled:
            return
        raise Exception("Failed to upload file/folder to Gofile API, Retry or Try after sometimes...")

    async def create_folder(self, parent_folder_id: str, folder_name: str) -> Dict[str, Any]:
        """Create a new folder in GoFile."""
        if not self.token:
            raise Exception()

        async with ClientSession() as session:
            async with session.put(
                url=f"{self.api_url}createFolder",
                data={
                    "parentFolderId": parent_folder_id,
                    "folderName": folder_name,
                    "token": self.token
                }
            ) as resp:
                return await self.__resp_handler(await resp.json())

    async def __set_options(self, content_id: str, option: str, value: str):
        """Set options for a content in GoFile."""
        if not self.token:
            raise Exception()

        if option not in ["public", "password", "description", "expire", "tags"]:
            raise Exception(f"Invalid GoFile Option Specified : {option}")

        async with ClientSession() as session:
            async with session.put(
                url=f"{self.api_url}setOption",
                data={
                    "token": self.token,
                    "contentId": content_id,
                    "option": option,
                    "value": value
                }
            ) as resp:
                return await self.__resp_handler(await resp.json())

    async def get_content(self, content_id: str):
        """Get content details from GoFile."""
        if not self.token:
            raise Exception()

        async with ClientSession() as session:
            async with session.get(
                url=f"{self.api_url}getContent?contentId={content_id}&token={self.token}"
            ) as resp:
                return await self.__resp_handler(await resp.json())

    async def copy_content(self, content_ids: str, folder_id_dest: str):
        """Copy content to a new folder in GoFile."""
        if not self.token:
            raise Exception()

        async with ClientSession() as session:
            async with session.put(
                url=f"{self.api_url}copyContent",
                data={
                    "token": self.token,
                    "contentsId": content_ids,
                    "folderIdDest": folder_id_dest
                }
            ) as resp:
                return await self.__resp_handler(await resp.json())

    async def delete_content(self, content_id: str):
        """Delete content from GoFile."""
        if not self.token:
            raise Exception()

        async with ClientSession() as session:
            async with session.delete(
                url=f"{self.api_url}deleteContent",
                data={
                    "contentId": content_id,
                    "token": self.token
                }
            ) as resp:
                return await self.__resp_handler(await resp.json())
