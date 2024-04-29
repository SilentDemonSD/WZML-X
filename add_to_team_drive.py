import sys
import time
import argparse
import glob
import pickle
import progress.bar
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

def load_json_file(file_path):
    try:
        with open(file_path, 'r') as file:
            return json.load(file)
    except Exception as e:
        print(f'Error loading JSON file: {e}')
        sys.exit(1)

def get_service_account_emails(account_folder):
    service_account_files = glob.glob(f'{account_folder}/*.json')
    service_account_emails = []

    for file in service_account_files:
        data = load_json_file(file)
        service_account_emails.append(data['client_email'])

    return service_account_emails

def get_drive_service(credentials_file, scopes):
    creds = None

    if os.path.exists('token_sa.pickle'):
        with open('token_sa.pickle', 'rb') as token:
            creds = pickle.load(token)

    if not creds or not creds.valid:
        flow = InstalledAppFlow.from_client_secrets_file(credentials_file, scopes)
        creds = flow.run_console()

        with open('token_sa.pickle', 'wb') as token:
            pickle.dump(creds, token)

    return build("drive", "v3", credentials=creds)

def main():
    start_time = time.time()

    parser = argparse.ArgumentParser(description='A tool to add service accounts to a shared drive from a folder containing credential files.')
    parser.add_argument('--path', '-p', default='accounts', help='Specify an alternative path to the service accounts folder.')
    parser.add_argument('--credentials', '-c', default='./credentials.json', help='Specify the relative path for the credentials file.')
    parser.add_argument('--yes', '-y', default=False, action='store_true', help='Skips the sanity prompt.')
    parser.add_argument('--drive-id', '-d', help='The ID of the Shared Drive.', required=True)

    args = parser.parse_args()

    account_folder = args.path
    drive_id = args.drive_id
    credentials_file = args.credentials
    scopes = ['https://www.googleapis.com/auth/admin.directory.group', 'https://www.googleapis.com/auth/admin.directory.group.member']

    if not os.path.exists(account_folder):
        print(f'Error: The specified account folder "{account_folder}" does not exist.')
        sys.exit(1)

    if not os.path.exists(credentials_file):
        print(f'Error: The specified credentials file "{credentials_file}" does not exist.')
        sys.exit(1)

    if not args.yes:
        input('>> Make sure the **Google account** that has generated credentials.json\n   is added into your Team Drive (shared drive) as Manager\n>> (Press any key to continue)')

    drive_service = get_drive_service(credentials_file, scopes)

    service_account_emails = get_service_account_emails(account_folder)

    batch = drive_service.new_batch_http_request()

    pbar = progress.bar.Bar("Readying accounts", max=len(service_account_emails))

    for email in service_account_emails:
        batch.add(drive_service.permissions().create(fileId=drive_id, supportsAllDrives=True, body={
            "role": "organizer",
            "type": "user",
            "emailAddress": email
        }))

        pbar.next()

    pbar.finish()

    print('Adding...')
    batch.execute()
    print('Complete.')

    elapsed_time = time.time() - start_time
    hours, rem = divmod(elapsed_time, 3600)
    minutes, sec = divmod(rem, 60)
    print(f"Elapsed Time: {int(hours)}:{int(minutes)}:{sec:.2f}")

if __name__ == '__main__':
    main()
