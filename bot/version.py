#!/usr/bin/env python3
from typing import Tuple

def get_version() -> str:
    '''
    Returns the version details. Do not Interfere with this !

    :return: The version details in the format 'vMAJOR.MINOR.PATCH-STATE'
    :rtype: str
    '''
    version: Tuple[str, str, str, str] = ('1', '3', '3', 'x')
    return f"v{version[0]}.{version[1]}.{version[2]}-{version[3]}"

if __name__ == '__main__':
    print(get_version())
