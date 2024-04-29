import asyncio  # Importing the asyncio library for asynchronous programming
import logging  # Importing the logging library for logging purposes

# Setting up the logger
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')

async def main():
    # Using asyncio.gather to run multiple coroutines concurrently
    await asyncio.gather(
        task1(),
        task2(),
        task3()
    )

async def task1():
    logging.info('Task 1 started')
    await asyncio.sleep(1)
    logging.info('Task 1 completed')

async def task2():
    logging.info('Task 2 started')
    await asyncio.sleep(2)
    logging.info('Task 2 completed')

async def task3():
    logging.info('Task 3 started')
    await asyncio.sleep(3)
    logging.info('Task 3 completed')

if __name__ == "__main__":
    # Running the main function
    start_time = time.perf_counter()
    asyncio.run(main())
    end_time = time.perf_counter()
    logging.info(f'Total time taken: {end_time - start_time:.4f} seconds')
