from __future__ import print_function
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from google.auth.transport.requests import Request
from google.auth.exceptions import RefreshError
from google.auth.scopes import SCOPES
import argparse
import json
import progress.bar
import glob
import os
import sys
import time

def file_exists(file_path: str) -> bool:
    """Check if a file exists.

    Args:
        file_path (str): The path of the file to check.

    Returns:
        bool: True if the file exists, False otherwise.
    """
    return os.path.isfile(file_path)

def get_time_str(seconds: float) -> str:
    """Format elapsed time as hours, minutes, and seconds.

    Args:
        seconds (float): The elapsed time in seconds.

    Returns:
        str: The elapsed time in the format hh:mm:ss.ss
    """
    hours, rem = divmod(seconds, 3600)
    minutes, seconds = divmod(rem, 60)
    return f"{int(hours):0>2}:{int(minutes):0>2}:{seconds:05.2f}"

def get_drive_service(credentials: Credentials) -> build:
    """Get the Google Drive service.

    Args:
        credentials (google.oauth2.credentials.Credentials): The OAuth 2.0 credentials.

    Returns:
        googleapiclient.discovery.Resource: The Google Drive service.
    """
    return build("drive", "v3", credentials=credentials)

def add_service_accounts_to_drive(drive_id: str, account_folder: str, credentials_file: str, yes: bool) -> None:
    """Add service accounts to a shared drive.

    Args:
        drive_id (str): The ID of the shared drive.
        account_folder (str): The path to the folder containing service account credentials.
        credentials_file (str): The path to the credentials file.
        yes (bool): Whether to skip the sanity prompt.
    """
    if not file_exists(credentials_file):
        print(">> No credentials found.")
        sys.exit(0)

    if not yes:
        input(
            '>> Make sure the Google account that has generated ' + credentials_file + ' '
            'is added into your Team Drive (shared drive) as Manager\n>> (Press any key to continue)'
        )

    credentials = Credentials.from_authorized_user_file(credentials_file, SCOPES)

    if not credentials or not credentials.valid:
        if credentials and credentials.expired and credentials.refresh_token:
            try:
                credentials.refresh(Request())
            except RefreshError:
                print("The credentials have expired and cannot be refreshed.")
                sys.exit(1)
        else:
            print(">> Please run `gcloud auth application-default login` to authenticate.")
            sys.exit(1)

    drive = get_drive_service(credentials)
    batch = drive.new_batch_http_request()

    aa = glob.glob(f"{account_folder}/*.json")
    pbar = progress.bar.Bar("Readying accounts", max=len(aa))
    for i in aa:
        ce = json.loads(open(i, 'r').read())['client_email']
        batch.add(
            drive.permissions().create(
                fileId=drive_id,
                supportsAllDrives=True,
                body={
                    "role": "organizer",
                    "type": "user",
                    "emailAddress": ce
                }
            )
        )
        pbar.next()
    pbar.finish()
    print('Adding...')
    batch.execute()

    print('Complete.')
    elapsed_time = get_time_str(time.time() - stt)
    print(f"Elapsed Time:\n{elapsed_time}")

if __name__ == "__main__":
    stt = time.time()

    parse = argparse.ArgumentParser(
        description='A tool to add service accounts to a shared drive from a folder containing credential files.'
    )
    parse.add_argument('--path', '-p', default='accounts', help='Specify an alternative path to the service accounts folder.')
    parse.add_argument('--credentials', '-c', default='./credentials.json',
                       help='Specify the relative path for the credentials file.')
    parse.add_argument('--yes', '-y', default=False, action='store_true',
                       help='Skips the sanity prompt.')
    parsereq = parse.add_argument_group('required arguments')
    parsereq.add_argument('--drive-id', '-d', help='The ID of the Shared Drive.', required=True)

    args = parse.parse_args()

    add_service_accounts_to_drive(args.drive_id, args.path, args.credentials, args.yes)
