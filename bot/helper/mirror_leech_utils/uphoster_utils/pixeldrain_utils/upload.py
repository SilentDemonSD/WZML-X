from io import BufferedReader
from logging import getLogger
from os import path as ospath
from os import walk as oswalk
from pathlib import Path

from aiofiles.os import path as aiopath
from aiohttp import BasicAuth, ClientSession
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

    def __len__(self):
        return self.length


class PixelDrainUpload:
    def __init__(self, listener, path):
        self.listener = listener
        self._updater = None
        self._path = path
        self._is_errored = False
        self.api_url = "https://pixeldrain.com/api/"
        self.__processed_bytes = 0
        self.last_uploaded = 0
        self.total_time = 0
        self.total_files = 0
        self.total_folders = 0
        self.is_uploading = True
        self.update_interval = 3

        from bot import user_data

        user_dict = user_data.get(self.listener.user_id, {})
        self.token = user_dict.get("PIXELDRAIN_KEY") or Config.PIXELDRAIN_KEY

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
            filename=file_path, read_callback=self.__progress_callback
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
                if resp.status == 200:
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
            return f"list/{list_id}"
        else:
            return f"u/{uploaded_files[0]['id']}"

    async def upload(self):
        try:
            LOGGER.info(f"PixelDrain Uploading: {self._path}")
            self._updater = SetInterval(self.update_interval, self.progress)

            if not self.token:
                LOGGER.warning(
                    "PixelDrain API Key not provided! Upload might fail or be anonymous."
                )

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

    async def cancel_task(self):
        self.listener.is_cancelled = True
        if self.is_uploading:
            LOGGER.info(f"Cancelling PixelDrain Upload: {self.listener.name}")
            await self.listener.on_upload_error("PixelDrain upload has been cancelled!")
