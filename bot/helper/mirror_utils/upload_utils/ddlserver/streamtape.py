#!/usr/bin/env python3
import os

import aiohttp
from typing import Optional
from pathlib import Path


ALLOWED_EXTS = [
    '.avi', '.mkv', '.mpg', '.mpeg', '.vob', '.wmv', '.flv', '.mp4', '.mov', '.m4v',
    '.m2v', '.divx', '.3gp', '.webm', '.ogv', '.ogg', '.ts', '.ogm'
]

class Streamtape:
    def __init__(self, dluploader, login, key):
        self.login = login
        self.key = key
        self.dluploader = dluploader
        self.base_url = 'https://api.streamtape.com'

    async def get_account_info(self):
        url = f"{self.base_url}/account/info?login={self.login}&key={self.key}"
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    if data["status"] == 200:
                        return data["result"]
        return None

    async def get_upload_url(self, folder: Optional[str] = None, sha256: Optional[str] = None, httponly: Optional[bool] = False) -> dict:
        url = f"{self.base_url}/file/ul?login={self.login}&key={self.key}"
        if folder is not None:
            url += f"&folder={folder}"
        if sha256 is not None:
            url += f"&sha256={sha256}"
        if httponly:
            url += "&httponly=true"
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    if data["status"] == 200:
                        return data["result"]
        return None

    async def upload(self, file_path: str, folder: Optional[str] = None, sha256: Optional[str] = None, httponly: Optional[bool] = False) -> dict:
        upload_info = await self.get_upload_url(folder=folder, sha256=sha256, httponly=httponly)
        if upload_info is not None:
            upload_url = upload_info["url"]
            file_extension = Path(file_path).suffix.lower()
            if file_extension in ALLOWED_EXTS:
                file_name = Path(file_path).name
                with open(file_path, "rb") as f:
                    file_data = f.read()
                async with aiohttp.ClientSession() as session:
                    async with session.post(upload_url, data={file_name: file_data}) as response:
                        if response.status == 200:
                            content_type = response.headers.get("Content-Type")
                            if content_type == "application/json":
                                data = await response.json()
                                return data
                            else:
                                return (f"Sucessfully upload")
            else:
                return (
                    f"Skipping file '{file_path}' due to disallowed extension.")
        return None

    async def upload_file(self, file_path: str, sha256: Optional[str] = None, httponly: Optional[bool] = False) -> dict:
        file_extension = Path(file_path).suffix.lower()
        if file_extension in ALLOWED_EXTS:
            file_name = Path(file_path).name
            folder_name = file_name.rsplit(".", 1)[0]
            create_folder_result = await self.create_folder(name=folder_name)
            if create_folder_result is not None:
                folder_id = create_folder_result["folderid"]
                upload_info = await self.get_upload_url(folder=folder_id, sha256=sha256, httponly=httponly)
                if upload_info is not None:
                    upload_url = upload_info["url"]
                    with open(file_path, "rb") as f:
                        file_data = f.read()
                    async with aiohttp.ClientSession() as session:
                        async with session.post(upload_url, data={file_name: file_data}) as response:
                            if response.status == 200:
                                list_folder_result = await self.list_folder(folder=folder_id)
                                return list_folder_result
        else:
            return (
                f"Skipping file '{file_path}' due to disallowed extension.")
        return None

    async def create_folder(self, name: str, parent: Optional[str] = None) -> dict:
        list_folder_result = await self.list_folder(folder=parent)
        if list_folder_result is not None:
            existing_folders = list_folder_result["folders"]
            existing_folder_names = [folder["name"]
                                     for folder in existing_folders]
            if name in existing_folder_names:
                i = 1
                new_name = f"{i} {name}"
                while new_name in existing_folder_names:
                    i += 1
                    new_name = f"{i} {name}"
                name = new_name
        url = f"{self.base_url}/file/createfolder?login={self.login}&key={self.key}&name={name}"
        if parent is not None:
            url += f"&pid={parent}"
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    if data["status"] == 200:
                        return data["result"]
        return None

    async def list_folder(self, folder: Optional[str] = None) -> dict:
        url = f"{self.base_url}/file/listfolder?login={self.login}&key={self.key}"
        if folder is not None:
            url += f"&folder={folder}"
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    if data["status"] == 200:
                        return data["result"]
        return None

    async def upload_folder(self, folder_path: str, parent_folder_id: Optional[str] = None) -> dict:
        folder_name = Path(folder_path).name
        create_folder_result = await self.create_folder(name=folder_name, parent=parent_folder_id)
        if create_folder_result is not None:
            new_folder_id = create_folder_result["folderid"]
            for entry in os.scandir(folder_path):
                if entry.is_file():
                    await self.upload(file_path=entry.path, folder=new_folder_id)
                elif entry.is_dir():
                    await self.upload_folder(folder_path=entry.path, parent_folder_id=new_folder_id)
            list_folder_result = await self.list_folder(folder=new_folder_id)
            return list_folder_result
        return None
        