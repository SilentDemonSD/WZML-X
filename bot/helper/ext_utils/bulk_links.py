#!/usr/bin/env python3

import pathlib
from typing import List, Union  # Importing List and Union types from the typing module

import aiofiles
from aiofiles.os import remove  # Importing the 'remove' function from aiofiles.os
from telegram import Message, Document, ReplyKeyboardRemove  # Importing Message, Document, and ReplyKeyboardRemove classes from the telegram module

# The following function is an asynchronous generator function that yields chunks of data from a file-like object
async def chunks(aws_file):
    while True:
        chunk = await aws_file.read(4096)  # Reading 4096 bytes from the file-like object
        if not chunk:
            break
        yield chunk  # Yielding the chunk of data

# The following function is an asynchronous function that downloads a file from AWS S3 and saves it to the local file system
async def download_file_from_s3(bucket_name: str, file_key: str, file_path: pathlib.Path):
    async with aiofiles.open(file_path, 'wb') as local_file:  # Opening the local file in write-binary mode
        async for chunk in chunks(await s3.get_object(Bucket=bucket_name, Key=file_key)['Body']):  # Downloading the file in chunks
            await local_file.write(chunk)  # Writing each chunk to the local file

# The following function is an asynchronous function that sends a message and a file to a Telegram chat
async def send_message_and_file(chat_id: int, message: Message, document: Document):
    await message.reply_text('File attached:', reply_markup=ReplyKeyboardRemove())  # Replying to the message with the text 'File attached:'
    await message.reply_document(document)  # Sending the file as a document

# The following function is an asynchronous function that deletes a file from the local file system
async def delete_file(file_path: pathlib.Path):
    await remove(file_path)  # Deleting the file
