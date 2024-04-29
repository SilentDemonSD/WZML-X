import pickle
import os
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

def load_credentials():
    """Loads the Google Drive credentials from the file.

    Returns:
        Credentials or None: The Google Drive credentials or None if not found.
    """
    credentials = None
    token_file = "token.pickle"

    if os.path.exists(token_file):
        with open(token_file, 'rb') as f:
            try:
                credentials = pickle.load(f)
            except Exception as e:
                print(f"Error loading credentials from file: {e}")

    return credentials

def refresh_and_save_credentials():
    """Refreshes the Google Drive credentials if necessary and saves them to the file.
    """
    credentials = load_credentials()
    oauth_scope = ["https://www.googleapis.com/auth/drive"]

    if credentials is None:
        flow = InstalledAppFlow.from_client_secrets_file(
            'credentials.json', oauth_scope)
        try:
            credentials = flow.run_local_server(port=0, open_browser=False)
        except Exception as e:
            print(f"Error running local server: {e}")

    if credentials and credentials.expired and credentials.refresh_token:
        try:
            credentials.refresh(Request())
        except Exception as e:
            print(f"Error refreshing credentials: {e}")

    if credentials:
        try:
            with open("token.pickle", 'wb') as token:
                pickle.dump(credentials, token)
        except Exception as e:
            print(f"Error saving credentials: {e}")

if __name__ == "__main__":
    refresh_and_save_credentials()
