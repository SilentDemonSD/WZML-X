#!/usr/bin/env python3
import asyncio
import pathlib
from typing import Any, Dict, List, Optional

import aiofiles.os
import aiohttp
import json

from bot import config_dict, LOGGER
from bot.helper.ext_utils.telegraph_helper import telegraph

ALLOWED_EXTS = [
    # ...
]

class Streamtape:
    def __init__(
        self,
        dluploader,
        login: str,
        key: str
    ):
        """
        Initialize a Streamtape instance.

        :param dluploader: The downloader instance.
        :param login: The Streamtape account login.
        :param key: The Streamtape account key.
        """
        self.dluploader = dluploader
        self.__userLogin = login
        self.__passKey = key
        self.base_url = 'https://api.streamtape.com'

    async def __get_acc_info(self) -> Optional[Dict[str, Any]]:
        """
        Get account information.

        :return: The account information or None if the request failed.
        """
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{self.base_url}/account/info?login={self.__userLogin}&key={self.__passKey}"
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    if data.get("status") == 200:
                        return data.get("result")
        return None

    async def __get_upload_url(
        self,
        folder: Optional[str] = None,
        sha256: Optional[str] = None,
        httponly: bool = False
    ) -> Optional[Dict[str, Any]]:
        """
        Get an upload URL.

        :param folder: The folder ID.
        :param sha256: The SHA256 hash.
        :param httponly: Whether to use HTTP only.
        :return: The upload URL or None if the request failed.
        """
        _url = f"{self.base_url}/file/ul?login={self.__userLogin}&key={self.__passKey}"
        if folder is not None:
            _url += f"&folder={folder}"
        if sha256 is not None:
            _url += f"&sha256={sha256}"
        if httponly:
            _url += "&httponly=true"

        async with aiohttp.ClientSession() as session:
            async with session.get(_url) as response:
                if response.status == 200:
                    data = await response.json()
                    if data.get("status") == 200:
                        return data.get("result")
        return None

    async def upload_file(
        self,
        file_path: pathlib.Path,
        folder_id: Optional[str] = None,
        sha256: Optional[str] = None,
        httponly: bool = False
    ) -> Optional[str]:
        """
        Upload a file.

        :param file_path: The file path.
        :param folder_id: The folder ID.
        :param sha256: The SHA256 hash.
        :param httponly: Whether to use HTTP only.
        :return: The StreamTape URL or None if the upload failed.
        """
        if file_path.suffix.lower() not in ALLOWED_EXTS:
            return f"Skipping '{file_path}' due to disallowed extension."

        file_name = file_path.name
        if not folder_id:
            genfolder = await self.create_folder(file_name.rsplit(".", 1)[0])
            if genfolder is None:
                return None
            folder_id = genfolder["folderid"]

        upload_info = await self.__get_upload_url(folder=folder_id, sha256=sha256, httponly=httponly)
        if upload_info is None:
            return None

        if self.dluploader.is_cancelled:
            return

        self.dluploader.last_uploaded = 0
        uploaded = await self.dluploader.upload_aiohttp(
            upload_info["url"],
            str(file_path),
            file_name,
            {}
        )

        if uploaded:
            file_id = (await self.list_folder(folder=folder_id))['files'][0]['linkid']
            await self.rename(file_id, file_name)
            return f"https://streamtape.to/v/{file_id}"
        return None

    async def create_folder(self, name: str, parent: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        Create a folder.

        :param name: The folder name.
        :param parent: The parent folder ID.
        :return: The folder information or None if the request failed.
        """
        exfolders = [
            folder["name"] for folder in (await self.list_folder(folder=parent) or {"folders": []})["folders"]
        ]

        if name in exfolders:
            i = 1
            while f"{i} {name}" in exfolders:
                i += 1
            name = f"{i} {name}"

        url = f"{self.base_url}/file/createfolder?login={self.__userLogin}&key={self.__passKey}&name={name}"
        if parent is not None:
            url += f"&pid={parent}"

        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    if data.get("status") == 200:
                        return data.get("result")
        return None

    async def rename(self, file_id: str, name: str) -> Optional[Dict[str, Any]]:
        """
        Rename a file.

        :param file_id: The file ID.
        :param name: The new file name.
        :return: The result of the request or None if the request failed.
        """
        url = f"{self.base_url}/file/rename?login={self.__userLogin}&key={self.__passKey}&file={file_id}&name={name}"

        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    if data.get("status") == 200:
                        return data.get("result")
        return None

    async def list_telegraph(
        self,
        folder_id: Optional[str] = None,
        nested: bool = False
    ) -> Optional[str]:
        """
        Generate a Telegraph page with the folder contents.

        :param folder_id: The folder ID.
        :param nested: Whether to include nested folders.
        :return: The Telegraph page URL or None if the request failed.
        """
        tg_html = ""
        contents = await self.list_folder(folder=folder_id)

        for fid in contents['folders']:
            tg_html += f"<aside>╾──────────────────────╼</aside><br><aside><b>🗂 {fid['name']}</b></aside><br><aside>╾──────────────────────╼</aside><br>"
            tg_html += await self.list_telegraph(fid['id'], True)

        tg_html += "<ol>"
        for finfo in contents['files']:
            tg_html += f"""<li> <code>{finfo['name']}</code><br>🔗 <a href="https://streamtape.to/v/{finfo['linkid']}">StreamTape URL</a><br> </li>"""
        tg_html += "</ol>"

        if nested:
            return tg_html

        tg_html = f"""<figure><img src='{config_dict["COVER_IMAGE"]}'></figure>""" + tg_html
        path = (await telegraph.create_page(title=f"StreamTape X", content=tg_html))["path"]
        return f"https://te.legra.ph/{path}"

    async def list_folder(self, folder: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        List the contents of a folder.

        :param folder: The folder ID.
        :return: The folder contents or None if the request failed.
        """
        url = f"{self.base_url}/file/listfolder?login={self.__userLogin}&key={self.__passKey}"
        if folder is not None:
            url += f"&folder={folder}"

        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    if data.get("status") == 200:
                        return data.get("result")
        return None

    async def upload_folder(
        self,
        folder_path: pathlib.Path,
        parent_folder_id: Optional[str] = None
    ) -> Optional[str]:
        """
        Upload a folder.

        :param folder_path: The folder path.
        :param parent_folder_id: The parent folder ID.
        :return: The Telegraph page URL or None if the upload failed.
        """
        folder_name = folder_path.name
        genfolder = await self.create_folder(name=folder_name, parent=parent_folder_id)

        if genfolder and (newfid := genfolder.get("folderid")):
            for entry in await aiofiles.os.scandir(folder_path):
                if entry.is_file():
                    result = await self.upload_file(entry.path, newfid)
                    if result:
                        self.dluploader.total_files += 1
                elif entry.is_dir():
                    result = await self.upload_folder(entry.path, newfid)
                    if result:
                        self.dluploader.total_folders += 1
            return await self.list_telegraph(newfid)
        return None

    async def upload(self, file_path: pathlib.Path) -> Optional[str]:
        """
        Upload a file or folder.

        :param file_path: The file or folder path.
        :return: The StreamTape URL or None if the upload failed.
        """
        stlink = None
        if await aiofiles.os.path.isfile(file_path):
            stlink = await self.upload_file(file_path)
        elif await aiofiles.os.path.isdir(file_path):
            stlink = await self.upload_folder(file_path)
        return stlink

if __name__ == "__main__":
    # Example usage:
    import asyncio

    async def main():
        streamtape = Streamtape(None, "login", "key")
        result = await streamtape.upload("path/to/file_or_folder")
        print(result)

    asyncio.run(main())
