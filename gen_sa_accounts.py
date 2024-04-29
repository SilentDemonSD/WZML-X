import argparse
import errno
import os
import pickle
import sys
from base64 import b64decode
from glob import glob
from json import loads
from random import choice
from time import sleep

from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

SCOPES = [
    'https://www.googleapis.com/auth/drive',
    'https://www.googleapis.com/auth/cloud-platform',
    'https://www.googleapis.com/auth/iam'
]

def create_accounts(service: build, project: str, count: int) -> None:
    """Create service accounts in a project.

    Args:
        service (build): Google Cloud Resource Manager service client.
        project (str): Project ID to create service accounts in.
        count (int): Number of service accounts to create.
    """
    batch = service.new_batch_http_request()
    for _ in range(count):
        aid = generate_id('mfc-')
        request = service.projects().serviceAccounts().create(
            name='projects/' + project,
            body={'accountId': aid, 'serviceAccount': {'displayName': aid}}
        )
        batch.add(request)
    batch.execute()

def create_remaining_accounts(iam: build, project: str) -> None:
    """Create service accounts in a project until there are 100.

    Args:
        iam (build): Google IAM service client.
        project (str): Project ID to create service accounts in.
    """
    print(f'Creating accounts in {project}')
    sa_count = len(list_sas(iam, project))
    while sa_count != 100:
        create_accounts(iam, project, 100 - sa_count)
        sa_count = len(list_sas(iam, project))

def generate_id(prefix: str = 'saf-') -> str:
    """Generate a random ID.

    Args:
        prefix (str, optional): Prefix for the ID. Defaults to 'saf-'.

    Returns:
        str: Random ID with the given prefix.
    """
    chars = '-abcdefghijklmnopqrstuvwxyz1234567890'
    return prefix + ''.join(choice(chars) for _ in range(25)) + choice(chars[1:])

def get_projects(service: build) -> list[str]:
    """List all projects visible to the user.

    Args:
        service (build): Google Cloud Resource Manager service client.

    Returns:
        list[str]: List of project IDs.
    """
    return [i['projectId'] for i in service.projects().list().execute()['projects']]

def def_batch_resp(id: int, resp: dict, exception: HttpError) -> None:
    """Default batch request callback.

    Args:

