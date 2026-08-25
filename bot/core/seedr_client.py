from json import dumps

from niquests import AsyncSession

from .. import LOGGER
from .config_manager import Config

TOKEN_URL = "https://www.seedr.cc/oauth_test/token.php"
RESOURCE_URL = "https://www.seedr.cc/oauth_test/resource.php"
CLIENT_ID = "seedr_chrome"


class SeedrClient:
    def __init__(self, email="", password=""):
        self.email = email
        self.password = password
        self._access_token = ""
        self._refresh_token = ""
        self.is_connected = False
        self.error = "Seedr Credentials not provided!"

    async def login(self, email="", password=""):
        if email:
            self.email = email
        if password:
            self.password = password
        usr = self.email or Config.SEEDR_EMAIL
        pwd = self.password or Config.SEEDR_PASSWORD
        if not usr or not pwd:
            self.is_connected = False
            self.error = "Seedr Credentials not provided!"
            raise ValueError(self.error)
        self.error = ""
        result = await self._token_request(
            {
                "username": usr,
                "password": pwd,
                "grant_type": "password",
                "client_id": CLIENT_ID,
                "type": "login",
            }
        )
        if "access_token" not in result:
            error_desc = (
                result.get("error_description") or result.get("error") or result
            )
            self.error = f"Seedr Login Failed: {error_desc}"
            raise ValueError(self.error)
        self._access_token = result["access_token"]
        self._refresh_token = result.get("refresh_token", "")
        self.is_connected = True
        return result

    async def _token_request(self, payload):
        async with AsyncSession(timeout=30) as client:
            resp = await client.post(TOKEN_URL, data=payload)
            return resp.json()

    async def _refresh(self):
        if not self._refresh_token:
            return False
        try:
            result = await self._token_request(
                {
                    "refresh_token": self._refresh_token,
                    "grant_type": "refresh_token",
                    "client_id": CLIENT_ID,
                }
            )
        except Exception as e:
            LOGGER.error(f"Seedr token refresh failed: {e}")
            return False
        if "access_token" not in result:
            LOGGER.error(f"Seedr token refresh failed: {result}")
            return False
        self._access_token = result["access_token"]
        self._refresh_token = result.get("refresh_token", self._refresh_token)
        return True

    async def _api(self, func, payload):
        async with AsyncSession(timeout=30) as client:
            resp = await client.post(
                RESOURCE_URL,
                params={"access_token": self._access_token, "func": func},
                data=payload,
            )
            result = resp.json()
        if result.get("error") == "expired_token" and await self._refresh():
            async with AsyncSession(timeout=30) as client:
                resp = await client.post(
                    RESOURCE_URL,
                    params={"access_token": self._access_token, "func": func},
                    data=payload,
                )
                result = resp.json()
        return result

    async def get_space(self):
        res = await self.list_contents("0")
        if isinstance(res, dict):
            space_max = int(res.get("space_max", 0) or 0)
            space_used = int(res.get("space_used", 0) or 0)
            return space_max, space_used
        return 0, 0

    async def add_torrent(self, magnet):
        result = await self._api(
            "add_torrent", {"torrent_magnet": magnet, "folder_id": "0"}
        )
        if not isinstance(result, dict):
            raise ValueError(f"Seedr API returned invalid response: {result}")

        torrent_id = result.get("torrent_id") or result.get("user_torrent_id")
        res_val = result.get("result")
        err_val = result.get("error")

        if err_val or res_val is not True or not torrent_id:
            raw_err = err_val or res_val or result.get("code") or result
            err_str = str(raw_err).lower()
            if "not_enough_space" in err_str or "space" in err_str:
                space_max, space_used = await self.get_space()
                from ..helper.ext_utils.status_utils import get_readable_file_size

                free_space = get_readable_file_size(max(0, space_max - space_used))
                max_space = get_readable_file_size(space_max)
                raise ValueError(
                    f"Not enough space in Seedr account! (Free: {free_space} / Total: {max_space})"
                )
            elif "queue_full" in err_str:
                raise ValueError(
                    "Seedr account download queue is full! Please clear existing downloads."
                )
            elif "invalid" in err_str:
                raise ValueError("Invalid magnet link or torrent!")
            raise ValueError(f"Seedr add torrent failed: {raw_err}")

        return result

    async def list_contents(self, content_id="0"):
        return await self._api(
            "list_contents", {"content_type": "folder", "content_id": str(content_id)}
        )

    async def fetch_file(self, folder_file_id):
        result = await self._api("fetch_file", {"folder_file_id": str(folder_file_id)})
        if isinstance(result, str):
            return result
        if (
            result.get("error")
            or result.get("result") is False
            or not result.get("url")
        ):
            raise ValueError(f"Seedr fetch_file failed: {result}")
        return result["url"]

    async def delete(self, item_type, item_id):
        return await self._api(
            "delete", {"delete_arr": dumps([{"type": item_type, "id": item_id}])}
        )


seedr = SeedrClient()
