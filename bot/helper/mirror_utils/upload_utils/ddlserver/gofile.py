#!/usr/bin/env python3
from os import path as ospath, walk
from aiofiles.os import path as aiopath
from asyncio import sleep
from aiohttp import ClientSession

from bot import LOGGER
from bot.helper.ext_utils.bot_utils import is_gofile_token, sync_to_async

class Gofile:
    def __init__(self, dluploader=None, token=None):
        self.api_url = "https://api.gofile.io/"
        self.dluploader = dluploader
        self.token = token
        if self.token is not None:
            is_gofile_token(url=self.api_url, token=self.token)

    async def __resp_handler(self, response):
        api_status = response["status"]
        if api_status == "ok":
            return response["data"]
        else:
            if "error-" in response["status"]:
                error = response["status"].split("-")[1]
            else:
                error = "Response Status is not ok and reason is unknown"
            raise Exception(error)

    async def __getServer(self):
        async with ClientSession() as session:
            async with session.get(f"{self.api_url}getServer") as resp:
                return await self.__resp_handler(await resp.json())

    async def __getAccount(self, check_account=False):
        if self.token is None:
            raise Exception()
        
        api_url = f"{self.api_url}getAccountDetails?token={self.token}&allDetails=true"
        async with ClientSession() as session:
            resp = await (await session.get(url=api_url)).json()
            if check_account:
                return resp["status"] == "ok" if True else await self.__resp_handler(resp)
            else:
                return await self.__resp_handler(resp)

    async def upload_folder(self, path: str, folderId: str = "", delay: int = 2):
        if not await aiopath.isdir(path):
            raise Exception(f"{path} is not a valid directory")

        folder_name = ospath.basename(path)
        if not folderId:
            account_data = await self.__getAccount()
            rtfid = account_data["rootFolder"]
            folder_data = await self.create_folder(rtfid, folder_name)
            folderId = folder_data["id"]

        uploaded = None
        folder_ids = {".": folderId}
        for root, dirs, files in await sync_to_async(walk, path):
            relative_path = ospath.relpath(root, path)
            if relative_path == ".":
                current_folder_id = folderId
            else:
                parent_folder_id = folder_ids.get(ospath.dirname(relative_path), folderId)
                folder_name = ospath.basename(relative_path)
                folder_data = await self.create_folder(parent_folder_id, folder_name)
                current_folder_id = folder_data["id"]
                folder_ids[relative_path] = current_folder_id
            self.dluploader.total_folders += 1
            
            for file in files:
                file_path = ospath.join(root, file)
                udt = await self.upload_file(file_path, current_folder_id)
                self.dluploader.total_files += 1
                if uploaded is None:
                    uploaded = udt
                await sleep(delay)
        return uploaded

    async def upload_file(self, file: str, folderId: str = "", description: str = "", password: str = "", tags: str = "", expire: str = ""):
        if password and len(password) < 4:
            raise ValueError("Password Length must be greater than 4")

        server = (await self.__getServer())["server"]
        token = self.token if self.token else ""
        req_dict = {}
        if token:
            req_dict["token"] = token
        if folderId:
            req_dict["folderId"] = folderId
        if description:
            req_dict["description"] = description
        if password:
            req_dict["password"] = password
        if tags:
            req_dict["tags"] = tags
        if expire:
            req_dict["expire"] = expire
        
        if self.dluploader.is_cancelled:
            return
        self.dluploader.last_uploaded = 0
        upload_file = await self.dluploader.upload_aiohttp(f"https://{server}.gofile.io/uploadFile", file, req_dict)
        return await self.__resp_handler(upload_file)
        
    async def upload(self, file_path):
            return
        if await aiopath.isfile(file_path):
            cmd = await self.upload_file(file=file_path)
        elif await aiopath.isdir(file_path):
            cmd = await self.upload_folder(path=file_path)
            if cmd and 'parentFolder' in cmd:
                await self.__setOptions(contentId=cmd['parentFolder'], option="public", value="true")
        if cmd and 'downloadPage' in cmd:
            return cmd['downloadPage'] 
        raise Exception("Failed to upload file/folder")

    async def create_folder(self, parentFolderId, folderName):
        if self.token is None:
            raise Exception()
        
        async with ClientSession() as session:
            async with session.put(url=f"{self.api_url}createFolder",
                data={
                        "parentFolderId": parentFolderId,
                        "folderName": folderName,
                        "token": self.token
                    }
                ) as resp:
                return await self.__resp_handler(await resp.json())

    async def __setOptions(self, contentId, option, value):
        if self.token is None:
            raise Exception()
        
        if not option in ["public", "password", "description", "expire", "tags"]:
            raise Exception(f"Invalid GoFile Option Specified : {option}")
        async with ClientSession() as session:
            async with session.put(url=f"{self.api_url}setOption",
                data={
                        "token": self.token,
                        "contentId": contentId,
                        "option": option,
                        "value": value
                    }
                ) as resp:
                return await self.__resp_handler(await resp.json())

    async def get_content(self, contentId):
        if self.token is None:
            raise Exception()
        
        async with ClientSession() as session:
            async with session.get(url=f"{self.api_url}getContent?contentId={contentId}&token={self.token}") as resp:
                return await self.__resp_handler(await resp.json())

    async def copy_content(self, contentsId, folderIdDest):
        if self.token is None:
            raise Exception()
        async with ClientSession() as session:
            async with session.put(url=f"{self.api_url}copyContent",
                    data={
                        "token": self.token,
                        "contentsId": contentsId,
                        "folderIdDest": folderIdDest
                    }
                ) as resp:
                return await self.__resp_handler(await resp.json())

    async def delete_content(self, contentId):
        if self.token is None:
            raise Exception()
        async with ClientSession() as session:
            async with session.delete(url=f"{self.api_url}deleteContent",
                    data={
                        "contentId": contentId,
                        "token": self.token
                    }
                ) as resp:
                return await self.__resp_handler(await resp.json())
