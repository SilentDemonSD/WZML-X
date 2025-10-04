from asyncio import sleep, TimeoutError
from aiohttp.client_exceptions import ClientError

from ... import LOGGER
from ...core.torrent_manager import TorrentManager, aria2_name


class DirectListener:
    def __init__(self, path, listener, a2c_opt):
        self.listener = listener
        self._path = path
        self._a2c_opt = a2c_opt
        self._proc_bytes = 0
        self._failed = 0
        self.download_task = None
        self.name = self.listener.name

    @property
    def processed_bytes(self):
        if self.download_task:
            return self._proc_bytes + int(
                self.download_task.get("completedLength", "0")
            )
        return self._proc_bytes

    @property
    def speed(self):
        return (
            int(self.download_task.get("downloadSpeed", "0"))
            if self.download_task
            else 0
        )

    async def download(self, contents):
        self.is_downloading = True
        for content in contents:
            if self.listener.is_cancelled:
                break

            filename = content["filename"]
            success = False

            # Try progressive fallback if url_variants exist
            if 'url_variants' in content:
                success = await self._download_with_fallback(content)
            else:
                # Fallback to original method
                success = await self._download_original_method(content)

            if not success:
                self._failed += 1

        if self.listener.is_cancelled:
            return
        if self._failed == len(contents):
            await self.listener.on_download_error("All files are failed to download!")
            return
        await self.listener.on_download_complete()

    async def _download_with_fallback(self, content):
        """Download using progressive fallback method"""
        filename = content["filename"]
        url_variants = content.get("url_variants", [])
        file_id = content.get("file_id")
        api_key = content.get("api_key")

        for attempt, (url, headers, method) in enumerate(url_variants, 1):
            if self.listener.is_cancelled:
                return False

            LOGGER.info(f"Attempting download #{attempt} for {filename} using {method} method")

            # Create file-specific options
            file_a2c_opt = self._a2c_opt.copy()

            # Set directory and filename
            if content["path"]:
                file_a2c_opt["dir"] = f"{self._path}/{content['path']}"
            else:
                file_a2c_opt["dir"] = self._path
            file_a2c_opt["out"] = filename

            # Add headers if present
            if headers:
                if isinstance(headers, dict):
                    header_strings = [f"{k}: {v}" for k, v in headers.items()]
                    file_a2c_opt["header"] = header_strings
                    LOGGER.info(f"Using {method} headers for {filename}")
                else:
                    file_a2c_opt["header"] = headers

            try:
                gid = await TorrentManager.aria2.addUri(
                    uris=[url], options=file_a2c_opt, position=0
                )
                LOGGER.info(f"Started download attempt #{attempt}: {filename} with {method} method")

                if await self._wait_for_download_completion(gid, filename, method):
                    return True  # Success
                else:
                    # This attempt failed, continue to next variant
                    continue

            except (TimeoutError, ClientError, Exception) as e:
                LOGGER.error(f"Download attempt #{attempt} failed for {filename} using {method}: {e}")
                continue

        # All attempts failed
        if not api_key and len(url_variants) < 3:  # No API key was available
            LOGGER.error(
                f"All download attempts failed for {filename}. API key not set - cannot try authenticated download.")
            await self.listener.on_download_error(
                f"Download failed for {filename}. Consider setting up Pixeldrain API key for authenticated downloads.")
        else:
            LOGGER.error(f"All download attempts failed for {filename} including authenticated method.")

        return False

    async def _download_original_method(self, content):
        """Fallback to original download method"""
        filename = content["filename"]

        file_a2c_opt = self._a2c_opt.copy()

        if content["path"]:
            file_a2c_opt["dir"] = f"{self._path}/{content['path']}"
        else:
            file_a2c_opt["dir"] = self._path
        file_a2c_opt["out"] = filename

        # Handle headers if present
        if file_headers := content.get("headers"):
            if isinstance(file_headers, dict):
                header_strings = [f"{k}: {v}" for k, v in file_headers.items()]
                file_a2c_opt["header"] = header_strings
            else:
                file_a2c_opt["header"] = file_headers

        try:
            gid = await TorrentManager.aria2.addUri(
                uris=[content["url"]], options=file_a2c_opt, position=0
            )
            LOGGER.info(f"Started download (original method): {filename}")

            return await self._wait_for_download_completion(gid, filename, "original")

        except (TimeoutError, ClientError, Exception) as e:
            LOGGER.error(f"Unable to download {filename} due to: {e}")
            return False

    async def _wait_for_download_completion(self, gid, filename, method):
        """Wait for download completion and handle errors"""
        self.download_task = await TorrentManager.aria2.tellStatus(gid)

        while True:
            if self.listener.is_cancelled:
                if self.download_task:
                    await TorrentManager.aria2_remove(self.download_task)
                return False

            self.download_task = await TorrentManager.aria2.tellStatus(gid)

            if error_message := self.download_task.get("errorMessage"):
                LOGGER.error(f"Download failed for {filename} using {method} method: {error_message}")
                await TorrentManager.aria2_remove(self.download_task)
                return False
            elif self.download_task.get("status", "") == "complete":
                self._proc_bytes += int(self.download_task.get("totalLength", "0"))
                await TorrentManager.aria2_remove(self.download_task)
                LOGGER.info(f"Successfully downloaded: {filename} using {method} method")
                self.download_task = None
                return True

            await sleep(1)

    async def cancel_task(self):
        self.listener.is_cancelled = True
        LOGGER.info(f"Cancelling Download: {self.listener.name}")
        await self.listener.on_download_error("Download Cancelled by User!")
        if self.download_task:
            await TorrentManager.aria2_remove(self.download_task)
