import errno  # Import the errno module for handling error numbers
import os  # Import the os module for interacting with the operating system
import pickle  # Import the pickle module for serializing and deserializing Python object structures
import sys  # Import the sys module for interacting with the Python runtime environment
import time  # Import the time module for measuring elapsed time

from argparse import ArgumentParser  # Import the ArgumentParser class for parsing command-line options
from base64 import b64decode  # Import the b64decode function for decoding base64-encoded strings
from contextlib import contextmanager  # Import the contextmanager decorator for creating context managers
from glob import glob  # Import the glob function for searching for files that match a specified pattern
from google.auth.exceptions import TransportError  # Import the TransportError exception for handling transport-related errors
from google.auth.transport.requests import Request  # Import the Request class for making HTTP requests
from google_auth_oauthlib.flow import InstalledAppFlow  # Import the InstalledAppFlow class for handling OAuth 2.0 flows for installed applications
from googleapiclient.discovery import build  # Import the build function for building API clients
from googleapiclient.errors import HttpError, ResourceNotFoundError, TooManyRequests  # Import various API client errors
from googleapiclient.http import HttpRequest  # Import the HttpRequest class for making HTTP requests
from psutil import cpu_count  # Import the cpu_count function for getting the number of processors in the system
from tqdm import tqdm  # Import the tqdm function for creating progress bars

# Define the scopes for the Google API credentials
SCOPES = [
    'https://www.googleapis.com/auth/drive',  # Drive API scope
    'https://www.googleapis.com/auth/cloud-platform',  # Google Cloud Platform scope
    'https://www.googleapis.com/auth/iam'  # Identity and Access Management scope
]


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
