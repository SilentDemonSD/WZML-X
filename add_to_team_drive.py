from __future__ import print_function  # Enable print function for Python 2.x

# Import required libraries and modules
from google.oauth2.service_account import Credentials
import googleapiclient.discovery
import json
import progress.bar  # Progress bar module for displaying the processing progress
import glob
import sys
import argparse
import time
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
import os
import pickle

# Start the timer
stt = time.time()

# Initialize the argument parser
parse = argparse.ArgumentParser(
    description='A tool to add service accounts to a shared drive from a folder containing credential files.')

# Define and add arguments
parse.add_argument('--path', '-p', default='accounts',
                   help='Specify an alternative path to the service accounts folder.')
parse.add_argument('--credentials', '-c', default='./credentials.json',
                   help='Specify the relative path for the credentials file.')
parse.add_argument('--yes', '-y', default=False,
                   action='store_true', help='Skips the sanity prompt.')
parsereq = parse.add_argument_group('required arguments')
parsereq.add_argument('--drive-id', '-d',
                      help='The ID of the Shared Drive.', required=True)

# Parse the arguments
args = parse.parse_args()

# Set the path for the service accounts folder
acc_dir = args.path

# Get the ID of the shared drive
did = args.drive_id

# Find the credentials file
credentials = glob.glob(args.credentials)

# Check if the credentials file exists
try:
    open(credentials[0], 'r')
    print('>> Found credentials.')
except IndexError:
    print('>> No credentials found.')
    sys.exit(0)

# Prompt the user for confirmation if the --yes flag is not set
if not args.yes:
    input('>> Make sure the **Google account** that has generated credentials.json\n   is added into your Team Drive '
          '(shared drive) as Manager\n>> (Press any key to continue)')

# Initialize the credentials object
creds = None

# Check if the token pickle file exists
if os.path.exists('token_sa.pickle'):
    # Load the credentials from the token pickle file
    with open('token_sa.pickle', 'rb') as token:
        creds = pickle.load(token)

# If the credentials are not valid, refresh or obtain new credentials
if not creds or not creds.valid:
    if creds and creds.expired and creds.refresh_token:
        # Refresh the credentials
        creds.refresh(Request())
    else:
        # Obtain new credentials
        flow = InstalledAppFlow.from_client_secrets_file(credentials[0], scopes=[
            'https://www.googleapis.com/auth/admin.directory.group',
            'https://www.googleapis.com/auth/admin.directory.group.member'
        ])
        # Run the flow to get the credentials
        creds = flow.run_console()
    # Save the credentials for the next run
    with open('token_sa.pickle', 'wb') as token:
        pickle.dump(creds, token)

# Initialize the Google Drive API client
drive = googleapiclient.discovery.build("drive", "v3", credentials=creds)

# Initialize the batch request
batch = drive.new_batch_http_request()

# Find all service account JSON files in the specified folder
aa = glob.glob('%s/*.json' % acc_dir)

# Initialize the progress bar
pbar = progress.bar.Bar("Readying accounts", max=len(aa))

# Process each service account JSON file
for i in aa:
    # Extract the client email from the JSON file
    ce = json.loads(open(i, 'r').read())['client_email']

    # Add a permission for the service account on the shared drive
    batch.add(drive.permissions().create(fileId=did, supportsAllDrives=True, body={
        "role": "organizer",
        "type": "user",
        "emailAddress": ce
    }))

    # Update the progress bar
    pbar.next()

# Finish the progress bar
pbar.finish()

# Execute the batch request
print('Adding...')
batch.execute()

# Print completion message
print('Complete.')

# Calculate and print the elapsed time
hours, rem = divmod((time.time() - stt), 3600)
minutes, sec = divmod(rem, 60)
print("Elapsed Time:\n{:0>2}:{:0>2}:{:05.2f}".format(
    int(hours), int(minutes), sec))
