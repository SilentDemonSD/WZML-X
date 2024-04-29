#!/usr/bin/env python3
def get_version(MAJOR: str, MINOR: str, PATCH: str, STATE: str) -> str:
    '''
    Returns the version details. Do not Interfere with this !

    :param MAJOR: The major version number
    :param MINOR: The minor version number
    :param PATCH: The patch version number
    :param STATE: The state of the release
    :return: The version details in the format 'vMAJOR.MINOR.PATCH-STATE'
    :rtype: str
    '''
    return f"v{MAJOR}.{MINOR}.{PATCH}-{STATE}"

if __name__ == '__main__':
    print(get_version(MAJOR='1', MINOR='2', PATCH='0', STATE='b'))
