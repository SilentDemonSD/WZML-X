import random
import time
from typing import Any
from typing import Dict
from typing import Optional

import requests
from requests.exceptions import HTTPError
from urllib.parse import quote  # Used to escape URL characters

from cloudscraper import create_scraper  # Used to bypass cloud-based anti-scraping services
from bot import LOGGER, shorteners_list  # Importing the LOGGER and shorteners_list from bot.py

