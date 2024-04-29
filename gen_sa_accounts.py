import errno
import os
import pickle
import sys
from argparse import ArgumentParser
from base64 import b64decode
from glob import glob
from json import loads
from random import choice
from time import sleep

import google.auth.exceptions
import google.auth.transport.requests
import google_auth_oauthlib.flow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

SCOPES = [
    "https://www.googleapis.com/auth/drive",
    "https://www.googleapis.com/auth/cloud-platform",
    "https://www.googleapis.com/auth/iam",
]
ProjectServiceAccounts = list[dict[str, str]]
Projects = list[str]
ServiceAccountKeys = list[tuple[str, str]]

