import os

from asyncio import sleep
from aiohttp import ClientSession

from bot.helper.ext_utils.bot_utils import is_valid_token


class Async_Gofile:
    def __init__(self, token=None):
        self.api_url = "https://api.gofile.io/"
        self.token = token
        if self.token is not None:
            is_valid_token(url=self.api_url, token=self.token)

    async def _api_resp_handler(self, response):
        api_status = response["status"]
        if api_status == "ok":
            return response["data"]
        else:
            if "error-" in response["status"]:
                error = response["status"].split("-")[1]
            else:
                error = "Response Status is not ok and reason is unknown"
            raise Exception(error)

    async def get_Server(self, pre_session=None):
        if pre_session:
            server_resp = await pre_session.get(f"{self.api_url}getServer")
            server_resp = await server_resp.json()
            return await self._api_resp_handler(server_resp)
        else:
            async with ClientSession() as session:
                try:
                    server_resp = await session.get(f"{self.api_url}getServer")
                    server_resp = await server_resp.json()
                    return await self._api_resp_handler(server_resp)
                except Exception as e:
                    raise Exception(e)

    async def get_Account(self, check_account=False):
        if self.token is None:
            raise Exception()
        async with ClientSession() as session:
            try:
                get_account_resp = await session.get(url=f"{self.api_url}getAccountDetails?token={self.token}&allDetails=true")
                get_account_resp = await get_account_resp.json()
                if check_account is True:
                    if get_account_resp["status"] == "ok":
                        return True
                    elif get_account_resp["status"] == "error-wrongToken":
                        return False
                    else:
                        return await self._api_resp_handler(get_account_resp)
                else:
                    return await self._api_resp_handler(get_account_resp)
            except Exception as e:
                raise Exception(e)

    async def upload_folder(self, path: str, folderId: str = "", delay: int = 2):
        if not os.path.isdir(path):
            raise Exception(f"{path} is not a valid directory")

        folder_name = os.path.basename(path)
        if not folderId:
            account_data = await self.get_Account()
            rtfid = account_data["rootFolder"]
            folder_data = await self.create_folder(rtfid, folder_name)
            folderId = folder_data["id"]

        uploaded = None
        folder_ids = {".": folderId}  # Dictionary to store created folder IDs
        for root, dirs, files in os.walk(path):
            relative_path = os.path.relpath(root, path)
            if relative_path == ".":
                current_folder_id = folderId
            else:
                parent_folder_id = folder_ids.get(os.path.dirname(relative_path), folderId)
                folder_name = os.path.basename(relative_path)
                folder_data = await self.create_folder(parent_folder_id, folder_name)
                current_folder_id = folder_data["id"]
                folder_ids[relative_path] = current_folder_id
            
            for file in files:
                file_path = os.path.join(root, file)
                udt = await self.upload(file_path, current_folder_id)
                if uploaded is None:
                    uploaded = udt
                await sleep(delay)
        return uploaded

    async def upload(self, file: str, folderId: str = "", description: str = "", password: str = "", tags: str = "", expire: str = ""):
        async with ClientSession() as session:
            # Check time
            if password and len(password) < 4:
                raise ValueError("Password Length must be greater than 4")

            server = await self.get_Server(pre_session=session)
            server = server["server"]
            token = self.token if self.token else ""

            # Making dict
            req_dict = {}
            if token:
                req_dict["token"] = token
            if folderId:
                req_dict["folderId"] = folderId
            if description:
                req_dict["description"] = description
            if password:
                req_dict["password"] = password
            if tags:
                req_dict["tags"] = tags
            if expire:
                req_dict["expire"] = expire

            with open(file, "rb") as go_file_d:
                req_dict["file"] = go_file_d
                upload_file = await session.post(
                    url=f"https://{server}.gofile.io/uploadFile",
                    data=req_dict
                )
                upload_file = await upload_file.json()
                return await self._api_resp_handler(upload_file)

    async def create_folder(self, parentFolderId, folderName):
        if self.token is None:
            raise Exception()
        async with ClientSession() as session:
            try:
                folder_resp = await session.put(
                    url=f"{self.api_url}createFolder",
                    data={
                        "parentFolderId": parentFolderId,
                        "folderName": folderName,
                        "token": self.token
                    }
                )
                folder_resp = await folder_resp.json()
                return await self._api_resp_handler(folder_resp)
            except Exception as e:
                raise Exception(e)

    async def set_option(self, contentId, option, value):
        if self.token is None:
            raise Exception()
        if not option in ["public", "password", "description", "expire", "tags"]:
            raise Exception(option)
        async with ClientSession() as session:
            try:
                set_resp = await session.put(
                    url=f"{self.api_url}setOption",
                    data={
                        "token": self.token,
                        "contentId": contentId,
                        "option": option,
                        "value": value
                    }
                )
                set_resp = await set_resp.json()
                return await self._api_resp_handler(set_resp)
            except Exception as e:
                raise Exception(e)

    async def get_content(self, contentId):
        if self.token is None:
            raise Exception()
        async with ClientSession() as session:
            try:
                get_content_resp = await session.get(url=f"{self.api_url}getContent?contentId={contentId}&token={self.token}")
                get_content_resp = await get_content_resp.json()
                return await self._api_resp_handler(get_content_resp)
            except Exception as e:
                raise Exception(e)

    async def copy_content(self, contentsId, folderIdDest):
        if self.token is None:
            raise Exception()
        async with ClientSession() as session:
            try:
                copy_content_resp = await session.put(
                    url=f"{self.api_url}copyContent",
                    data={
                        "token": self.token,
                        "contentsId": contentsId,
                        "folderIdDest": folderIdDest
                    }
                )
                copy_content_resp = await copy_content_resp.json()
                return await self._api_resp_handler(copy_content_resp)
            except Exception as e:
                raise Exception(e)

    async def delete_content(self, contentId):
        if self.token is None:
            raise Exception()
        async with ClientSession() as session:
            try:
                del_content_resp = await session.delete(
                    url=f"{self.api_url}deleteContent",
                    data={
                        "contentId": contentId,
                        "token": self.token
                    }
                )
                del_content_resp = await del_content_resp.json()
                return await self._api_resp_handler(del_content_resp)
            except Exception as e:
                raise Exception(e)
