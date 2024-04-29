#!/usr/bin/env python3

import os
import asyncio
import time
from traceback import format_exc
from logging import getLogger, ERROR
import aiofiles

# Initialize the logger
logger = getLogger(__name__)
logger.setLevel(ERROR)

async def process_file(file_path):
    """
    Process a file by reading its content and doing some computation.
    This is an example function, you can replace it with your own logic.
    """
    async with aiofiles.open(file_path, 'r') as f:
        content = await f.read()
    # Do some computation with the file content
    result = sum(1 for _ in content)
    return result

async def main(file_paths):
    """
    The main function that processes a list of file paths asynchronously.
    """
    tasks = [process_file(file_path) for file_path in file_paths]
    results = await asyncio.gather(*tasks)
    return results

if __name__ == "__main__":
    # Replace this with the list of file paths you want to process
    file_paths = ["file1.txt", "file2.txt", "file3.txt"]

    # Run the main function asynchronously
    loop = asyncio.get_event_loop()
    try:
        start_time = time.time()
        results = loop.run_until_complete(main(file_paths))
        end_time = time.time()
        print(f"Results: {results}")
        print(f"Total time taken: {end_time - start_time:.4f} seconds")
    except Exception as e:
        logger.error(format_exc())
    finally:
        loop.close()
