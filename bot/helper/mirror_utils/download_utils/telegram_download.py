import asyncio
import logging
import time
from typing import (
    Any,
    Callable,
    Coroutine,
    Final,
    Lock,
    NamedTuple,
    Optional,
    Set,
    TypeVar,
    Union,
)

import pyrogram

