from asyncio import gather
from logging import getLogger

from bot.helper.mirror_leech_utils.uphoster_utils.gofile_utils.upload import (
    GoFileUpload,
)
from bot.helper.mirror_leech_utils.uphoster_utils.buzzheavier_utils.upload import (
    BuzzHeavierUpload,
)
from bot.helper.mirror_leech_utils.uphoster_utils.pixeldrain_utils.upload import (
    PixelDrainUpload,
)

LOGGER = getLogger(__name__)


class MultiUphosterUpload:
    def __init__(self, listener, path, services):
        self.listener = listener
        self.path = path
        self.services = services
        self.uploaders = []
        self._processed_bytes = 0
        self._speed = 0
        self.is_cancelled = False
        self.results = {}
        self.failed = []

        for service in services:
            if service == "gofile":
                self.uploaders.append(GoFileUpload(ProxyListener(self, "gofile"), path))
            elif service == "buzzheavier":
                self.uploaders.append(
                    BuzzHeavierUpload(ProxyListener(self, "buzzheavier"), path)
                )
            elif service == "pixeldrain":
                self.uploaders.append(
                    PixelDrainUpload(ProxyListener(self, "pixeldrain"), path)
                )

    @property
    def speed(self):
        return sum(u.speed for u in self.uploaders)

    @property
    def processed_bytes(self):
        if not self.uploaders:
            return 0
        return sum(u.processed_bytes for u in self.uploaders) / len(self.uploaders)

    async def upload(self):
        tasks = [u.upload() for u in self.uploaders]
        await gather(*tasks)

    async def cancel_task(self):
        self.is_cancelled = True
        tasks = [u.cancel_task() for u in self.uploaders]
        await gather(*tasks)

    async def on_upload_complete(
        self, service, link, files, folders, mime_type, dir_id
    ):
        self.results[service] = {
            "link": link,
            "files": files,
            "folders": folders,
            "mime_type": mime_type,
            "dir_id": dir_id,
        }
        await self._check_completion()

    async def on_upload_error(self, service, error):
        LOGGER.error(f"Upload failed for {service}: {error}")
        self.failed.append(service)
        self.results[service] = {"error": error}
        await self._check_completion()

    async def _check_completion(self):
        if len(self.results) == len(self.uploaders):
            if len(self.failed) == len(self.uploaders):
                await self.listener.on_upload_error("All uploads failed.")
            else:
                successful_result = next(
                    v for k, v in self.results.items() if "error" not in v
                )
                await self.listener.on_upload_complete(
                    self.results,
                    successful_result["files"],
                    successful_result["folders"],
                    successful_result["mime_type"],
                    successful_result["dir_id"],
                )


class ProxyListener:
    def __init__(self, multi_uploader, service):
        self.multi_uploader = multi_uploader
        self.service = service
        self.is_cancelled = False

    def __getattr__(self, name):
        return getattr(self.multi_uploader.listener, name)

    async def on_upload_complete(self, link, files, folders, mime_type, dir_id=""):
        await self.multi_uploader.on_upload_complete(
            self.service, link, files, folders, mime_type, dir_id
        )

    async def on_upload_error(self, error):
        await self.multi_uploader.on_upload_error(self.service, error)
