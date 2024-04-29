import pickle
import os
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

def load_and_refresh_credentials():
    """Loads and refreshes the Google Drive credentials if necessary.

    Returns:
        google.oauth2.credentials.Credentials: The Google Drive credentials.
    """
    credentials = None
    __G_DRIVE_TOKEN_FILE = "token.pickle"

    if os.path.exists(__G_DRIVE_TOKEN_FILE):
        try:
            with open(__G_DRIVE_TOKEN_FILE, 'rb') as f:
                credentials = pickle.load(f)

                if (
                    credentials is not None
                    and not credentials.valid
                    and credentials.expired
                    and credentials.refresh_token
                ):
                    credentials.refresh(Request())
        except Exception as e:
            print(f"Error loading credentials: {e}")

    if credentials is None:
        __OAUTH_SCOPE = ["https://www.googleapis.com/auth/drive"]
        flow = InstalledAppFlow.from_client_secrets_file(
            'credentials.json', __OAUTH_SCOPE)
        try:
            credentials = flow.run_local_server(port=0, open_browser=False)
        except Exception as e:
            print(f"Error running local server: {e}")

    # Save the credentials for the next run
    try:
        with open(__G_DRIVE_TOKEN_FILE, 'wb') as token:
            pickle.dump(credentials, token)
    except Exception as e:
        print(f"Error saving credentials: {e}")

    return credentials

if __name__ == "__main__":
    load_and_refresh_credentials()
