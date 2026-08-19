from json import JSONDecodeError
from logging import getLogger
from os import path as ospath
from os import walk as oswalk
from random import choice

from aiofiles.os import path as aiopath
from aiohttp import ClientSession, FormData
from aiohttp.client_exceptions import ContentTypeError
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from bot.core.config_manager import Config
from bot.helper.ext_utils.bot_utils import sync_to_async

from ..base import BaseUpload
from ..common import ProgressFileReader

LOGGER = getLogger(__name__)


class GoFileUpload(BaseUpload):
    SERVICE_NAME = "GoFile"
    _TOKEN_KEY = "GOFILE_TOKEN"
    _CONFIG_KEY = "GOFILE_API"

    def __init__(self, listener, path, folder_name=""):
        super().__init__(listener, path, folder_name)
        self.api_url = "https://api.gofile.io/"
        from bot import user_data

        user_dict = user_data.get(self.listener.user_id, {})
        self.folder_id = (
            user_dict.get("GOFILE_FOLDER_ID") or Config.GOFILE_FOLDER_ID or ""
        )
        self.auto_create = (
            user_dict.get("GOFILE_AUTO_CREATE_FOLDER")
            if "GOFILE_AUTO_CREATE_FOLDER" in user_dict
            else Config.GOFILE_AUTO_CREATE_FOLDER
        )

    @staticmethod
    async def is_goapi(token):
        if token is None:
            return False
        headers = {"Authorization": f"Bearer {token}"}
        async with (
            ClientSession() as session,
            session.get(
                "https://api.gofile.io/accounts/website", headers=headers
            ) as resp,
        ):
            res = await resp.json()
            return res.get("status") == "ok"

    async def __resp_handler(self, response):
        if (api_resp := response.get("status", "")) == "ok":
            return response["data"]
        raise Exception(
            api_resp.split("-")[1]
            if "error-" in api_resp
            else "Response Status is not ok and Reason is Unknown"
        )

    async def __getServer(self):
        async with ClientSession() as session:
            async with session.get(f"{self.api_url}servers") as resp:
                return await self.__resp_handler(await resp.json())

    async def __getAccount(self, check_account=False):
        if self.token is None:
            raise Exception("GoFile API token not found!")
        headers = {"Authorization": f"Bearer {self.token}"}
        async with (
            ClientSession() as session,
            session.get(f"{self.api_url}accounts/website", headers=headers) as resp,
        ):
            res = await resp.json()
            if check_account:
                return res["status"] == "ok"
            return await self.__resp_handler(res)

    async def __setOptions(self, contentId, option, value):
        if self.token is None:
            raise Exception("GoFile API token not found!")
        if option not in [
            "name",
            "description",
            "tags",
            "public",
            "expiry",
            "password",
        ]:
            raise Exception(f"Invalid GoFile Option Specified: {option}")
        headers = {"Authorization": f"Bearer {self.token}"}
        async with (
            ClientSession() as session,
            session.put(
                url=f"{self.api_url}contents/{contentId}/update",
                json={"attribute": option, "attributeValue": value},
                headers=headers,
            ) as resp,
        ):
            return await self.__resp_handler(await resp.json())

    @retry(
        wait=wait_exponential(multiplier=2, min=4, max=8),
        stop=stop_after_attempt(3),
        retry=retry_if_exception_type(Exception),
    )
    async def upload_aiohttp(self, url, file_path, req_file, data):
        with ProgressFileReader(
            filename=file_path, read_callback=self._progress_callback
        ) as file:
            form = FormData()
            for key, value in data.items():
                form.add_field(key, value)
            form.add_field(
                req_file, file, filename=ospath.basename(file_path).replace(" ", ".")
            )
            async with ClientSession() as session:
                async with session.post(url, data=form) as resp:
                    if resp.status == 200:
                        try:
                            return await resp.json()
                        except (ContentTypeError, JSONDecodeError):
                            return {
                                "status": "ok",
                                "data": {"downloadPage": "Uploaded"},
                            }
                    else:
                        raise Exception(f"HTTP {resp.status}: {await resp.text()}")
        return None

    async def create_folder(self, parentFolderId, folderName=None):
        if self.token is None:
            raise Exception("GoFile API token not found!")
        headers = {"Authorization": f"Bearer {self.token}"}
        body = {"parentFolderId": parentFolderId}
        if folderName:
            body["folderName"] = folderName
        async with (
            ClientSession() as session,
            session.post(
                url=f"{self.api_url}contents/createfolder",
                json=body,
                headers=headers,
            ) as resp,
        ):
            return await self.__resp_handler(await resp.json())

    async def upload_file(
        self,
        path: str,
        folderId: str = "",
        description: str = "",
        password: str = "",
        tags: str = "",
        expire: str = "",
    ):
        if password and len(password) < 4:
            raise ValueError("Password Length must be greater than 4")
        server = choice((await self.__getServer())["servers"])["name"]
        req_dict = {}
        if self.token:
            req_dict["token"] = self.token
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
        if self.listener.is_cancelled:
            return None
        upload_file = await self.upload_aiohttp(
            f"https://{server}.gofile.io/uploadfile",
            path,
            "file",
            req_dict,
        )
        return await self.__resp_handler(upload_file)

    async def _upload_dir(
        self, input_directory, parent_folder_id=None, root_folder_id=None
    ):
        if parent_folder_id is None:
            if self.folder_id:
                parent_folder_id = self.folder_id
                main_folder_code = self.folder_id
            else:
                if root_folder_id is None:
                    account_data = await self.__getAccount()
                    root_folder_id = account_data["rootFolder"]
                folder_data = await self.create_folder(
                    root_folder_id, self.folder_name or ospath.basename(input_directory)
                )
                parent_folder_id = folder_data.get("id") or folder_data["folderId"]
                await self.__setOptions(
                    contentId=parent_folder_id,
                    option="public",
                    value="true",
                )
                main_folder_code = folder_data["code"]
        else:
            main_folder_code = None

        folder_ids = {".": parent_folder_id}
        for root, _dirs, files in await sync_to_async(oswalk, input_directory):
            if self.listener.is_cancelled:
                break
            rel_path = ospath.relpath(root, input_directory)
            current_folder_id = folder_ids.get(
                ospath.dirname(rel_path), parent_folder_id
            )
            if rel_path != ".":
                folder_name = ospath.basename(rel_path)
                curr_folder_data = await self.create_folder(
                    current_folder_id, folder_name
                )
                curr_folder_id = (
                    curr_folder_data.get("id") or curr_folder_data["folderId"]
                )
                await self.__setOptions(
                    contentId=curr_folder_id,
                    option="public",
                    value="true",
                )
                folder_ids[rel_path] = curr_folder_id
                current_folder_id = curr_folder_id
                self.total_folders += 1
            for file in files:
                if self.listener.is_cancelled:
                    break
                file_path = ospath.join(root, file)
                await self.upload_file(file_path, current_folder_id)
                self.total_files += 1
        return main_folder_code

    async def _validate_token(self):
        if not self.token:
            raise ValueError(
                "GoFile API token not configured! Please set your GoFile token in user settings or configure a global token."
            )

    async def _upload_process(self):
        try:
            account_data = await self.__getAccount()
        except Exception as e:
            raise Exception(f"GoFile Account Error: {e}") from e

        if await aiopath.isfile(self._path):
            folder_id = self.folder_id
            folder_code = ""
            if not folder_id and self.auto_create:
                folder_data = await self.create_folder(
                    account_data["rootFolder"], self.folder_name or None
                )
                folder_id = folder_data.get("id") or folder_data["folderId"]
                await self.__setOptions(
                    contentId=folder_id,
                    option="public",
                    value="true",
                )
                folder_code = folder_data.get("code", "")
            else:
                folder_id = folder_id or account_data["rootFolder"]
            file_result = await self.upload_file(path=self._path, folderId=folder_id)
            if file_result and file_result.get("downloadPage"):
                link = (
                    f"https://gofile.io/d/{folder_code}"
                    if folder_code
                    else file_result["downloadPage"]
                )
                mime_type = "File"
                self.total_files = 1
            else:
                raise ValueError("Failed to upload file to GoFile")
        elif await aiopath.isdir(self._path):
            folder_code = await self._upload_dir(
                self._path, root_folder_id=account_data["rootFolder"]
            )
            if folder_code:
                link = f"https://gofile.io/d/{folder_code}"
                mime_type = "Folder"
            else:
                raise ValueError("Failed to upload folder to GoFile")
        else:
            raise ValueError("Invalid file path!")

        if self.listener.is_cancelled:
            return

        LOGGER.info(f"Uploaded To GoFile: {self.listener.name}")
        await self.listener.on_upload_complete(
            link,
            self.total_files,
            self.total_folders,
            mime_type,
            dir_id="",
        )
