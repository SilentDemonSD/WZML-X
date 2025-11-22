from io import BufferedReader
from json import loads as json_loads
from logging import getLogger
from os import path as ospath
from os import walk as oswalk
from pathlib import Path

from aiofiles.os import path as aiopath
from aiofiles.os import rename as aiorename
from aiohttp import ClientSession
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


class BuzzHeavierUpload:
    def __init__(self, listener, path):
        self.listener = listener
        self._updater = None
        self._path = path
        self._is_errored = False
        self.api_url = "https://buzzheavier.com/api/"
        self.upload_url = "https://w.buzzheavier.com/"
        self.__processed_bytes = 0
        self.last_uploaded = 0
        self.total_time = 0
        self.total_files = 0
        self.total_folders = 0
        self.is_uploading = True
        self.update_interval = 3

        from bot import user_data

        user_dict = user_data.get(self.listener.user_id, {})
        self.token = user_dict.get("BUZZHEAVIER_TOKEN") or Config.BUZZHEAVIER_API
        self.folder_id = user_dict.get("BUZZHEAVIER_FOLDER_ID") or ""

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
    async def is_buzzapi(token):
        if not token:
            return False
        async with (
            ClientSession() as session,
            session.get(
                "https://buzzheavier.com/api/account",
                headers={"Authorization": f"Bearer {token}"},
            ) as resp,
        ):
            return resp.status == 200

    async def __resp_handler(self, response):
        try:
            if isinstance(response, dict):
                if "id" in response:
                    return response["id"]
                if (
                    "data" in response
                    and isinstance(response["data"], dict)
                    and "id" in response["data"]
                ):
                    return response["data"]["id"]
            elif isinstance(response, str):
                try:
                    # Try to parse JSON if it's a string
                    json_resp = json_loads(response)
                    if isinstance(json_resp, dict):
                        if "id" in json_resp:
                            return json_resp["id"]
                        if (
                            "data" in json_resp
                            and isinstance(json_resp["data"], dict)
                            and "id" in json_resp["data"]
                        ):
                            return json_resp["data"]["id"]
                except Exception:
                    pass
                # If not JSON or parsing failed, return cleaned string
                return response.strip().strip('"')
        except Exception as e:
            LOGGER.error(f"Response handling error: {e}")
        return response

    async def __get_root_id(self):
        if self.token is None:
            raise Exception("BuzzHeavier API token not found!")

        async with ClientSession() as session:
            # Try getting account info first as it is more likely to contain root ID reference
            async with session.get(
                f"{self.api_url}account",
                headers={"Authorization": f"Bearer {self.token}"},
            ) as resp:
                if resp.status == 200:
                    try:
                        res = await resp.json()
                        if "rootDirectoryId" in res:
                            return res["rootDirectoryId"]
                        # Sometimes it might be in data
                        if (
                            "data" in res
                            and isinstance(res["data"], dict)
                            and "rootDirectoryId" in res["data"]
                        ):
                            return res["data"]["rootDirectoryId"]
                    except Exception:
                        pass

            # Fallback to FS
            async with session.get(
                f"{self.api_url}fs", headers={"Authorization": f"Bearer {self.token}"}
            ) as resp:
                if resp.status == 200:
                    try:
                        res = await resp.json()
                        if "id" in res:
                            return res["id"]
                        if (
                            "data" in res
                            and isinstance(res["data"], dict)
                            and "id" in res["data"]
                        ):
                            return res["data"]["id"]
                    except Exception:
                        pass
        return None

    @retry(
        wait=wait_exponential(multiplier=2, min=4, max=8),
        stop=stop_after_attempt(3),
        retry=retry_if_exception_type(Exception),
    )
    async def upload_aiohttp(self, url, file_path):
        headers = {"Authorization": f"Bearer {self.token}"}
        with ProgressFileReader(
            filename=file_path, read_callback=self.__progress_callback
        ) as file:
            async with ClientSession() as session:
                async with session.put(url, data=file, headers=headers) as resp:
                    if resp.status in [200, 201]:
                        return await self.__resp_handler(await resp.text())
                    else:
                        raise Exception(f"HTTP {resp.status}: {await resp.text()}")
        return None

    async def create_folder(self, parentFolderId, folderName):
        if self.token is None:
            raise Exception("BuzzHeavier API token not found!")

        if not parentFolderId:
            parentFolderId = await self.__get_root_id()
            if not parentFolderId:
                raise Exception("Could not determine Root Directory ID.")

        url = f"{self.api_url}fs/{parentFolderId}"
        async with ClientSession() as session:
            async with session.post(
                url=url,
                json={"name": folderName},
                headers={"Authorization": f"Bearer {self.token}"},
            ) as resp:
                if resp.status in [200, 201]:
                    return await resp.json()
                else:
                    raise Exception(f"Create Folder Failed: {await resp.text()}")

    async def upload_file(self, path: str, parentId: str = ""):
        if self.listener.is_cancelled:
            return None

        # Replace spaces with dots in filename
        new_path = ospath.join(
            ospath.dirname(path), ospath.basename(path).replace(" ", ".")
        )
        await aiorename(path, new_path)
        file_name = ospath.basename(new_path)

        if not parentId:
            # Default to root if no parentId provided
            parentId = await self.__get_root_id()

        if parentId:
            url = f"{self.upload_url}{parentId}/{file_name}"
        else:
            # Fallback to uploading to default location (root usually) if we still don't have an ID?
            # The docs say: https://w.buzzheavier.com/{name} Uploads a file to default location
            url = f"{self.upload_url}{file_name}"

        return await self.upload_aiohttp(url, new_path)

    async def _upload_dir(self, input_directory):
        parent_folder_id = self.folder_id or await self.__get_root_id()
        if not parent_folder_id:
            raise Exception("Failed to retrieve Root Directory ID for folder upload")

        folder_name = ospath.basename(input_directory)
        main_folder_data = await self.create_folder(parent_folder_id, folder_name)

        # Handle response for folder creation
        if "id" in main_folder_data:
            main_folder_id = main_folder_data["id"]
        elif (
            "data" in main_folder_data
            and isinstance(main_folder_data["data"], dict)
            and "id" in main_folder_data["data"]
        ):
            main_folder_id = main_folder_data["data"]["id"]
        else:
            raise Exception(
                f"Could not retrieve folder ID from response: {main_folder_data}"
            )

        folder_ids = {".": main_folder_id}

        for root, _dirs, files in await sync_to_async(oswalk, input_directory):
            if self.listener.is_cancelled:
                break

            rel_path = ospath.relpath(root, input_directory)
            current_folder_id = folder_ids.get(ospath.dirname(rel_path), main_folder_id)

            if rel_path != ".":
                current_folder_id = folder_ids.get(rel_path)

            for subdir in _dirs:
                sub_folder_data = await self.create_folder(current_folder_id, subdir)
                # Handle response for subfolder creation
                if "id" in sub_folder_data:
                    sub_folder_id = sub_folder_data["id"]
                elif (
                    "data" in sub_folder_data
                    and isinstance(sub_folder_data["data"], dict)
                    and "id" in sub_folder_data["data"]
                ):
                    sub_folder_id = sub_folder_data["data"]["id"]
                else:
                    raise Exception(
                        f"Could not retrieve subfolder ID from response: {sub_folder_data}"
                    )

                sub_rel_path = ospath.join(rel_path, subdir)
                folder_ids[sub_rel_path] = sub_folder_id
                self.total_folders += 1

            for file in files:
                if self.listener.is_cancelled:
                    break
                file_path = ospath.join(root, file)
                await self.upload_file(file_path, current_folder_id)
                self.total_files += 1

        return main_folder_id

    async def upload(self):
        try:
            LOGGER.info(f"BuzzHeavier Uploading: {self._path}")
            self._updater = SetInterval(self.update_interval, self.progress)

            if not self.token:
                raise ValueError(
                    "BuzzHeavier API token not configured! Please set your BuzzHeavier token in user settings or configure a global token."
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
        if not await self.is_buzzapi(self.token):
            raise Exception("Invalid BuzzHeavier API Key, please check your token!")

        if await aiopath.isfile(self._path):
            file_id = await self.upload_file(path=self._path, parentId=self.folder_id)
            if file_id:
                file_id = str(file_id).strip()
                # Ensure file_id is not a JSON string or invalid
                if "{" in file_id or "}" in file_id:
                    raise ValueError(f"Invalid file ID received: {file_id}")

                if file_id.startswith("http"):
                    link = file_id
                else:
                    link = f"https://buzzheavier.com/{file_id}"

                mime_type = "File"
                self.total_files = 1
            else:
                raise ValueError("Failed to upload file to BuzzHeavier")
        elif await aiopath.isdir(self._path):
            folder_id = await self._upload_dir(self._path)
            if folder_id:
                link = f"https://buzzheavier.com/{folder_id}"
                mime_type = "Folder"
            else:
                raise ValueError("Failed to upload folder to BuzzHeavier")
        else:
            raise ValueError("Invalid file path!")

        if self.listener.is_cancelled:
            return

        LOGGER.info(f"Uploaded To BuzzHeavier: {self.listener.name}")
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
            LOGGER.info(f"Cancelling BuzzHeavier Upload: {self.listener.name}")
            await self.listener.on_upload_error(
                "BuzzHeavier upload has been cancelled!"
            )
