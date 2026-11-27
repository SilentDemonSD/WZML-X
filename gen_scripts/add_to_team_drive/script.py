#!/usr/bin/env python3
"""
Add Service Accounts to Team Drive

This script adds Google service accounts to a Team Drive with
organizer access, enabling the bot to search files in that drive.
"""

from argparse import ArgumentParser, RawDescriptionHelpFormatter
from glob import glob
from json import load, JSONDecodeError
from os import path
from pickle import load as pickle_load, dump as pickle_dump
from sys import exit

from googleapiclient.discovery import build
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow


def print_header(title: str) -> None:
    """Print a formatted header."""
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60)


def print_step(step: int, total: int, message: str) -> None:
    """Print a step indicator."""
    print(f"\n[{step}/{total}] {message}")


def load_credentials_file(credentials_pattern):
    """Find and validate credentials file."""
    credentials_files = glob(credentials_pattern)
    if not credentials_files:
        print("[ERROR] No credentials found!")
        exit(0)
    credentials_file = credentials_files[0]
    try:
        with open(credentials_file, "r") as f:
            load(f)
        print(f"[OK] Found: {credentials_file}")
    except (IOError, JSONDecodeError) as e:
        print(f"[ERROR] Invalid credentials file: {e}")
        exit(1)
    return credentials_file


def authenticate(creds_file, token_path):
    """Authenticate and return credentials."""
    creds = None
    try:
        if path.exists(token_path):
            with open(token_path, "rb") as token_file:
                creds = pickle_load(token_file)
    except Exception as e:
        print(f"[WARN] Could not load existing token: {e}")

    try:
        if not creds or not getattr(creds, "valid", False):
            if (
                creds
                and getattr(creds, "expired", False)
                and getattr(creds, "refresh_token", None)
            ):
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    creds_file,
                    scopes=[
                        "https://www.googleapis.com/auth/admin.directory.group",
                        "https://www.googleapis.com/auth/admin.directory.group.member",
                    ],
                )
                creds = flow.run_local_server(port=0, open_browser=False)
            with open(token_path, "wb") as token_file:
                pickle_dump(creds, token_file)
        print("[OK] Authentication successful!")
    except Exception as e:
        print(f"[ERROR] Authentication failed: {e}")
        exit(1)
    return creds


def add_service_accounts(drive_client, account_dir, drive_id):
    """Add all service accounts in folder to Team Drive."""
    account_files = glob(path.join(account_dir, "*.json"))
    if not account_files:
        print(f"[ERROR] No service account files found in: {account_dir}")
        print("\nMake sure you have run gen_sa_accounts first!")
        exit(0)

    print(f"[INFO] Found {len(account_files)} service accounts")

    batch = drive_client.new_batch_http_request()
    added_count = 0

    for acc_file in account_files:
        try:
            with open(acc_file, "r") as f:
                data = load(f)
            client_email = data["client_email"]
            batch.add(
                drive_client.permissions().create(
                    fileId=drive_id,
                    supportsAllDrives=True,
                    body={
                        "role": "organizer",
                        "type": "user",
                        "emailAddress": client_email,
                    },
                )
            )
            added_count += 1
            print(f"  [OK] Queued: {client_email}")
        except Exception as e:
            print(f"  [ERROR] Failed to process {acc_file}: {e}")

    print(f"\n[INFO] Adding {added_count} accounts to Team Drive...")
    try:
        batch.execute()
        print(f"[OK] Successfully added {added_count} accounts!")
    except Exception as e:
        print(f"[ERROR] Batch execution failed: {e}")
        exit(1)


def main():
    epilog = """
Examples:
  # Basic usage with drive ID
  python script.py --drive-id "0ABCD123456789XYZ"

  # Custom credentials and accounts path
  python script.py -c ../config/credentials.json -p ./accounts -d "0ABCD123456789XYZ"

  # Skip confirmation prompt
  python script.py -d "0ABCD123456789XYZ" --yes

Notes:
  - Get your Team Drive ID from the URL: docs.google.com/spreadsheets/d/DRIVE_ID/...
  - Your Google account needs Manager access on the Team Drive
  - Run gen_sa_accounts first to create service accounts
"""
    parser = ArgumentParser(
        description="Add Service Accounts to Team Drive",
        epilog=epilog,
        formatter_class=RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--path",
        "-p",
        default="accounts",
        help="Path to service accounts folder (default: accounts)",
    )
    parser.add_argument(
        "--credentials",
        "-c",
        default="../../config/credentials.json",
        help="Path to credentials file (default: ../../config/credentials.json)",
    )
    parser.add_argument(
        "--yes", "-y", action="store_true", help="Skip confirmation prompt"
    )
    req = parser.add_argument_group("required arguments")
    req.add_argument(
        "--drive-id", "-d", required=True, help="Team Drive ID (get from URL)"
    )
    args = parser.parse_args()

    print_header("Add Service Accounts to Team Drive")

    # Step 1: Validate credentials
    print_step(1, 3, "Validating credentials...")
    credentials_file = load_credentials_file(args.credentials)

    # Step 2: Confirm
    if not args.yes:
        print(
            "\n[IMPORTANT] Your Google account must have Manager access on the Team Drive."
        )
        confirm = input("Continue? (y/n): ").strip().lower()
        if confirm != "y":
            print("\n[INFO] Cancelled.")
            exit(0)

    # Step 3: Authenticate
    print_step(2, 3, "Authenticating...")
    token_path = path.join(path.dirname(args.credentials), "tokens", "token_sa.pickle")
    creds = authenticate(credentials_file, token_path)

    # Step 4: Add accounts
    print_step(3, 3, "Adding service accounts to Team Drive...")
    drive_client = build("drive", "v3", credentials=creds)
    add_service_accounts(drive_client, args.path, args.drive_id)

    print("\n" + "=" * 60)
    print("  SUCCESS!")
    print("=" * 60)
    print("\nAll service accounts now have organizer access to:")
    print(f"  Team Drive ID: {args.drive_id}")
    print("\nThe bot can now search files in this Team Drive.")


if __name__ == "__main__":
    main()
