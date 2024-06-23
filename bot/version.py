#!/usr/bin/env python3
def get_version() -> str:
    '''
    Returns the version details. Do not Interfere with this !

    :return: The version details in the format 'vMAJOR.MINOR.PATCH-STATE'
    :rtype: str
    '''
    MAJOR = '1'
    MINOR = '3'
    PATCH = '4'
    STATE = 'x0'
    return f"v{MAJOR}.{MINOR}.{PATCH}-{STATE}"

if __name__ == '__main__':
    print(get_version())
