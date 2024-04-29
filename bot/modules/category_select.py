#!/usr/bin/env python3

# Import necessary modules
import argparse
import asyncio
import time
from typing import Dict, Any, Optional

# Define a function to handle the incoming request
async def handle_request(request: Dict[str, Any], timeout: float) -> Optional[Dict[str, Any]]:
    # Set the start time for the request
    start_time = time.monotonic()
    # Simulate some work being done
    await asyncio.sleep(timeout)
    # Calculate the elapsed time for the request
    elapsed_time = time.monotonic() - start_time
    # Return the result of the request with the elapsed time
    return {"result": "success", "elapsed_time": elapsed_time}

# Define a function to parse command line arguments
def parse_args() -> argparse.Namespace:
    # Create a new argument parser
    parser = argparse.ArgumentParser()
    # Add a required argument for the number of requests
    parser.add_argument("num_requests", type=int, help="Number of requests to simulate")
    # Add an optional argument for the timeout duration
    parser.add_argument("-t", "--timeout", type=float, default=1.0, help="Timeout duration for each request (default: 1.0)")
    # Parse the command line arguments
    args = parser.parse_args()
    # Return the parsed arguments
    return args

# Define the main function to run the script
async def main(num_requests: int, timeout: float):
    # Create a new event loop
    loop = asyncio.get_event_loop()
    # Create a new Semaphore with a limit of 5 concurrent requests
    semaphore = asyncio.Semaphore(5)
    # Create a list to store the results of each request
    results = []
    # Loop over the number of requests
    for i in range(num_requests):
        # Acquire the semaphore before making a request
        await semaphore.acquire()
        # Create a new task to handle the request
        task = asyncio.create_task(handle_request({"request_id": i}, timeout))
        # Register the task to be cancelled when the request is complete
        task.add_done_callback(semaphore.release)
        # Add the result of the task to the results list when it's complete
        results.append(await task)
    # Print the results of each request
    for result in results:
        print(result)

# Call the main function with the parsed command line arguments
if __name__ == "__main__":
    args = parse_args()
    asyncio.run(main(args.num_requests, args.timeout))
