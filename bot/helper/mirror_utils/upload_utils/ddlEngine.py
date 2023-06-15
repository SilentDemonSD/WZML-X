#!/usr/bin/env python3
import asyncio
from re import findall as re_findall
from os import path as ospath
from time import time

from bot import LOGGER, user_data
from bot.helper.ext_utils.fs_utils import get_mime_type
from bot.helper.ext_utils.bot_utils import setInterval
from bot.helper.mirror_utils.upload_utils.ddlserver.gofile import Async_Gofile

class DDLUploader:

    def __init__(self, name=None, path=None, listener=None):
        self.name = name
        self.__processed_bytes = 0
        self.__listener = listener
        self.__path = path
        self.__updater = None
        self.__start_time = time()
        self.__total_files = 0
        self.__total_folders = 0
        self.__is_cancelled = False
        self.__is_errored = False
        self.__ddl_servers = {}
        self.__engine = ''
        self.__total_time = 0
        self.__update_interval = 3
        self.__user_id = self.__listener.message.from_user.id
    
    async def __user_settings(self):
        user_dict = user_data.get(self.__user_id, {})
        self.__ddl_servers = user_dict.get('ddl_servers', {})
        
    async def __progress(self):
        if self.__updater is not None:
            self.__processed_bytes += self.__updater.interval

    async def __upload_to_gofile(self, file_path, token):
        gf = Async_Gofile(token=token)
        if ospath.isfile(file_path):
            cmd = await gf.upload(file=file_path)
        elif ospath.isdir(file_path):
            cmd = await gf.upload_folder(path=file_path)
            if cmd and 'parentFolder' in cmd:
                await gf.set_option(contentId=cmd['parentFolder'], option="public", value="true")
        if cmd and 'downloadPage' in cmd:
            return cmd['downloadPage'] 
        raise Exception("Failed to upload file/folder")

    async def __upload_to_ddl(self, file_path):
        for serv, (enabled, api_key) in self.__ddl_servers.items():
            if enabled:
                if serv == 'gofile':
                    self.__engine = 'GoFile API'
                    return await self.__upload_to_gofile(file_path, api_key)
                elif serv == 'streamsb':
                    self.__engine = 'StreamSB API'
                    # return await self.__upload_to_streamsb(file_path, api_key)
        raise Exception("No DDL Enabled to Upload.")

    async def upload(self, file_name, size):
        item_path = f"{self.__path}/{file_name}"
        LOGGER.info(f"Uploading: {item_path} via DDL")
        self.__updater = setInterval(self.__update_interval, self.__progress)
        await self.__user_settings()
        try:
            if ospath.isfile(item_path):
                mime_type = get_mime_type(item_path)
                link = await self.__upload_to_ddl(item_path)
                if self.__is_cancelled:
                    return
                if link is None:
                    raise Exception('Upload has been manually cancelled')
                LOGGER.info(f"Uploaded To DDL: {item_path}")
            else:
                mime_type = 'Folder'
                link = await self.__upload_to_ddl(item_path)
                if link is None:
                    raise Exception('Upload has been manually cancelled!')
                if self.__is_cancelled:
                    return
                LOGGER.info(f"Uploaded To DDL: {file_name}")
        except Exception as err:
            LOGGER.info(f"DDL Upload has been Cancelled")
            self.__is_errored = True
        finally:
            if self.__is_cancelled or self.__is_errored:
                return
            await self.__listener.onUploadComplete(link, size, self.__total_files, self.__total_folders, mime_type, file_name)

    @property
    def speed(self):
        try:
            return self.__processed_bytes / self.__total_time
        except ZeroDivisionError:
            return 0

    @property
    def processed_bytes(self):
        return self.__processed_bytes
    
    @property
    def engine(self):
        return self.__engine

    async def cancel_download(self):
        self.__is_cancelled = True
        LOGGER.info(f"Cancelling Upload: {self.name}")
        await self.__listener.onUploadError('Your upload has been stopped!')
