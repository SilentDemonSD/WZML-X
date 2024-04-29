import errno
import os
import pickle
import signal
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
from googleapiclient.errors import HttpError, HttpError as GoogleAPICLientHttpError
from googleapiclient.http import HttpRequest
from psutil import Process
from typing import Any, Callable, Dict, List, NamedTuple, Optional, Union

