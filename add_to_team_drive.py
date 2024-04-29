import argparse
import json
from pathlib import Path
import pickle
import progress.bar
from typing import Any, Dict, List, Optional

import google.auth
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import BatchHttpRequest

chdrive = build("drive", "v3", credentials=None)

class GoogleDriveTool:
    """A tool to add service accounts to a shared drive from a folder containing credential files."""

    def __init__(self, drive_id: str, credential_file: str, service_account_dir: str, yes: bool = False):
        self.drive_id = drive_id
        self.credential_file = credential_file
        self.service_account_dir = service_account_dir
        self.yes = yes

    def _get_service_account_emails(self) -> List[str]:
        """Get the email addresses of all service accounts in the specified directory."""
        service_account_files = list(self.service_account_dir.glob("*.json"))
        if not service_account_files:
            print(">> No service account files found.")
            sys.exit(0)

        service_account_emails = []
        for file in service_account_files:
            with file.open() as f:
                data = json.load(f)
            service_account_emails.append(data["client_email"])

        return service_account_emails

    def _authorize(self) -> Credentials:
        """Authorize the user and get credentials."""
        creds = None
        if Path("token_sa.pickle").exists():
            with Path("token_sa.pickle").open("rb") as token:
                creds = pickle.load(token)

        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    self.credential_file,
                    scopes=[
                        "https://www.googleapis.com/auth/admin.directory.group",
                        "https://www.googleapis.com/auth/admin.directory.group.member",
                    ],
                )
                creds = flow.run_console()

            with Path("token_sa.pickle").open("wb") as token:
                pickle.dump(creds, token)

        return creds

    def _add_service_accounts_to_drive(self, service_account_emails: List[str]):
        """Add the specified service accounts to the shared drive."""
        drive = googleapiclient.discovery.build("drive", "v3", credentials=self._authorize())
        batch = drive.new_batch_http_request()

        for email in service_account_emails:
            batch.add(
                drive.permissions().create(
                    fileId=self.drive_id,
                    supportsAllDrives=True,
                    body={
                        "role": "organizer",
                        "type": "user",
                        "emailAddress": email,
                    },
                )
            )

        try:
            batch.execute()
        except HttpError as error:
            print(f"An error occurred: {error}")
            sys.exit(1)

    def run(self):
        """Run the tool."""
        start_time = time.time()

        service_account_emails = self._get_service_account_emails()

        if not self.yes:
            input(
                f">> Make sure the Google account that has generated {self.credential_file} "
                "is added into your Team Drive (shared drive) as Manager\n>> (Press any key to continue)"
            )

        self._add_service_accounts_to_drive(service_account_emails)

        print("Complete.")
        hours, rem = divmod((time.time() - start_time), 3600)
        minutes, sec = divmod(rem, 60)
        print(
            f"Elapsed Time:\n{int(hours)}:{int(minutes)}:{sec:05.2f}"
        )

if __name__ == "__main__":
    parse = argparse.ArgumentParser(
        description="A tool to add service accounts to a shared drive from a folder containing credential files."
    )
    parse.add_argument(
        "--path",
        "-p",
        default="accounts",
        help="Specify an alternative path to the service accounts folder.",
    )
    parse.add_argument(
        "--credentials",
        "-c",
        default="./credentials.json",
        help="Specify the relative path for the credentials file.",
    )
    parse.add_argument(
        "--yes",
        "-y",
        default=False,
        action="store_true",
        help="Skips the sanity prompt.",
    )
    parsereq = parse.add_argument_group("required arguments")
    parsereq.add_argument(
        "--drive-id",
        "-d",
        help="The ID of the Shared Drive.",
        required=True,
    )

    args = parse.parse_args()

    tool = GoogleDriveTool(args.drive_id, args.credentials, Path(args.path), args.yes)
    tool.run()


pip install --upgrade google-api-python-client google-auth-httplib2 google-auth-oauthlib
pip install argcomplete


import argcomplete
argcomplete.autocomplete(parse)
