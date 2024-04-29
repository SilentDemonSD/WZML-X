import sys
import time
import argparse
import glob
import pickle
import os

import argcomplete
import google.auth
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from google.auth.exceptions import RefreshError
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
import pathlib
import typing as t
import tqdm

