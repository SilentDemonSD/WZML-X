import sys
import time
import argparse
import glob
import pickle
import os

import argcomplete
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from google.auth.exceptions import RefreshError
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
import pathlib
import typing as t
import tqdm

def get_credentials(scopes: t.List[str], token_file: str) -> Credentials:
    """Gets credentials for Google API access.

    Args:
        scopes (List[str]): List of scopes for the API.
        token_file (str): Path to the token file.

    Returns:
        Credentials: Google API credentials.
    """
    creds = None
    if os.path.exists("credentials.json"):
        if os.path.exists(token_file):
            with open(token_file, "rb") as tf:
                try:
                    creds = pickle.load(tf)
                except Exception as e:
                    print(f"Error loading token file: {e}")
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                try:
                    creds.refresh(Request())
                except RefreshError as e:
                    print(f"Error refreshing credentials: {e}")
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    "credentials.json", scopes)
                creds = flow.run_local_server(port=0)
            if creds:
                try:
                    with open(token_file, "wb") as tf:
                        pickle.dump(creds, tf)
                except Exception as e:
                    print(f"Error writing token file: {e}")
    return creds

def main(api_service_name: str, api_version: str, scopes: t.List[str],
         token_file: str) -> None:
    """Main function.

    Args:
        api_service_name (str): Name of the API service.
        api_version (str): Version of the API.
        scopes (List[str]): List of scopes for the API.
        token_file (str): Path to the token file.
    """
    if not api_service_name or not api_version:
        raise ValueError("api_service_name and api_version must be provided.")
    if not scopes or not all(isinstance(s, str) for s in scopes):
        raise ValueError("scopes must be a non-empty list of strings.")
    creds = get_credentials(scopes, token_file)
    if creds:
        service = build(api_service_name, api_version, credentials=creds)
        # Use the service object to make API requests.
    else:
        print("Could not obtain credentials.")

