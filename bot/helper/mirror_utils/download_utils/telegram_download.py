import asyncio
import atexit
import logging
import time
from contextlib import asynccontextmanager
from typing import (
    Any,
    AsyncContextManager,
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

# Set up logging
logging.basicConfig(level=logging.INFO)

# Define a custom event for our task
class TaskEvent(NamedTuple):
    task_name: str
    status: str

# Define a type for our coroutine functions
TaskCoroutine = Callable[[Any], Coroutine]

# Define a type for our lock
LockType = Lock

# Define a type for our set of tasks
TaskSet = Set[TaskCoroutine]

# Define a type for our optional logger
OptionalLogger = Optional[logging.Logger]

# Define a type for our final logger
FinalLogger = Final[logging.Logger]

# Define a type for our optional lock
OptionalLock = Optional[LockType]

# Define a type for our final lock
FinalLock = Final[LockType]

@asynccontextmanager
async def acquire_lock() -> AsyncContextManager[LockType]:
    lock = asyncio.Lock()
    atexit.register(lock.release)
    async with lock:
        yield lock

async def main(
    tasks: TaskSet,
    max_workers: int = 3,
    logger: OptionalLogger = logging.getLogger(__name__),
    lock: OptionalLock = None,
) -> None:
    # Set up our final logger and lock
    final_logger: FinalLogger = logger
    final_lock: FinalLock = lock or await acquire_lock()

    # Create a list of tasks from our set of tasks
    task_list: list[asyncio.Task] = [
        asyncio.create_task(task()) for task in tasks
    ]

    # Wait for all tasks to complete
    done, pending = await asyncio.wait(task_list, return_when=asyncio.ALL_COMPLETED)

    # Print the status of all completed tasks
    for task in done:
        final_logger.info(f"Task {task.get_name()}: done")

    # Print the status of all pending tasks
    for task in pending:
        final_logger.info(f"Task {task.get_name()}: pending")

if __name__ == "__main__":
    # Define our set of tasks
    tasks: TaskSet = {pyrogram.Client.start, pyrogram.Client.stop}

    # Run our main function
    asyncio.run(
        main(
            tasks,
            max_workers=3,
            logger=logging.getLogger(__name__),
            lock=None,
        )
    )
