#!/usr/bin/env python3
import asyncio
import os
import sys
import textwrap
from io import StringIO
from re import match
from traceback import format_exc
from aiofiles import open as aioopen
from pyrogram.handlers import MessageHandler
from pyrogram.filters import command
from pyrogram.errors import FloodWait
from contextlib import redirect_stdout, suppress
from bot.helper.telegram_helper.filters import CustomFilters
from bot.helper.telegram_helper.bot_commands import BotCommands
from bot.helper.telegram_helper.message_utils import sendFile, sendMessage
from bot.helper.ext_utils.bot_utils import new_task

namespaces = {}

def namespace_of(message):
    if message.chat.id not in namespaces:
        namespaces[message.chat.id] = {
            '__builtins__': globals()['__builtins__'],
            'bot': bot,
            'message': message,
            'user': user,
        }
    return namespaces[message.chat.id]


async def log_input(message):
    LOGGER.info(f"INPUT: {message.text} (User ID ={message.from_user.id} | Chat ID ={message.chat.id})")


async def send(msg, message):
    if len(str(msg)) > 2000:
        with BytesIO(str.encode(msg)) as out_file:
            out_file.name = "output.txt"
            await sendFile(message, out_file)
    else:
        LOGGER.info(f"OUTPUT: '{msg}'")
        if not msg or msg == '\n':
            msg = "MessageEmpty"
        elif not bool(match(r'<(spoiler|b|i|code|s|u|/a)>', msg)):
            msg = f"<code>{msg}</code>"
        await sendMessage(message, msg)


@new_task
async def evaluate(client, message):
    await log_input(message)
    content = message.text.split(maxsplit=1)[-1]
    body = content.strip('` \n')
    env = namespace_of(message)

    try:
        with redirect_stdout(StringIO()) as stdout:
            exec(compile(f'async def func():\n{textwrap.indent(body, "  ")}', '<string>', 'exec'), env)
            func = env['func']
            func_return = await func()
    except Exception as e:
        return await send(f'{e.__class__.__name__}: {e}', message)

    result = None
    if func_return is None:
        try:
            result = str(eval(body, env))
        except Exception as e:
            result = f'{format_exc()}'
    else:
        result = str(func_return)

    if result:
        await send(result, message)


@new_task
async def execute(client, message):
    await log_input(message)
    content = message.text.split(maxsplit=1)[-1]
    body = content.strip('` \n')
    env = namespace_of(message)

    try:
        with redirect_stdout(StringIO()) as stdout:
            exec(compile(f'def func():\n{textwrap.indent(body, "  ")}', '<string>', 'exec'), env)
            func = env['func']
            func_return = func()
    except Exception as e:
        return await send(f'{e.__class__.__name__}: {e}', message)

    result = None
    if func_return is None:
        try:
            result = str(eval(body, env))
        except Exception as e:
            result = f'{format_exc()}'
    else:
        result = str(func_return)

    if result:
        await send(result, message)


@new_task
async def clear(client, message):
    await log_input(message)
    if message.chat.id in namespaces:
        del namespaces[message.chat.id]
        await send("<b>Cached Locals Cleared !</b>", message)
    else:
        await send("<b>No Cache Locals Found !</b>", message)


bot.add_handler(MessageHandler(evaluate, filters=command(
    BotCommands.EvalCommand) & CustomFilters.sudo))
bot.add_handler(MessageHandler(execute, filters=command(
    BotCommands.ExecCommand) & CustomFilters.sudo))
bot.add_handler(MessageHandler(clear, filters=command(
    BotCommands.ClearLocalsCommand) & CustomFilters.sudo))

