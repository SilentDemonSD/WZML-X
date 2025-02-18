from os.path import exists
import pickle

from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow

TOKEN_FILE = "token.pickle"
OAUTH_SCOPE = ["https://www.googleapis.com/auth/drive"]

def load_credentials(token_file: str):
    if exists(token_file):
        try:
            with open(token_file, "rb") as f:
                creds = pickle.load(f)
                return creds
        except Exception as e:
            print(f"Error loading credentials: {e}")
    return None

def save_credentials(token_file: str, credentials) -> None:
    try:
        with open(token_file, "wb") as f:
            pickle.dump(credentials, f)
    except Exception as e:
        print(f"Error saving credentials: {e}")

def get_credentials():
    credentials = load_credentials(TOKEN_FILE)
    if credentials and credentials.valid:
        return credentials

    if credentials and credentials.expired and credentials.refresh_token:
        try:
            credentials.refresh(Request())
            return credentials
        except Exception as e:
            print(f"Error refreshing credentials: {e}")

    try:
        flow = InstalledAppFlow.from_client_secrets_file("credentials.json", OAUTH_SCOPE)
        credentials = flow.run_local_server(port=0, open_browser=False)
    except Exception as e:
        print(f"Error during OAuth flow: {e}")
        raise

    return credentials

def main():
    try:
        credentials = get_credentials()
        save_credentials(TOKEN_FILE, credentials)
    except Exception as e:
        print(f"Failed to obtain credentials: {e}")

if __name__ == "__main__":
    main()
