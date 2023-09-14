#!/usr/bin/env python3
from os import path as ospath, walk
from aiofiles.os import path as aiopath, rename as aiorename
from asyncio import sleep
from aiohttp import ClientSession

from bot import LOGGER
from bot.helper.ext_utils.bot_utils import sync_to_async

class Gofile:
    def __init__(self, dluploader=None, token=None):
        self.api_url = "https://api.gofile.io/"
        self.dluploader = dluploader
        self.token = token

    @staticmethod
    async def is_goapi(token):
        if token is None:
            return
        async with ClientSession() as session:
            async with session.get(f"https://api.gofile.io/getAccountDetails?token={token}&allDetails=true") as resp:
                if (await resp.json())["status"] == "ok":
                    return True
        return False

    async def __resp_handler(self, response):
        api_resp = response.get("status", "")
        if api_resp == "ok":
            return response["data"]
        raise Exception(api_resp.split("-")[1] if "error-" in api_resp else "Response Status is not ok and Reason is Unknown")

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
        
    async def upload_folder(self, path, folderId=None):
        if not await aiopath.isdir(path):
            raise Exception(f"Path: {path} is not a valid directory")
            
        folder_data = await self.create_folder((await self.__getAccount())["rootFolder"], ospath.basename(path))
        await self.__setOptions(contentId=folder_data["id"], option="public", value="true")
    
        folderId = folderId or folder_data["id"]
        folder_ids = {".": folderId}
        for root, _, files in await sync_to_async(walk, path):
            rel_path = ospath.relpath(root, path)
            parentFolderId = folder_ids.get(ospath.dirname(rel_path), folderId)
            folder_name = ospath.basename(rel_path)
            currFolderId = (await self.create_folder(parentFolderId, folder_name))["id"]
            await self.__setOptions(contentId=currFolderId, option="public", value="true")
            folder_ids[rel_path] = currFolderId

            for file in files:
                file_path = ospath.join(root, file)
                up = await self.upload_file(file_path, currFolderId)
                
        return folder_data["code"]

    async def upload_file(self, path: str, folderId: str = "", description: str = "", password: str = "", tags: str = "", expire: str = ""):
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
        new_path = ospath.join(ospath.dirname(path), ospath.basename(path).replace(' ', '.'))
        await aiorename(path, new_path)
        self.dluploader.last_uploaded = 0
        upload_file = await self.dluploader.upload_aiohttp(f"https://{server}.gofile.io/uploadFile", new_path, "file", req_dict)
        return await self.__resp_handler(upload_file)
        
    async def upload(self, file_path):
        if not await self.is_goapi(self.token):
            raise Exception("Invalid Gofile API Key, Recheck your account !!")
        if await aiopath.isfile(file_path):
            if (gCode := await self.upload_file(path=file_path)) and gCode.get("downloadPage", False):
                return gCode['downloadPage']
        elif await aiopath.isdir(file_path):
            if (gCode := await self.upload_folder(path=file_path)):
                return f"https://gofile.io/d/{gCode}"
        if self.dluploader.is_cancelled:
            return
        raise Exception("Failed to upload file/folder to Gofile API, Retry or Try after sometimes...")

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
