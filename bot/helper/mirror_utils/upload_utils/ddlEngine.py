import asyncio
import io
import pathlib
import traceback
import json
import re
import aiofiles.os as aiopath
import time
import aiohttp
from typing import Dict, Any, Union, Optional, Callable, List, Tuple
from tenacity import retry, wait_exponential, stop_after_attempt, retry_if_exception_type

class ProgressFileReader(io.BufferedReader):
    """
    A custom BufferedReader that allows tracking of the number of bytes read.
    """
    def __init__(self, filename: str, read_callback: Optional[Callable[[int], None]] = None):
        super().__init__(open(filename, "rb"))
        self.__read_callback = read_callback
        self.length = pathlib.Path(filename).stat().st_size

    def read(self, size: Optional[int] = None) -> Union[bytes, MemoryView]:
        """
        Reads up to `size` bytes of data from the file.
        If `read_callback` is provided, it will be called with the current file position.
        """
        size = size or (self.length - self.tell())
        if self.__read_callback:
            self.__read_callback(self.tell())
        return super().read(size)

class DDLUploader:
    """
    A class for uploading files to various DDL servers.
    """
    def __init__(self, listener, name, path, speed_limit: int = 0):
        """
        Initializes a new instance of the DDLUploader class.
        """
        self.name = name
        self.__processed_bytes = 0
        self.last_uploaded = 0
        self.__listener = listener
        self.__path = path
        self.__start_time = time.time()
        self.total_files = 0
        self.total_folders = 0
        self.is_cancelled = False
        self.__is_errored = False
        self.__ddl_servers = {}
        self.__engine = 'DDL v1'
        self.__asyncSession = None
        self.__user_id = self.__listener.message.from_user.id
        self.speed_limit = speed_limit
        super().__init__()

    def __del__(self):
        if self.__asyncSession:
            self.__asyncSession.close()

    async def __user_settings(self):
        """
        Loads user settings from the `user_data` module.
        """
        user_dict = user_data.get(self.__user_id, {})
        self.__ddl_servers = user_dict.get('ddl_servers', {})

    def __progress_callback(self, current: int):
        """
        Callback function that is called when a chunk of data is read from a file.
        """
        chunk_size = current - self.last_uploaded
        self.last_uploaded = current
        self.__processed_bytes += chunk_size
        if self.speed_limit > 0:
            await asyncio.sleep(chunk_size / self.speed_limit)
        if self.__listener.onUploadProgress:
            self.__listener.onUploadProgress(self.__processed_bytes)
        return chunk_size

    @retry(wait=wait_exponential(multiplier=2, min=4, max=8), stop=stop_after_attempt(3),
        retry=retry_if_exception_type(Exception))
    async def upload_aiohttp(self, url, file_path, req_file, data):
        """
        Uploads a file using aiohttp.
        """
        async with aiohttp.ClientSession() as self.__asyncSession:
            try:
                with ProgressFileReader(filename=file_path, read_callback=self.__progress_callback) as file:
                    data[req_file] = file
                    async with self.__asyncSession.post(url, data=data) as resp:
                        if resp.status == 200:
                            try:
                                return await resp.json()
                            except aiohttp.ContentTypeError:
                                return "Uploaded"
                        return None
            except aiohttp.ClientError as e:
                print(e)
                return None

    async def __upload_to_ddl(self, file_path):
        """
        Uploads a file to a DDL server.
        """
        all_links = {}
        for serv, (enabled, api_key) in self.__ddl_servers.items():
            if enabled:
                self.total_files = 0
                self.total_folders = 0
                if serv == 'gofile':
                    self.__engine = 'GoFile API'
                    if await aiopath.isfile(file_path):
                        mime_type = get_mime_type(file_path)
                    else:
                        mime_type = 'Folder'
                    try:
                        nlink = await Gofile(self, api_key).upload(file_path)
                    except Exception:
                        continue
                    all_links['GoFile'] = nlink
                if serv == 'streamtape':
                    self.__engine = 'StreamTape API'
                    if not await aiopath.isfile(file_path):
                        raise Exception("StreamTape only supports file uploads")
                    mime_type = get_mime_type(file_path)
                    try:
                        login, key = api_key.split(':')
                    except ValueError:
                        raise Exception("StreamTape Login & Key not Found, Kindly Recheck !")
                    try:
                        nlink = await Streamtape(self, login, key).upload(file_path)
                    except Exception:
                        continue
                    all_links['StreamTape'] = nlink
                self.__processed_bytes = 0
                if all_links:
                    break
        if not all_links:
            raise Exception("No DDL Enabled to Upload.")
        return all_links

    async def upload(self, file_name: str, size: int, speed_limit: int = 0) -> Tuple[Dict[str, Any], int]:
        """
        Uploads a file.
        """
        item_path = f"{self.__path}/{file_name}"
        print(f"Uploading: {item_path} via DDL")
        await self.__user_settings()
        try:
            link = await self.__upload_to_ddl(item_path)
            if link is not None:
                print(f"Uploaded To DDL: {item_path}")
                self.__listener.onUploadComplete(link, size, self.total_files, self.total_folders, 'application/octet-stream', file_name)
                return link, size
        except Exception as err:
            print("DDL Upload has been Cancelled")
            if self.__asyncSession:
                await self.__asyncSession.close()
            err = str(err).replace('>', '').replace('<', '')
            print(traceback.format_exc())
            self.__listener.onUploadError(err)
            self.__is_errored = True
        finally:
            if self.is_cancelled or self.__is_errored:
                return
            self.__listener.onUploadSpeed(self.speed)
            return

    @property
    def speed(self) -> float:
        """
        Returns the upload speed in bytes per second.
        """
        try:
            return self.__processed_bytes / int(time.time() - self.__start_time)
        except ZeroDivisionError:
            return 0

    @property
    def processed_bytes(self) -> int:
        """
        Returns the number of processed bytes.
        """
        return self.__processed_bytes

    @property
    def engine(self) -> str:
        """
        Returns the name of the upload engine.
        """
        return self.__engine

    async def cancel_download(self):
        """
        Cancels the current upload.
        """
        self.is_cancelled = True
        print(f"Cancelling Upload: {self.name}")
        if self.__asyncSession:
            await self.__asyncSession.close()
        self.__listener.onUploadError('Your upload has been stopped!')
        return

import user_data
from gofile import Gofile
from streamtape import Streamtape
