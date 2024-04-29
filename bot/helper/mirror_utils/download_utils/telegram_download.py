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

def main(
    tasks: TaskSet,
    max_workers: int = 3,
    logger: OptionalLogger = logging.getLogger(__name__),
    lock: OptionalLock = asyncio.Lock(),
) -> None:
    # Set up our final logger and lock
    final_logger: FinalLogger = logger
    final_lock: FinalLock = lock

    # Create a list of tasks from our set of tasks
    task_list: list[asyncio.Task] = [
        asyncio.create_task(task()) for task in tasks
    ]

    # Set up a loop to check the status of our tasks
    while True:
        # Get the current time
        current_time: float = time.monotonic()

        # Get the status of all our tasks
        task_statuses: list[TaskEvent] = [
            TaskEvent(task_name, task.done()) for task_name, task in zip(tasks, task_list)
        ]

        # Print the status of all our tasks
        for task_status in task_statuses:
            final_logger.info(f"Task {task_status.task_name}: {task_status.status}")

        # If all our tasks are done, break out of the loop
        if all(task_status.status for task_status in task_statuses):
            break

        # Wait for a short period of time before checking again
        await asyncio.sleep(1)

    # Close our lock
    final_lock.release()

if __name__ == "__main__":
    # Define our set of tasks
    tasks: TaskSet = {some_task, another_task, yet_another_task}

    # Run our main function
    asyncio.run(
        main(
            tasks,
            max_workers=3,
            logger=logging.getLogger(__name__),
            lock=asyncio.Lock(),
        )
    )
