#!/usr/bin/env python3

def get_version() -> str:
    """
    Returns the version details in the format 'vMAJOR.MINOR.PATCH-STATE'.

    :return: The version details as a string.
    :rtype: str
    """
    major: str = '1'
    minor: str = '3'
    patch: str = '4'
    state: str = 'a0'

    return f"v{major}.{minor}.{patch}-{state}"

if __name__ == '__main__':
    print(get_version())
