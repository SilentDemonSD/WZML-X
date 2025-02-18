from __future__ import print_function
from argparse import ArgumentParser
from glob import glob
from json import load, JSONDecodeError
from os import path
from pickle import load as pickle_load, dump as pickle_dump
from sys import exit
from time import time

from googleapiclient.discovery import build
from progress.bar import Bar
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow


def parse_args():
    parser = ArgumentParser(
        description="Add service accounts to a shared drive using credentials files in a folder."
    )
    parser.add_argument(
        "--path",
        "-p",
        default="accounts",
        help="Path to the service accounts folder.",
    )
    parser.add_argument(
        "--credentials",
        "-c",
        default="./credentials.json",
        help="Path for the credentials file.",
    )
    parser.add_argument("--yes", "-y", action="store_true", help="Skips the prompt.")
    req = parser.add_argument_group("required arguments")
    req.add_argument("--drive-id", "-d", required=True, help="The ID of the Shared Drive.")
    return parser.parse_args()


def load_credentials_file(credentials_pattern):
    credentials_files = glob(credentials_pattern)
    if not credentials_files:
        print(">> No credentials found.")
        exit(0)
    credentials_file = credentials_files[0]
    try:
        with open(credentials_file, "r") as f:
            load(f)
        print(">> Found credentials.")
    except (IOError, JSONDecodeError) as e:
        print(">> Error reading credentials:", e)
        exit(1)
    return credentials_file


def authenticate(creds_file):
    token_path = "token_sa.pickle"
    creds = None
    try:
        if path.exists(token_path):
            with open(token_path, "rb") as token_file:
                creds = pickle_load(token_file)
    except Exception as e:
        print(">> Failed to load existing token:", e)
    try:
        if not creds or not getattr(creds, "valid", False):
            if creds and getattr(creds, "expired", False) and getattr(creds, "refresh_token", None):
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    creds_file,
                    scopes=[
                        "https://www.googleapis.com/auth/admin.directory.group",
                        "https://www.googleapis.com/auth/admin.directory.group.member",
                    ],
                )
                creds = flow.run_console()
            with open(token_path, "wb") as token_file:
                pickle_dump(creds, token_file)
    except Exception as e:
        print(">> Authentication failed:", e)
        exit(1)
    return creds


def add_service_accounts(drive_client, account_dir, drive_id):
    account_files = glob(path.join(account_dir, "*.json"))
    if not account_files:
        print(">> No service accounts found in:", account_dir)
        exit(0)
    batch = drive_client.new_batch_http_request()
    pbar = Bar("Readying accounts", max=len(account_files))
    for acc_file in account_files:
        try:
            with open(acc_file, "r") as f:
                data = load(f)
            client_email = data["client_email"]
            batch.add(
                drive_client.permissions().create(
                    fileId=drive_id,
                    supportsAllDrives=True,
                    body={"role": "organizer", "type": "user", "emailAddress": client_email},
                )
            )
        except Exception as e:
            print(">> Error processing file {}: {}".format(acc_file, e))
        pbar.next()
    pbar.finish()
    print("Adding...")
    try:
        batch.execute()
    except Exception as e:
        print(">> Batch execution failed:", e)
        exit(1)


def main():
    start_time = time()
    args = parse_args()
    credentials_file = load_credentials_file(args.credentials)

    if not args.yes:
        try:
            input(
                ">> Ensure the Google account that generated credentials.json has "
                "Manager access on your Team Drive.\n>> (Press any key to continue)"
            )
        except Exception as e:
            print(">> User prompt failed:", e)
            exit(1)

    creds = authenticate(credentials_file)
    drive_client = build("drive", "v3", credentials=creds)
    add_service_accounts(drive_client, args.path, args.drive_id)

    elapsed = time() - start_time
    hours, rem = divmod(elapsed, 3600)
    minutes, seconds = divmod(rem, 60)
    print("Complete.")
    print("Elapsed Time:\n{:0>2}:{:0>2}:{:05.2f}".format(int(hours), int(minutes), seconds))


if __name__ == "__main__":
    main()
