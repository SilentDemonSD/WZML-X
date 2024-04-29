#!/usr/bin/env python3
import asyncio
import os
from typing import Dict, Any

import aiofiles.os as aio_os
import aiohttp
from aiohttp import ClientSession

from bot import LOGGER
from bot.helper.ext_utils.bot_utils import sync_to_async

class GoFile:
    def __init__(self, dl_uploader=None, token=None):
        self.api_url = "https://api.gofile.io/"
        self.dl_uploader = dl_uploader
        self.token = token

    @staticmethod
    async def is_goapi_valid(token: str) -> bool:
        if not token:
            return False

        async with ClientSession() as session:
            async with session.get(f"https://api.gofile.io/accounts/{token.split(':')[0]}?token={token.split(':')[1]}&allDetails=true") as resp:
                if (await resp.json())["status"] == "ok":
                    return True
        return False

    async def __response_handler(self, response: Dict[str, Any]) -> Dict[str, Any]:
        api_resp = response.get("status", "")
        if api_resp == "ok":
            return response["data"]
        raise Exception(api_resp.split("-")[1] if "error-" in api_resp else "Response Status is not ok and Reason is Unknown")

    async def __get_server(self) -> Dict[str, Any]:
        async with ClientSession() as session:
            async with session.get(f"{self.api_url}servers") as resp:
                return await self.__response_handler(await resp.json())

    async def __get_account(self, check_account: bool = False) -> Dict[str, Any]:
        if not self.token:
            raise Exception()

        api_url = f"{self.api_url}accounts/{self.token.split(':')[0]}?token={self.token.split(':')[1]}&allDetails=true"
        async with ClientSession() as session:
            resp = await (await session.get(url=api_url)).json()
            if check_account:
                return resp["status"] == "ok" if True else await self.__response_handler(resp)
            else:
                return await self.__response_handler(resp)

    async def upload_folder(self, path: str, folder_id: str = None) -> str:
        if not await aio_os.isdir(path):
            raise Exception(f"Path: {path} is not a valid directory")

        folder_data = await self.create_folder((await self.__get_account())["rootFolder"], os.path.basename(path))
        await self.__set_options(content_id=folder_data["id"], option="public", value="true")

        folder_id = folder_id or folder_data["id"]
        folder_ids = {".": folder_id}
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

        async with ClientSession() as session:
            async with session.put(
                    url=f"{self.api_url}contents/createFolder",
                    data={
                        "parentFolderId": parent_folder_id,
                        "folderName": folder_name,
                        "token": self.token.split(':')[1]
                    }
            ) as resp:
                return await self.__response_handler(await resp.json())

    async def __set_options(self, content_id: str, option: str, value: str) -> Dict[str, Any]:
        if not self.token:
            raise Exception()

        if option not in ["public", "password", "description", "expire", "tags"]:
            raise Exception(f"Invalid GoFile Option Specified : {option}")

        async with ClientSession() as session:
            async with session.put(
                    url=f"{self.api_url}contents/{content_id}/update",
                    data={
                        "token": self.token.split(':')[1],
                        "attribute": option,
                        "attributevalue": value
                    }
            ) as resp:
                return await self.__response_handler(await resp.json())

    async def get_content(self, content_id: str) -> Dict[str, Any]:
        if not self.token:
            raise Exception()

        async with ClientSession() as session:
            async with session.get(url=f"{self.api_url}contents/{content_id}&token={self.token}") as resp:
                return await self.__response_handler(await resp.json())

    async def copy_content(self, content_ids: str, folder_id_dest: str) -> Dict[str, Any]:
        if not self.token:
            raise Exception()

        async with ClientSession() as session:
            async with session.put(
                    url=f"{self.api_url}contents/copy",
                    data={
                        "token": self.token.split(':')[1],
                        "contentsId": content_ids,
                        "folderId": folder_id_dest
                    }
            ) as resp:
                return await self.__response_handler(await resp.json())

    async def delete_content(self, content_id: str) -> Dict[str, Any]:
        if not self.token:
            raise Exception()

        async with ClientSession() as session:
            async with session.delete(
                    url=f"{self.api_url}contents/{content_id}",
                    data={
                        "token": self.token.split(':')[1]
                    }
            ) as resp:
                return await self.__response_handler(await resp.json())
