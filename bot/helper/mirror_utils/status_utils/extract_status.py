#!/usr/bin/env python3
from pathlib import Path
from time import time, sleep
from typing import Optional

def current_time() -> float:
    """Returns the current time in seconds since the epoch."""
    return time()

if __name__ == "__main__":
    while True:
        print(current_time())
        sleep(1)
