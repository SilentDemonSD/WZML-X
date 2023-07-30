#!/usr/bin/env python3

def get_version() -> str:
    'Version Control Modulation'
    MAJOR = '1'
    MINOR = '2'
    PATCH = '0'
    STATE = 'x'
    return f"v{MAJOR}.{MINOR}.{PATCH}-{STATE}"