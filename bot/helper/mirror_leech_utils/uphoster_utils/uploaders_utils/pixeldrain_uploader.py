from logging import getLogger
from os import path as ospath
from os import walk as oswalk

from aiofiles.os import path as aiopath
from aiohttp import BasicAuth, ClientSession
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from bot.helper.ext_utils.bot_utils import sync_to_async

from ..base import BaseUpload
from ..common import ProgressFileReader

LOGGER = getLogger(__name__)


class PixelDrainUpload(BaseUpload):
    SERVICE_NAME = "PixelDrain"
    _TOKEN_KEY = "PIXELDRAIN_KEY"
    _CONFIG_KEY = "PIXELDRAIN_KEY"

    def __init__(self, listener, path, folder_name=""):
        super().__init__(listener, path, folder_name)
        self.api_url = "https://pixeldrain.com/api/"

    async def __resp_handler(self, response):
        if response.get("success") or "id" in response:
            return response.get("id")
        elif response.get("value") == "file_not_found":
            raise Exception("File not found.")
        else:
            raise Exception(f"Error: {response.get('message', 'Unknown Error')}")

    @retry(
        wait=wait_exponential(multiplier=2, min=4, max=8),
        stop=stop_after_attempt(3),
        retry=retry_if_exception_type(Exception),
    )
    async def upload_aiohttp(self, url, file_path, file_name):
        auth = BasicAuth("", self.token) if self.token else None
        with ProgressFileReader(
            filename=file_path, read_callback=self._progress_callback
        ) as file:
            async with ClientSession(auth=auth) as session:
                async with session.put(f"{url}{file_name}", data=file) as resp:
                    if resp.status in [200, 201]:
                        return await self.__resp_handler(
                            await resp.json(content_type=None)
                        )
                    else:
                        raise Exception(f"HTTP {resp.status}: {await resp.text()}")
        return None

    async def create_list(self, title, files):
        if not self.token:
            LOGGER.warning(
                "Pixeldrain List creation requires an API Key. Skipping list creation."
            )
            return None
        data = {"title": title, "files": files, "anonymous": False}
        auth = BasicAuth("", self.token)
        async with ClientSession(auth=auth) as session:
            async with session.post(f"{self.api_url}list", json=data) as resp:
                if resp.status in [200, 201]:
                    res = await resp.json(content_type=None)
                    if res.get("success"):
                        return res.get("id")
                raise Exception(f"List Creation Failed: {await resp.text()}")

    async def upload_file(self, path: str):
        if self.listener.is_cancelled:
            return None
        file_name = ospath.basename(path).replace(" ", ".")
        url = f"{self.api_url}file/"
        return await self.upload_aiohttp(url, path, file_name)

    async def _upload_dir(self, input_directory):
        folder_name = ospath.basename(input_directory)
        uploaded_files = []
        for root, _, files in await sync_to_async(oswalk, input_directory):
            for file in files:
                if self.listener.is_cancelled:
                    break
                file_path = ospath.join(root, file)
                file_id = await self.upload_file(file_path)
                if file_id:
                    self.total_files += 1
                    uploaded_files.append(
                        {
                            "id": file_id,
                            "description": str(
                                ospath.relpath(file_path, input_directory)
                            ),
                        }
                    )
        if not uploaded_files:
            raise Exception("No files uploaded from directory.")
        list_id = await self.create_list(folder_name, uploaded_files)
        if list_id:
            return f"l/{list_id}"
        else:
            return f"u/{uploaded_files[0]['id']}"

    async def _validate_token(self):
        if not self.token:
            LOGGER.warning(
                "PixelDrain API Key not provided! Upload might fail or be anonymous."
            )

    async def _upload_process(self):
        link = ""
        if await aiopath.isfile(self._path):
            file_id = await self.upload_file(self._path)
            if file_id:
                link = f"https://pixeldrain.com/u/{file_id}"
                mime_type = "File"
                self.total_files = 1
            else:
                raise ValueError("Failed to upload file to PixelDrain")
        elif await aiopath.isdir(self._path):
            if not self.token:
                raise ValueError(
                    "PixelDrain API Key is required for folder (List) uploads."
                )
            result_path = await self._upload_dir(self._path)
            if result_path:
                link = f"https://pixeldrain.com/{result_path}"
                mime_type = "Folder"
                self.total_folders = 1
            else:
                raise ValueError("Failed to upload folder to PixelDrain")
        else:
            raise ValueError("Invalid file path!")

        if self.listener.is_cancelled:
            return

        LOGGER.info(f"Uploaded To PixelDrain: {self.listener.name}")
        await self.listener.on_upload_complete(
            link,
            self.total_files,
            self.total_folders,
            mime_type,
            dir_id="",
        )
