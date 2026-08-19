from logging import getLogger
from os import path as ospath
from os import walk as oswalk

from aiofiles.os import path as aiopath
from aiohttp import ClientSession
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from bot.helper.ext_utils.bot_utils import sync_to_async

from ..base import BaseUpload
from ..common import ProgressFileReader, extract_id

LOGGER = getLogger(__name__)


class BuzzHeavierUpload(BaseUpload):
    SERVICE_NAME = "BuzzHeavier"
    _TOKEN_KEY = "BUZZHEAVIER_TOKEN"
    _CONFIG_KEY = "BUZZHEAVIER_API"

    def __init__(self, listener, path, folder_name=""):
        super().__init__(listener, path, folder_name)
        self.api_url = "https://buzzheavier.com/api/"
        self.upload_url = "https://w.buzzheavier.com/"
        from bot import user_data

        user_dict = user_data.get(self.listener.user_id, {})
        self.folder_id = user_dict.get("BUZZHEAVIER_FOLDER_ID") or ""

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

    async def __get_root_id(self):
        if self.token is None:
            raise Exception("BuzzHeavier API token not found!")
        async with ClientSession() as session:
            async with session.get(
                f"{self.api_url}account",
                headers={"Authorization": f"Bearer {self.token}"},
            ) as resp:
                if resp.status == 200:
                    try:
                        res = await resp.json()
                        if "rootDirectoryId" in res:
                            return res["rootDirectoryId"]
                        if (
                            "data" in res
                            and isinstance(res["data"], dict)
                            and "rootDirectoryId" in res["data"]
                        ):
                            return res["data"]["rootDirectoryId"]
                    except Exception:
                        pass
            async with session.get(
                f"{self.api_url}fs",
                headers={"Authorization": f"Bearer {self.token}"},
            ) as resp:
                if resp.status == 200:
                    try:
                        return extract_id(await resp.json())
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
            filename=file_path, read_callback=self._progress_callback
        ) as file:
            async with ClientSession() as session:
                async with session.put(url, data=file, headers=headers) as resp:
                    if resp.status in [200, 201]:
                        return extract_id(await resp.text())
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
        file_name = ospath.basename(path).replace(" ", ".")
        if not parentId:
            parentId = await self.__get_root_id()
        if parentId:
            url = f"{self.upload_url}{parentId}/{file_name}"
        else:
            url = f"{self.upload_url}{file_name}"
        return await self.upload_aiohttp(url, path)

    async def _upload_dir(self, input_directory):
        parent_folder_id = self.folder_id or await self.__get_root_id()
        if not parent_folder_id:
            raise Exception("Failed to retrieve Root Directory ID for folder upload")
        folder_name = ospath.basename(input_directory)
        main_folder_data = await self.create_folder(parent_folder_id, folder_name)
        main_folder_id = extract_id(main_folder_data)
        if not main_folder_id or not str(main_folder_id).strip():
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
                sub_folder_id = extract_id(sub_folder_data)
                if not sub_folder_id or not str(sub_folder_id).strip():
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

    async def _validate_token(self):
        if not self.token:
            raise ValueError(
                "BuzzHeavier API token not configured! Please set your BuzzHeavier token in user settings or configure a global token."
            )

    async def _upload_process(self):
        if not await self.is_buzzapi(self.token):
            raise Exception("Invalid BuzzHeavier API Key, please check your token!")

        if await aiopath.isfile(self._path):
            file_id = await self.upload_file(path=self._path, parentId=self.folder_id)
            if file_id:
                file_id = str(file_id).strip()
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
