from time import sleep
from requests import get as rget
from os import getenv
from logging import error as logerror

BASE_URL = getenv("BASE_URL", None)
try:
    if len(BASE_URL) == 0:
        raise TypeError
    BASE_URL = BASE_URL.rstrip("/")
except TypeError:
    BASE_URL = None

PORT = getenv("PORT", None)
if PORT is not None and BASE_URL is not None:
    while True:
        try:
            rget(BASE_URL).status_code
            sleep(600)
        except Exception as e:
            logerror(f"cron_boot.py: {e}")
            sleep(2)
            continue
