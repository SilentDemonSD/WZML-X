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
    if os.path.exists(token_file):
        with open(token_file, "rb") as tf:
            creds = pickle.load(tf)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                "credentials.json", scopes)
            creds = flow.run_local_server(port=0)
        with open(token_file, "wb") as tf:
            pickle.dump(creds, tf)
    return creds

def main(api_service_name: str, api_version: str, scopes: t.List[str],
         token_file: str, *args, **kwargs) -> None:
    """Main function.

    Args:
        api_service_name (str): Name of the API service.
        api_version (str): Version of the API.
        scopes (List[str]): List of scopes for the API.
        token_file (str): Path to the token file.
        *args: Variable length argument list.
        **kwargs: Arbitrary keyword arguments.
    """
    creds = get_credentials(scopes, token_file)
    service = build(api_service_name, api_version, credentials=creds)
    # Use the service object to make API requests.

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    argcomplete.autocomplete(parser)
    parser.add_argument("api_service_name", help="Name of the API service.")
    parser.add_argument("api_version", help="Version of the API.")
    parser.add_argument("scopes", nargs="*", help="Scopes for the API.")
    parser.add_argument("--token_file", default="token.pickle",
                        help="Path to the token file.")
    args = parser.parse_args()
    main(args.api_service_name, args.api_version, args.scopes, args.token_file)
