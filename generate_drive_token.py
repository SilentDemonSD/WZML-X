import pickle
import os
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

def get_google_drive_credentials() -> any:
    """
    Load or create Google Drive credentials.

    Returns:
        The Google Drive credentials object.
    """
    credential_file = "token.pickle"
    oauth_scope = ["https://www.googleapis.com/auth/drive"]

    # Load credentials from file
    if os.path.exists(credential_file):
        with open(credential_file, 'rb') as f:
            credentials = pickle.load(f)

            # Check if credentials are valid
            if (
                credentials is not None
                and credentials.valid
            ):
                return credentials

            # Refresh expired credentials
            if (
                credentials is not None
                and credentials.expired
                and credentials.refresh_token
            ):
                credentials.refresh(Request())
                return credentials

    # Create credentials
    flow = InstalledAppFlow.from_client_secrets_file(
        'credentials.json', oauth_scope)
    credentials = flow.run_local_server(port=0, open_browser=False)

    # Save credentials for the next run
    try:
        with open(credential_file, 'wb') as token:
            pickle.dump(credentials, token)
    except Exception as e:
        print(f"Error saving credentials: {e}")

    return credentials
