from asyncio import gather
from logging import getLogger

from bot.helper.mirror_leech_utils.uphoster_utils.uploaders_utils.devuploads_uploader import (
    DevUploadsUpload,
)
from bot.helper.mirror_leech_utils.uphoster_utils.uploaders_utils.vikingfile_uploader import (
    VikingFileUpload,
)
from bot.helper.mirror_leech_utils.uphoster_utils.uploaders_utils.buzzheavier_uploader import (
    BuzzHeavierUpload,
)
from bot.helper.mirror_leech_utils.uphoster_utils.uploaders_utils.gofile_uploader import (
    GoFileUpload,
)
from bot.helper.mirror_leech_utils.uphoster_utils.uploaders_utils.pixeldrain_uploader import (
    PixelDrainUpload,
)

LOGGER = getLogger(__name__)

SERVICE_MAP = {
    "gofile": GoFileUpload,
    "buzzheavier": BuzzHeavierUpload,
    "pixeldrain": PixelDrainUpload,
    "devuploads": DevUploadsUpload,
    "vikingfile": VikingFileUpload,
}


class MultiUphosterUpload:
    def __init__(self, listener, path, services, folder_name=""):
        self.listener = listener
        self.path = path
        self.services = services
        self.folder_name = folder_name
        self.uploaders = []
        self._processed_bytes = 0
        self._speed = 0
        self.is_cancelled = False
        self.results = {}
        self.failed = []

        for service in services:
            uploader_cls = SERVICE_MAP.get(service)
            if uploader_cls:
                self.uploaders.append(
                    uploader_cls(ProxyListener(self, service), path, self.folder_name)
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
        self, service, link, files, folders, mime_type, dir_id=""
    ):
        if service in self.results:
            return
        self.results[service] = {
            "link": link,
            "files": files,
            "folders": folders,
            "mime_type": mime_type,
            "dir_id": dir_id,
        }
        LOGGER.info(f"{service.capitalize()} Upload Complete: {link}")
        await self._check_completion()

    async def on_upload_error(self, service, error):
        if service in self.results:
            return
        self.results[service] = {"error": error}
        self.failed.append(service)
        LOGGER.error(f"{service.capitalize()} Upload Failed: {error}")
        await self._check_completion()

    async def _check_completion(self):
        if len(self.results) == len(self.services):
            if len(self.failed) == len(self.services):
                await self.listener.on_upload_error("All uphoster uploads failed!")
            else:
                first_success = next(s for s in self.services if s not in self.failed)
                result = self.results[first_success]
                await self.listener.on_upload_complete(
                    link=self.results,
                    files=result["files"],
                    folders=result["folders"],
                    mime_type=result["mime_type"],
                    dir_id=result.get("dir_id", ""),
                )


class ProxyListener:
    """Lightweight proxy that routes upload callbacks to MultiUphosterUpload.

    Delegates shared attributes (user_id, name, message, is_cancelled) to
    the parent multi-uploader's listener, and intercepts completion/error
    callbacks to route them back with the service name.
    """

    def __init__(self, multi_uploader, service):
        self.multi_uploader = multi_uploader
        self.service = service
        self.is_cancelled = False

    @property
    def user_id(self):
        return self.multi_uploader.listener.user_id

    @property
    def name(self):
        return self.multi_uploader.listener.name

    @property
    def message(self):
        return self.multi_uploader.listener.message

    async def on_upload_complete(self, link, files, folders, mime_type, dir_id=""):
        await self.multi_uploader.on_upload_complete(
            self.service, link, files, folders, mime_type, dir_id
        )

    async def on_upload_error(self, error):
        await self.multi_uploader.on_upload_error(self.service, error)
