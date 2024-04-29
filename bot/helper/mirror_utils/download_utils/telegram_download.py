import asyncio
import atexit
import logging
import time
from contextlib import asynccontextmanager
from typing import (
    Any,
    AsyncContextManager,
    Callable,
)


@asynccontextmanager
async def timed(coroutine: Callable[..., Any], *args: Any, **kwargs: Any) -> AsyncContextManager[Any]:
    """
    Asynchronous context manager that times the execution of a coroutine.

    Args:
        coroutine (Callable[..., Any]): The coroutine to time.
        *args (Any): Positional arguments to pass to the coroutine.
        **kwargs (Any): Keyword arguments to pass to the coroutine.

    Yields:
        Any: The result of the coroutine.

    """
    start_time = time.perf_counter()
    result = await coroutine(*args, **kwargs)
    end_time = time.perf_counter()
    logging.info(f"Coroutine '{coroutine.__name__}' took {end_time - start_time:.4f} seconds - {time.asctime()}")
    yield result


async def main() -> None:
    """
    Simple asynchronous function that waits for 1 second.

    """
    logging.basicConfig(level=logging.INFO)
    await asyncio.sleep(1)


if __name__ == "__main__":
    # Set up atexit to close the event loop when the program exits.
    loop = asyncio.get_event_loop()
    atexit.register(loop.close)

    # Run the main function using the event loop.
    try:
        loop.run_until_complete(main())
    finally:
        loop.run_until_complete(loop.shutdown_asyncgens())
        loop.close()
