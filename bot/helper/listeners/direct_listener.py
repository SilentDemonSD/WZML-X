import aiohttp
import asyncio
from functools import wraps

import logging

logger = logging.getLogger(__name__)

async def aiohttp_get(*args, **kwargs):
    async with aiohttp.ClientSession() as session:
        async with session.get(*args, **kwargs) as response:
            return await response.text()

def aio_to_sync(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        return asyncio.run(func(*args, **kwargs))
    return wrapper

@aio_to_sync
async def download_file(url, output_file):
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            content_length = int(response.headers['Content-Length'])
            with open(output_file, 'wb') as f:
                while True:
                    chunk = await response.content.read(4096)
                    if not chunk:
                        break
                    f.write(chunk)
                    percentage = (f.tell() / content_length) * 100
                    logger.info(f"Downloaded {percentage:.2f}%")

