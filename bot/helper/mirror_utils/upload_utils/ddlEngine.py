import asyncio
import io
import json
import os
import pathlib
import re
import time
import aiohttp
import tenacity
from typing import Dict, Any, Union, Optional, Callable, List, Tuple, Type, AsyncContextManager
from gofile import Gofile  # A class for interacting with gofile.io API
from streamtape import Streamtape  # A class for interacting with streamtape.com API

class ProgressFileReader(io.BufferedReader):
    """
    A custom BufferedReader that allows tracking of the number of bytes read.
    """
    def __init__(self, filename: str, read_callback: Optional[Callable[[int], None]] = None):
        """
        Initializes a new ProgressFileReader instance.
        :param filename: The path to the file to read.
        :param read_callback: An optional callback function to be called when a chunk of data is read.
        """
        super().__init__(open(filename, "rb"))
        self.__read_callback = read_callback
        self.length = pathlib.Path(filename).stat().st_size  # The total length of the file

    def read(self, size: Optional[int] = None) -> Union[bytes, MemoryView]:
        """
        Reads up to `size` bytes of data from the file.
        If `read_callback` is provided, it will be called with the current file position.
        :param size: The number of bytes to read. If None, reads the remaining bytes.
        :return: The read data as bytes or MemoryView.
        """
        size = size or (self.length - self.tell())  # Calculate the remaining bytes if size is None
        if self.__read_callback:
            self.__read_callback(self.tell())  # Call the read_callback with the current file position
        result = super().read(size)  # Read the data
        asyncio.sleep(0)  # Yield control to the event loop
        return result

class DDLUploader:
    """
    A class for uploading files to various DDL servers.
    """
    def __init__(self, listener, name: str, path: str, speed_limit: int = 0):
        """
        Initializes a new instance of the DDLUploader class.
        :param listener: The listener object to send upload progress and completion events.
        :param name: The name of the file or folder being uploaded.
        :param path: The path to the file or folder being uploaded.
        :param speed_limit: The maximum upload speed in bytes per second. 0 means no limit.
        """
        self.name = name
        self.__processed_bytes = 0  # The number of processed bytes
        self.last_uploaded = 0  # The position of the last uploaded byte
        self.__listener = listener  # The listener object
        self.__path = path  # The path to the file or folder being uploaded
        self.__start_time = time.time()  # The start time of the upload
        self.total_files = 0  # The total number of files in the folder being uploaded
        self.total_folders = 0  # The total number of folders in the folder being uploaded
        self.is_cancelled = False  # A flag indicating if the upload has been cancelled
        self.__is_errored = False  # A flag indicating if an error occurred during the upload
        self.__ddl_servers: Dict[str, Tuple[bool, str]] = {}  # A dictionary of enabled DDL servers
        self.__engine = 'DDL v1'  # The name of the upload engine
        self.__asyncSession: Optional[AsyncContextManager[aiohttp.ClientSession]] = None  # An aiohttp session
        self.__user_id = self.__listener.message.from_user.id  # The user ID
        self.speed_limit = speed_limit  # The maximum upload speed in bytes per second

    def __del__(self):
        if self.__asyncSession:
            self.__asyncSession.close()

    async def __user_settings(self):
        """
        Loads user settings from the `user_data` module.
        """
        user_dict = user_data.get(self.__user_id, {})  # Get the user data
        self.__ddl_servers = user_dict.get('ddl_servers', {})  # Get the DDL servers

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

    @tenacity.retry(wait=tenacity.wait_exponential(multiplier=2, min=4, max=8), stop=tenacity.stop_after_attempt(3),
        retry=tenacity.retry_if_exception_type(aiohttp.ClientError), reraise=True)
    async def upload_aiohttp(self, url: str, file_path: str, req_file: str, data: dict) -> Union[Dict[str, Any], str]:
        """
        Uploads a file using aiohttp.
        """
        async with aiohttp.ClientSession() as self.__asyncSession:
            try:
                async with ProgressFileReader(filename=file_path, read_callback=self.__progress_callback) as file:
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
            except Exception as e:
                print(f"Error in upload_aiohttp: {e}")
                return None
            finally:
                file.close()

    async def __upload_to_ddl(self, file_path: str) -> Optional[Dict[str, str]]:
        """
        Uploads a file to a DDL server.
        """
        for serv, (enabled, api_key) in self.__ddl_servers.items():
            if enabled:
                self.total_files = 0
                self.total_folders = 0
                if serv == 'gofile':
                    self.__engine = 'GoFile API'
                    if os.path.isfile(file_path):
                        mime_type = get_mime_type(file_path)
                    else:
                        mime_type = 'Folder'
                    try:
                        nlink = await Gofile(self, api_key).upload(file_path)
                    except Exception:
                        continue
                    return {'GoFile': nlink}
                if serv == 'streamtape':
                    self.__engine = 'StreamTape API'
                    if not os.path.isfile(file_path):
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
                    return {'StreamTape': nlink}
                self.__processed_bytes = 0
        return None

    async def upload(self, file_name: str, size: int, speed_limit: int = 0) -> Tuple[Optional[Dict[str, Any]], int]:
        """
        Uploads a file.
        """
        item_path = f"{self.__path}/{file_name}"
        print(f"Uploading: {item_path} via DDL")
        await self.__user_settings()
        tasks = []
        try:
            for _ in range(3):
                task = asyncio.create_task(self.__upload_to_ddl(item_path))
                tasks.append(task)
            results = await asyncio.gather(*tasks)
            if any(results):
                print(f"Uploaded To DDL: {item_path}")
                self.__listener.onUploadComplete(dict(results[0]), size, self.total_files, self.total_folders, 'application/octet-stream', file_name)
                return dict(results[0]), size
        except Exception as err:
            print("DDL Upload has been Cancelled")
            if self.__asyncSession:
                await self.__asyncSession.close()
            print(traceback.format_exc())
            self.__listener.onUploadError(str(err))
            self.__is_errored = True
        finally:
            if self.is_cancelled or self.__is_errored:
                return {}, 0
            self.__listener.onUploadSpeed(self.speed)
            return {}, 0

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
