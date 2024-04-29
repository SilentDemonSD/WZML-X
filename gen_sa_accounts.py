import errno
import os
import pickle
import sys
import time
from argparse import ArgumentParser
from base64 import b64decode
from contextlib import contextmanager
from glob import glob
from google.auth.exceptions import TransportError
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError, ResourceNotFoundError, TooManyRequests
from googleapiclient.http import HttpRequest
from psutil import cpu_count
from tqdm import tqdm

SCOPES = [
    'https://www.googleapis.com/auth/drive',
    'https://www.googleapis.com/auth/cloud-platform',
    'https://www.googleapis.com/auth/iam'
]


def load_credentials(path: str) -> dict:
    """Load credentials from a JSON file."""
    if not os.path.exists(path):
        raise FileNotFoundError(errno.ENOENT, os.strerror(errno.ENOENT), path)
    with open(path, 'r') as f:
        return loads(f.read())


def print_spinner(msg: str, interval: float = 0.1) -> None:
    """Print a message with a spinner animation while a task is being performed."""
    spinner = ['-', '\\', '|', '/']
    i = 0
    while True:
        sys.stdout.write(f'\r{msg} {spinner[i]}')
        sys.stdout.flush()
        time.sleep(interval)
        i = (i + 1) % len(spinner)
        if not sys.stdout.isatty():
            break

