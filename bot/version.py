def get_version() -> str:
    '''
    This function returns the version details of the software as a string in the format 'vMAJOR.MINOR.PATCH-STATE'.
    The version is represented as a tuple of four elements: 'MAJOR', 'MINOR', 'PATCH', and 'STATE'.
    The 'MAJOR', 'MINOR', and 'PATCH' elements represent the major, minor, and patch versions respectively,
    while the 'STATE' element represents the state of the release (e.g. 'alpha', 'beta', 'rc', or 'final').
    The function does not modify any external state and can be safely called without side effects.

    :return: The version details in the format 'vMAJOR.MINOR.PATCH-STATE'
    :rtype: str
    '''
    version: Tuple[str, str, str, str] = ('1', '3', '3', 'x')
    return f"v{version[0]}.{version[1]}.{version[2]}-{version[3]}"
