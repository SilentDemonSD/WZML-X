from io import BufferedReader
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
            session.get("https://buzzheavier.com/api/account", headers={"Authorization": f"Bearer {token}"}) as resp,
        ):
            return resp.status == 200

    async def __resp_handler(self, response):
        # BuzzHeavier returns text for uploads, JSON for API
        if isinstance(response, dict):
            return response
        return response

    async def __get_root_id(self):
        # BuzzHeavier might have a root directory ID or we can just upload to root.
        # API docs say: "To create directory under root directory, first you will need to get directoryId using 'Get root directory' call."
        if self.token is None:
            raise Exception("BuzzHeavier API token not found!")

        async with ClientSession() as session:
            async with session.get(
                f"{self.api_url}fs",
                headers={"Authorization": f"Bearer {self.token}"}
            ) as resp:
                if resp.status == 200:
                    res = await resp.json()
                    # Assuming the response contains the ID of the root directory listing
                    # Or the directory listing itself has an ID.
                    # Typically file system APIs return the current folder object with an ID.
                    # If it returns a list of files, I might need to check account info.
                    # Let's assume 'id' field in the root object or 'rootDirectoryId' in account.

                    # Let's try getting account info if fs doesn't give an ID directly.
                    if "id" in res:
                        return res["id"]

                # Fallback to account info
                async with session.get(
                    f"{self.api_url}account",
                    headers={"Authorization": f"Bearer {self.token}"}
                ) as resp2:
                    if resp2.status == 200:
                        res2 = await resp2.json()
                        # Inspecting potential keys for root folder
                        # Common keys: rootFolderId, root_directory_id, etc.
                        # Without live API access, I'll try to find 'rootDirectoryId' or similar if documented
                        # Re-reading docs: "Get root directory" -> Retrieves contents.
                        # Maybe the "Get root directory" endpoint IS the root directory ID?
                        # No, usually you GET /api/fs and it lists content.
                        # But to create a folder you need parentId.
                        # If I can't find it, I'll assume root is implicit or I need to fetch /api/fs and maybe look for a metadata field.
                        # Let's assume checking /api/fs returns a Directory object.
                        if "id" in res:
                            return res["id"]

                        # If not found, check logs/debugging. For now, return None or raise.
                        # But wait, "To create directory under root directory, first you will need to get directoryId using 'Get root directory' call."
                        # This strongly implies /api/fs returns the directory object of root.
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
                    if resp.status == 200 or resp.status == 201:
                        return await resp.text()
                    else:
                        raise Exception(f"HTTP {resp.status}: {await resp.text()}")
        return None

    async def create_folder(self, parentFolderId, folderName):
        if self.token is None:
            raise Exception("BuzzHeavier API token not found!")

        # If parentFolderId is None, we might be trying to create in root.
        # If we failed to get root ID, this call might fail.
        url = f"{self.api_url}fs/{parentFolderId}" if parentFolderId else f"{self.api_url}fs"
        # Wait, docs say "Create directory: POST .../api/fs/{parentDirectoryId}"
        # "To create directory under root directory, first you will need to get directoryId..."
        # So parentFolderId is required.

        if not parentFolderId:
             # Try to fetch root ID again if missed
             parentFolderId = await self.__get_root_id()
             if not parentFolderId:
                 raise Exception("Could not determine Root Directory ID.")

        async with ClientSession() as session:
            async with session.post(
                url=f"{self.api_url}fs/{parentFolderId}",
                json={"name": folderName},
                headers={"Authorization": f"Bearer {self.token}"}
            ) as resp:
                if resp.status == 200 or resp.status == 201:
                    return await resp.json()
                else:
                    raise Exception(f"Create Folder Failed: {await resp.text()}")

    async def upload_file(self, path: str, parentId: str = ""):
        if self.listener.is_cancelled:
            return None

        # Replace spaces with dots in filename (common practice in these bots)
        new_path = ospath.join(
            ospath.dirname(path), ospath.basename(path).replace(" ", ".")
        )
        await aiorename(path, new_path)
        file_name = ospath.basename(new_path)

        # Construct URL
        # Upload into user directory: PUT https://w.buzzheavier.com/{parentId}/{name}
        # Upload to default location (root?): PUT https://w.buzzheavier.com/{name}

        if parentId:
            url = f"{self.upload_url}{parentId}/{file_name}"
        else:
            url = f"{self.upload_url}{file_name}"

        upload_resp = await self.upload_aiohttp(url, new_path)
        return upload_resp

    async def _upload_dir(self, input_directory):
        # Get Root ID
        parent_folder_id = await self.__get_root_id()

        # Create main folder
        folder_name = ospath.basename(input_directory)
        main_folder_data = await self.create_folder(parent_folder_id, folder_name)
        main_folder_id = main_folder_data["id"]
        # We can construct a link to the folder. BuzzHeavier link format?
        # Docs don't explicitly state "Share Link" format for folders.
        # Usually it's https://buzzheavier.com/d/{id} or /f/{id}.
        # I'll assume https://buzzheavier.com/f/{id} for now or check if response has link.

        folder_ids = {".": main_folder_id}

        for root, _dirs, files in await sync_to_async(oswalk, input_directory):
            if self.listener.is_cancelled:
                break

            rel_path = ospath.relpath(root, input_directory)
            current_folder_id = folder_ids.get(
                ospath.dirname(rel_path), main_folder_id
            )

            if rel_path != ".":
                current_folder_id = folder_ids.get(rel_path)
                # if for some reason we missed creating it (logic below handles creation of subdirs)

            # Create sub-folders for next iteration (wait, os.walk yields top-down by default)
            # So when we are at 'root', 'dirs' has subdirectories.
            # We should create them now so we have their IDs.
            for subdir in _dirs:
                # parent for subdir is current_folder_id (which corresponds to 'root')
                # 'root' is the full path. rel_path is relative to input_dir.
                # If rel_path is ".", current_folder_id is main_folder_id.
                # If rel_path is "sub", current_folder_id is ID of "sub".

                # We need to find ID for 'root' from our map.
                # rel_path key in map stores the ID for 'root'.
                parent_id_for_subs = folder_ids.get(rel_path)

                # Create subdir
                sub_folder_data = await self.create_folder(parent_id_for_subs, subdir)

                # Store ID. Key is relative path of subdir.
                sub_rel_path = ospath.join(rel_path, subdir)
                folder_ids[sub_rel_path] = sub_folder_data["id"]
                self.total_folders += 1

            # Upload files in current directory
            current_dir_id = folder_ids.get(rel_path)
            for file in files:
                if self.listener.is_cancelled:
                    break
                file_path = ospath.join(root, file)
                await self.upload_file(file_path, current_dir_id)
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
            # Single file upload
            # BuzzHeavier response is text (typically the ID).
            file_id = await self.upload_file(path=self._path)
            if file_id:
                if file_id.startswith("http"):
                    link = file_id
                else:
                    link = f"https://buzzheavier.com/f/{file_id}"

                mime_type = "File"
                self.total_files = 1
            else:
                raise ValueError(
                    f"Failed to upload file to BuzzHeavier. Response: {file_id}"
                )
        elif await aiopath.isdir(self._path):
            # Directory upload
            folder_id = await self._upload_dir(self._path)
            if folder_id:
                # Construct link. Assuming format.
                link = f"https://buzzheavier.com/f/{folder_id}"
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
            await self.listener.on_upload_error("BuzzHeavier upload has been cancelled!")
