#!/usr/bin/env python3
import os
import re
from typing import Any, Dict, List, Optional, Union

import google.auth
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from tenacity.retry import RetryError

from bot import OWNER_ID, config_dict, list_drives_dict, GLOBAL_EXTENSION_FILTER
from bot.helper.ext_utils.bot_utils import setInterval, async_to_sync, get_readable_file_size, fetch_user_tds
from bot.helper.ext_utils.fs_utils import get_mime_type
from bot.helper.ext_utils.leech_utils import format_filename

LOGGER = google.auth.transport.requests.Request()
getLogger('googleapiclient.discovery').setLevel(ERROR)

