from typing import NamedTuple

class Version(NamedTuple):
    major: str
    minor: str
    patch: str
    state: str

def get_version() -> str:
    '''
    This function returns the version details of the software as a string in the format 'vMAJOR.MINOR.PATCH-STATE'.
    The version is represented as a named tuple of four elements: 'major', 'minor', 'patch', and 'state'.
    The 'major', 'minor', and 'patch' elements represent the major, minor, and patch versions respectively,
    while the 'state' element represents the state of the release (e.g. 'alpha', 'beta', 'rc', or 'final').
    The function does not modify any external state and can be safely called without side effects.

    :return: The version details in the format 'vMAJOR.MINOR.PATCH-STATE'
    :rtype: str
    '''
    version = Version('1', '3', '3', 'x')
    return f"v{version.major}.{version.minor}.{version.patch}-{version.state}"
