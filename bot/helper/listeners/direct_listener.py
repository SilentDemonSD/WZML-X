from time import sleep

from bot import LOGGER, aria2
from bot.helper.ext_utils.bot_utils import async_to_sync, sync_to_async
import aiohttp
import asyncio

class DirectListener:
    """
    A class to handle direct downloads.
    """
    def __init__(self, foldername: str, total_size: int, path: str, listener, a2c_opt):
        self.__path = path
        self.__listener = listener
        self.__is_cancelled = False
        self.__a2c_opt = a2c_opt
        self.__proc_bytes = 0
        self.__failed = 0
        self.task = None
        self.name = foldername
        self.total_size = total_size

    @property
    def processed_bytes(self):
        if self.task:
            return self.__proc_bytes + self.task.completed_length
        return self.__proc_bytes

    @property
    def speed(self):
        return self.task.download_speed if self.task else 0

    async def download(self, contents):
        """
        Download the given contents.
        """
        self.is_downloading = True
        try:
            async with aiohttp.ClientSession() as session:
                tasks = []
                for content in contents:
                    if self.__is_cancelled:
                        break
                    if content['path']:
                        self.__a2c_opt['dir'] = f"{self.__path}/{content['path']}"
                    else:
                        self.__a2c_opt['dir'] = self.__path
                    filename = content['filename']
                    self.__a2c_opt['out'] = filename
                    try:
                        task = aria2.add_uris([content['url']], self.__a2c_opt, position=0, session=session)
                    except Exception as e:
                        self.__failed += 1
                        LOGGER.error(f'Unable to download {filename} due to: {e}')
                        continue
                    tasks.append(task)
                await asyncio.gather(*tasks)
        except asyncio.CancelledError:
            self.__is_cancelled = True
            LOGGER.info(f"Cancelling Download: {self.name}")
            await self.__listener.onDownloadError("Download Cancelled by User!")
            if self.task:
                await sync_to_async(self.task.remove, force=True, files=True)
            self.is_downloading = False
            return
        except Exception as e:
            LOGGER.error(f'Unable to download due to: {e}')
            await self.__listener.onDownloadError('Download Failed!')
            self.is_downloading = False
            return

        self.__proc_bytes = sum([task.completed_length for task in tasks])
        self.is_downloading = False
        if self.__failed == len(contents):
            await async_to_sync(self.__listener.onDownloadError, 'All files are failed to download!')
            return
        await async_to_sync(self.__listener.onDownloadComplete)

    async def cancel_download(self):
        """
        Cancel the current download.
        """
        self.__is_cancelled = True
        LOGGER.info(f"Cancelling Download: {self.name}")
        await self.__listener.onDownloadError("Download Cancelled by User!")
        if self.task:
            await sync_to_async(self.task.remove, force=True, files=True)
        self.is_downloading = False
