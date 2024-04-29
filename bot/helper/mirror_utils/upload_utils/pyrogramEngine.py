#!/usr/bin/env python3

import os
import asyncio
import time
from traceback import format_exc
from logging import getLogger, ERROR, basicConfig
from typing import List, Any

__version__ = "0.1.0"
__author__ = "Your Name"

# Initialize the logger
basicConfig(level=ERROR)
logger = getLogger(__name__)

async def process_file(file_path: str) -> float:
    """
    Process a file by reading its content and returning the file size in MB.
    """
    if not os.path.isfile(file_path):
        logger.error(f"File '{file_path}' does not exist.")
        return None

    async with aiofiles.open(file_path, 'rb') as f:
        content = await f.read()

    file_size_mb = len(content) / (1024 * 1024)
    return file_size_mb

async def main(file_paths: List[str]) -> List[Any]:
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
