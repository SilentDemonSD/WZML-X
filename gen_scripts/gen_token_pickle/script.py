#!/usr/bin/env python3
"""
Generate Google Drive OAuth Token

This script authenticates with Google Drive API and generates a token file
for use with other Google Drive-related scripts.
"""

import sys
import pickle
import socket

from os.path import exists
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow

CREDENTIALS_FILE = "../config/credentials.json"
TOKEN_FILE = "../tokens/token.pickle"
SCOPES = [
    "https://www.googleapis.com/auth/drive",
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube.readonly",
    "https://www.googleapis.com/auth/youtube.force-ssl",
]


def print_header(title: str) -> None:
    """Print a formatted header."""
    print("\n" + "=" * 50)
    print(f"  {title}")
    print("=" * 50)


def print_step(step: int, total: int, message: str) -> None:
    """Print a step indicator."""
    print(f"\n[{step}/{total}] {message}")


def port_available(port: int) -> bool:
    """Check if a port is available for use."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(("localhost", port)) != 0


def find_port(start: int = 8080, end: int = 8090) -> int:
    """Find an available port in the given range."""
    for port in range(start, end):
        if port_available(port):
            return port
    return None


def load_token() -> pickle:
    """Load existing token from file."""
    if not exists(TOKEN_FILE):
        return None
    try:
        with open(TOKEN_FILE, "rb") as f:
            return pickle.load(f)
    except Exception:
        return None


def save_token(creds) -> None:
    """Save credentials to token file."""
    try:
        with open(TOKEN_FILE, "wb") as f:
            pickle.dump(creds, f)
        print(f"\n[OK] Token saved to: {TOKEN_FILE}")
    except Exception as e:
        print(f"\n[ERROR] Failed to save token: {e}")
        sys.exit(1)


def refresh_token(creds) -> pickle:
    """Refresh expired credentials."""
    try:
        creds.refresh(Request())
        return creds
    except Exception:
        return None


def run_flow():
    """Run OAuth flow with browser and console fallback."""
    if not exists(CREDENTIALS_FILE):
        print("\n[ERROR] credentials.json not found!")
        print(f"\nPlease ensure '{CREDENTIALS_FILE}' exists.")
        print("\nTo get credentials:")
        print("1. Go to https://console.cloud.google.com/")
        print("2. Create a project or select existing")
        print("3. Enable Google Drive API")
        print("4. Create OAuth 2.0 credentials (Desktop app)")
        print("5. Download and save as 'credentials.json'")
        sys.exit(1)

    print("\n[INFO] Starting OAuth authentication...")
    flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)

    # Try browser-based auth first
    port = find_port()
    if port:
        try:
            print(f"[INFO] Waiting for authentication on port {port}...")
            return flow.run_local_server(port=port, prompt="consent")
        except Exception as e:
            print(f"[WARN] Browser auth failed: {e}")

    try:
        return flow.run_local_server(port=0, open_browser=False, prompt="consent")
    except Exception:
        print("\n[ERROR] OAuth authentication failed!")
        print("\nTroubleshooting:")
        print("- Check your credentials.json is valid")
        print("- Ensure Google Drive API is enabled")
        print("- Check your internet connection")
        sys.exit(1)


def get_credentials():
    """Get valid credentials, refreshing or regenerating if needed."""
    print_header("Google Drive Token Generator")

    # Step 1: Check for existing token
    print_step(1, 3, "Checking for existing token...")
    creds = load_token()

    if creds and creds.valid:
        print("[OK] Valid token found!")
        return creds

    # Step 2: Check if token can be refreshed
    if creds and creds.expired and creds.refresh_token:
        print("[INFO] Token expired. Attempting to refresh...")
        creds = refresh_token(creds)
        if creds:
            print("[OK] Token refreshed successfully!")
            save_token(creds)
            return creds

    # Step 3: Generate new token
    print_step(2, 3, "Generating new token...")
    creds = run_flow()
    save_token(creds)
    return creds


def main():
    try:
        print("\nThis script will authenticate with Google Drive API")
        print("and save a token for future use.\n")

        creds = get_credentials()

        print_step(3, 3, "Verification")
        if creds and creds.valid:
            print("\n" + "=" * 50)
            print("  SUCCESS! Token generated and saved.")
            print("=" * 50)
            print(f"\nToken location: {TOKEN_FILE}")
            print("\nYou can now use other scripts that require Google Drive access.")
        else:
            print("\n[ERROR] Failed to obtain valid credentials")
            sys.exit(1)

    except KeyboardInterrupt:
        print("\n\n[INFO] Cancelled by user.")
        sys.exit(0)
    except Exception as e:
        print(f"\n[ERROR] {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
