#!/usr/bin/env python3

import os
import re
import logging
import asyncio
import tenacity
from contextlib import closing
from google.auth import default, jwt
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload

# Import bot-specific modules
from bot import OWNER_ID, config_dict, list_drives_dict, GLOBAL_EXTENSION_FILTER
from bot.helper.ext_utils.bot_utils import setInterval, async_to_sync, get_readable_file_size, fetch_user_tds
from bot.helper.ext_utils.fs_utils import get_mime_type
from bot.helper.ext_utils.leech_utils import format_filename

# Create a Request object for logging in with Google
LOGGER = Request()

# Configure logging for the Google API client
logging.getLogger('googleapiclient.discovery').setLevel(logging.ERROR)

def get_google_credentials() -> Credentials:
    """
    Returns a Google credentials object using the default application credentials.
    """
    try:
        credentials, _ = default(scopes=['https://www.googleapis.com/auth/drive'])
    except ValueError:
        # If no default credentials are found, try loading them from a JSON file
        credentials = Credentials.from_authorized_user_file('credentials.json', scopes=['https://www.googleapis.com/auth/drive'])
    return credentials

def get_google_drive_service() -> googleapiclient.discovery.Resource:
    """
    Returns a Google Drive service object using the default application credentials.
    """
    credentials = get_google_credentials()
    try:
        service = build('drive', 'v3', credentials=credentials)
    except HttpError as error:
        logging.error(f'An error occurred while building the Google Drive service: {error}')
        raise
    return service

def download_file(service: googleapiclient.discovery.Resource, file_id: str, file_path: str) -> None:
    """
    Downloads a file from Google Drive to the specified file path.
    """
    request = service.files().get_media(fileId=file_id)
    with closing(request) as download_request:
        with open(file_path, 'wb') as file:
            while True:
                chunk = download_request.read(8192)
                if not chunk:
                    break
                file.write(chunk)

def upload_file(service: googleapiclient.discovery.Resource, file_path: str, mime_type: str, parents: Optional[List[str]] = None) -> str:
    """
    Uploads a file to Google Drive and returns its file ID.
    """
    file_name = os.path.basename(file_path)
    media = MediaFileUpload(file_path, mime_type=mime_type, resumable=True)
    request = service.files().create(body={'name': file_name, 'mimeType': mime_type, 'parents': parents}, media_body=media, fields='id')
    response = request.execute()
    return response.get('id')

@retry(wait=wait_exponential(multiplier=1, min=1, max=60), stop=stop_after_attempt(3), retry=retry_if_exception_type(HttpError))
def retry_upload_file(service: googleapiclient.discovery.Resource, file_path: str, mime_type: str, parents: Optional[List[str]] = None) -> str:
    """
    Retries uploading a file to Google Drive until it succeeds or the maximum number of retries is reached.
    """
    return upload_file(service, file_path, mime_type, parents)

@asyncio.coroutine
def main():
    """
    The main function of the script.
    """
    service = get_google_drive_service()
    file_id = 'FILE_ID' # Replace with the actual file ID
    file_path = 'FILE_PATH' # Replace with the actual file path
    mime_type = get_mime_type(file_path)
    parents = ['PARENT_ID'] # Replace with the actual parent ID

    # Download the file from Google Drive
    download_file(service, file_id, file_path)

    # Upload the file to Google Drive
    file_id = retry_upload_file(service, file_path, mime_type, parents)
    print(f'File uploaded successfully: {file_id}')

if __name__ == '__main__':
    asyncio.run(main())

