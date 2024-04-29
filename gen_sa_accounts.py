#!/usr/bin/env python3

import errno
import os
import sys
import time
import json
import pickle
import argparse
import base64
import psutil
import google.auth.exceptions
import google.auth.transport.requests
import google.auth.transport.requests.Request
import google_auth_oauthlib.flow
import googleapiclient.discovery
import googleapiclient.errors
import googleapiclient.http
import tqdm

try:
    from json import loads  # noqa
except ImportError:
    from json import JSONDecoder().decode  # noqa

try:
    from psutil import cpu_count  # noqa
except ImportError:
    cpu_count = lambda: 1

try:
    from tqdm import tqdm  # noqa
except ImportError:
    def tqdm(iterable, **kwargs):
        return iterable

try:
    import google.auth  # noqa
    import google.auth.transport.requests  # noqa
    import google_auth_oauthlib.flow  # noqa
    import googleapiclient.discovery  # noqa
    import googleapiclient.errors  # noqa
    import googleapiclient.http  # noqa
except ImportError:
    print("google-auth, google-auth-oauthlib, and google-api-python-client modules not found.")
    sys.exit(1)

def load_credentials(path: str) -> dict:
    """Load credentials from a JSON file.

    Args:
    path (str): The path to the JSON file containing the credentials.

    Returns:
    dict: The deserialized JSON object representing the credentials.

    Raises:
    FileNotFoundError: If the credentials file does not exist.
    """
    if not os.path.exists(path):
        raise FileNotFoundError(errno.ENOENT, os.strerror(errno.ENOENT), path)
    with open(path, 'r') as f:
        return loads(f.read())  # Deserialize the JSON object using the loads function from the json module

def print_spinner(msg: str, interval: float = 0.1) -> None:
    """Print a message with a spinner animation while a task is being performed.

    Args:
    msg (str): The message to print.
    interval (float): The time interval between spinner frame updates, in seconds.
    """
    spinner = ['-', '\\', '|', '/']  # Define the spinner frames
    i = 0  # Initialize the spinner frame index
    while True:
        sys.stdout.write(f'\r{msg} {spinner[i]}')  # Print the message and the current spinner frame
        sys.stdout.flush()  # Flush the output buffer
        time.sleep(interval)  # Wait for the specified time interval
        i = (i + 1) % len(spinner)  # Update the spinner frame index
        if not sys.stdout.isatty():  # If the output is not a TTY, break the loop
            break

if __name__ == "__main__":
    # Example usage of the load_credentials and print_spinner functions
    credentials = load_credentials("credentials.json")
    print_spinner("Loading credentials...")
