#!/usr/bin/env python3
import os
import os.path as ospath
import requests
from bot import LOGGER
from bot.helper.ext_utils.bot_utils import is_gofile_token

class Gofile:
    def __init__(self, dluploader=None, token=None):
        self.api_url = "https://api.gofile.io/"
        self.dluploader = dluploader
        self.token = token
        if self.token is not None:
            is_gofile_token(url=self.api_url, token=self.token)

    def __resp_handler(self, response):
        api_resp = response.get("status", "")
        if api_resp == "ok":
            return response["data"]
        raise Exception(api_resp.split("-")[1] if "error-" in api_resp else "Response Status is not ok and Reason is Unknown")

    def __getServer(self):
        response = requests.get(f"{self.api_url}getServer").json()
        return self.__resp_handler(response)

    def __getAccount(self, check_account=False):
        if self.token is None:
            raise Exception()
        
        api_url = f"{self.api_url}getAccountDetails?token={self.token}&allDetails=true"
        response = requests.get(api_url).json()
        if check_account:
            return response["status"] == "ok" if True else self.__resp_handler(response)
        else:
            return self.__resp_handler(response)
        
    def upload_folder(self, path, folderId=None):
        if not os.path.isdir(path):
            raise Exception(f"Path: {path} is not a valid directory")
            
        folder_data = self.create_folder(self.__getAccount()["rootFolder"], ospath.basename(path))
        self.__setOptions(contentId=folder_data["id"], option="public", value="true")
    
        folderId = folderId or folder_data["id"]
        folder_ids = {".": folderId}
        for root, _, files in os.walk(path):
            rel_path = ospath.relpath(root, path)
            parentFolderId = folder_ids.get(ospath.dirname(rel_path), folderId)
            folder_name = ospath.basename(rel_path)
            currFolderId = self.create_folder(parentFolderId, folder_name)["id"]
            self.__setOptions(contentId=currFolderId, option="public", value="true")
            folder_ids[rel_path] = currFolderId

            for file in files:
                file_path = ospath.join(root, file)
                up = self.upload_file(file_path, currFolderId)
                
        return folder_data["code"]

    def upload_file(self, file: str, folderId: str = "", description: str = "", password: str = "", tags: str = "", expire: str = ""):
        if password and len(password) < 4:
            raise ValueError("Password Length must be greater than 4")

        server = self.__getServer()["server"]
        token = self.token if self.token else ""
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
        
        if self.dluploader.is_cancelled:
            return
        self.dluploader.last_uploaded = 0
        upload_file = self.dluploader.upload_httpx(f"https://{server}.gofile.io/uploadFile", file, "file", req_dict)
        return self.__resp_handler(upload_file)
        
    def upload(self, file_path):
        if os.path.isfile(file_path):
            if (gCode := self.upload_file(file=file_path)) and gCode.get("downloadPage", False):
                return gCode['downloadPage']
        elif os.path.isdir(file_path):
            if (gCode := self.upload_folder(path=file_path)):
                return f"https://gofile.io/d/{gCode}"
        raise Exception("Failed to upload file/folder to Gofile API, Retry or Try after sometimes...")

    def create_folder(self, parentFolderId, folderName):
        if self.token is None:
            raise Exception()
        
        response = requests.put(url=f"{self.api_url}createFolder",
            data={
                    "parentFolderId": parentFolderId,
                    "folderName": folderName,
                    "token": self.token
                }
            ).json()
        return self.__resp_handler(response)

    def __setOptions(self, contentId, option, value):
        if self.token is None:
            raise Exception()
        
        if not option in ["public", "password", "description", "expire", "tags"]:
            raise Exception(f"Invalid GoFile Option Specified : {option}")
        response = requests.put(url=f"{self.api_url}setOption",
            data={
                    "token": self.token,
                    "contentId": contentId,
                    "option": option,
                    "value": value
                }
            ).json()
        return self.__resp_handler(response)

    def get_content(self, contentId):
        if self.token is None:
            raise Exception()
        
        response = requests.get(url=f"{self.api_url}getContent?contentId={contentId}&token={self.token}").json()
        return self.__resp_handler(response)

    def copy_content(self, contentsId, folderIdDest):
        if self.token is None:
            raise Exception()
        response = requests.put(url=f"{self.api_url}copyContent",
                data={
                    "token": self.token,
                    "contentsId": contentsId,
                    "folderIdDest": folderIdDest
                }
            ).json()
        return self.__resp_handler(response)

    def delete_content(self, contentId):
        if self.token is None:
            raise Exception()
        response = requests.delete(url=f"{self.api_url}deleteContent",
                data={
                    "contentId": contentId,
                    "token": self.token
                }
            ).json()
        return self.__resp_handler(response)
