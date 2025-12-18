from io import BufferedReader
from json import JSONDecodeError
from logging import getLogger
from os import path as ospath
from os import walk as oswalk
from pathlib import Path
from random import choice

from aiofiles.os import path as aiopath
from aiofiles.os import rename as aiorename
from aiohttp import ClientSession
from aiohttp.client_exceptions import ContentTypeError
from tenacity import (
    RetryError,
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from bot.core.config_manager import Config
from bot.helper.ext_utils.bot_utils import SetInterval, sync_to_async

LOGGER = getLogger(__name__)


class ProgressFileReader(BufferedReader):
    def __init__(self, filename, read_callback=None):
        super().__init__(open(filename, "rb"))
        self.__read_callback = read_callback
        self.length = Path(filename).stat().st_size

    def read(self, size=None):
        size = size or (self.length - self.tell())
        if self.__read_callback:
            self.__read_callback(self.tell())
        return super().read(size)


class GoFileUpload:
    def __init__(self, listener, path):
        self.listener = listener
        self._updater = None
        self._path = path
        self._is_errored = False
        self.api_url = "https://api.gofile.io/"
        self.__processed_bytes = 0
        self.last_uploaded = 0
        self.total_time = 0
        self.total_files = 0
        self.total_folders = 0
        self.is_uploading = True
        self.update_interval = 3

        # Get user-specific token or fall back to global config
        from bot import user_data

        user_dict = user_data.get(self.listener.user_id, {})
        self.token = user_dict.get("GOFILE_TOKEN") or Config.GOFILE_API
        self.folder_id = (
            user_dict.get("GOFILE_FOLDER_ID") or Config.GOFILE_FOLDER_ID or ""
        )

    @property
    def speed(self):
        try:
            return self.__processed_bytes / self.total_time
        except Exception:
            return 0

    @property
    def processed_bytes(self):
        return self.__processed_bytes

    def __progress_callback(self, current):
        chunk_size = current - self.last_uploaded
        self.last_uploaded = current
        self.__processed_bytes += chunk_size

    async def progress(self):
        self.total_time += self.update_interval

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
                json={
                    "attribute": option,
                    "attributeValue": value,
                },
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
            filename=file_path, read_callback=self.__progress_callback
        ) as file:
            data[req_file] = file
            async with ClientSession() as session:
                async with session.post(url, data=data) as resp:
                    if resp.status == 200:
                        try:
                            return await resp.json()
                        except ContentTypeError:
                            return {
                                "status": "ok",
                                "data": {"downloadPage": "Uploaded"},
                            }
                        except JSONDecodeError:
                            return {
                                "status": "ok",
                                "data": {"downloadPage": "Uploaded"},
                            }
                    else:
                        raise Exception(f"HTTP {resp.status}: {await resp.text()}")
        return None

    async def create_folder(self, parentFolderId, folderName):
        if self.token is None:
            raise Exception("GoFile API token not found!")

        headers = {"Authorization": f"Bearer {self.token}"}
        async with (
            ClientSession() as session,
            session.post(
                url=f"{self.api_url}contents/createfolder",
                json={
                    "parentFolderId": parentFolderId,
                    "folderName": folderName,
                },
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

        # Replace spaces with dots in filename
        new_path = ospath.join(
            ospath.dirname(path), ospath.basename(path).replace(" ", ".")
        )
        await aiorename(path, new_path)

        upload_file = await self.upload_aiohttp(
            f"https://{server}.gofile.io/uploadfile",
            new_path,
            "file",
            req_dict,
        )
        return await self.__resp_handler(upload_file)

    async def _upload_dir(self, input_directory, parent_folder_id=None):
        if parent_folder_id is None:
            # Use user's folder_id if specified, otherwise create in root
            if self.folder_id:
                # Upload to user's specified folder
                parent_folder_id = self.folder_id
                main_folder_code = self.folder_id
            else:
                # Create main folder in root
                account_data = await self.__getAccount()
                folder_data = await self.create_folder(
                    account_data["rootFolder"], ospath.basename(input_directory)
                )
                await self.__setOptions(
                    contentId=folder_data["folderId"], option="public", value="true"
                )
                parent_folder_id = folder_data["folderId"]
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

            # Create folders for current directory
            if rel_path != ".":
                folder_name = ospath.basename(rel_path)
                curr_folder_data = await self.create_folder(
                    current_folder_id, folder_name
                )
                await self.__setOptions(
                    contentId=curr_folder_data["folderId"],
                    option="public",
                    value="true",
                )
                folder_ids[rel_path] = curr_folder_data["folderId"]
                current_folder_id = curr_folder_data["folderId"]
                self.total_folders += 1

            # Upload files in current directory
            for file in files:
                if self.listener.is_cancelled:
                    break

                file_path = ospath.join(root, file)
                await self.upload_file(file_path, current_folder_id)
                self.total_files += 1

        return main_folder_code

    async def upload(self):
        try:
            LOGGER.info(f"GoFile Uploading: {self._path}")
            self._updater = SetInterval(self.update_interval, self.progress)

            if not self.token:
                raise ValueError(
                    "GoFile API token not configured! Please set your GoFile token in user settings or configure a global token."
                )

            # Run the async process directly
            await self._upload_process()

        except Exception as err:
            if isinstance(err, RetryError):
                LOGGER.info(f"Total Attempts: {err.last_attempt.attempt_number}")
                err = err.last_attempt.exception()
            err = str(err).replace(">", "").replace("<", "")
            LOGGER.error(err)
            await self.listener.on_upload_error(err)
            self._is_errored = True
        finally:
            if self._updater:
                self._updater.cancel()
            if (
                self.listener.is_cancelled and not self._is_errored
            ) or self._is_errored:
                return

    async def _upload_process(self):
        if not await self.is_goapi(self.token):
            raise Exception("Invalid GoFile API Key, please check your token!")

        if await aiopath.isfile(self._path):
            # Single file upload
            file_result = await self.upload_file(
                path=self._path, folderId=self.folder_id
            )
            if file_result and file_result.get("downloadPage"):
                link = file_result["downloadPage"]
                mime_type = "File"
                self.total_files = 1
            else:
                raise ValueError("Failed to upload file to GoFile")
        elif await aiopath.isdir(self._path):
            # Directory upload
            folder_code = await self._upload_dir(self._path)
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

    async def cancel_task(self):
        self.listener.is_cancelled = True
        if self.is_uploading:
            LOGGER.info(f"Cancelling GoFile Upload: {self.listener.name}")
            await self.listener.on_upload_error("GoFile upload has been cancelled!")
