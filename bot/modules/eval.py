#!/usr/bin/env python3
from swibots import CommandHandler
from pyrogram.handlers import MessageHandler
from pyrogram.filters import command
from os import path as ospath, getcwd, chdir
from aiofiles import open as aiopen
from traceback import format_exc
from textwrap import indent
from io import StringIO, BytesIO
from re import match
from contextlib import redirect_stdout, suppress

from bot import LOGGER, bot, user, app
from bot.helper.tele_swi_helper.filters import CustomFilters
from bot.helper.tele_swi_helper.bot_commands import BotCommands
from bot.helper.tele_swi_helper.message_utils import sendFile, sendMessage
from bot.helper.ext_utils.bot_utils import new_task

namespaces = {}

def namespace_of(message, isSwitch):
    chat_id = message.group_id or message.user_id if isSwitch else message.chat.id
    if chat_id not in namespaces:
        namespaces[chat_id] = {
            '__builtins__': globals()['__builtins__'],
            'bot': bot,
            'message': message,
            'user': user,
            'app': app,
        }
    return namespaces[chat_id]


def log_input(message, isSwitch):
    chat_id = message.group_id or message.user_id if isSwitch else message.chat.id
    LOGGER.info(f"INPUT: {message.message if isSwitch else message.text} (User ID ={message.user_id if isSwitch else message.from_user.id} | Chat ID ={chat_id})")


async def send(msg, message, isSwitch=False):
    if len(str(msg)) > 2000:
        with BytesIO(str.encode(msg)) as out_file:
            out_file.name = "output.txt"
            await sendFile(message, out_file, isSwitch=isSwitch)
    else:
        LOGGER.info(f"OUTPUT: '{msg}'")
        if not msg or msg == '\n':
            msg = "MessageEmpty"
        elif not bool(match(r'<(spoiler|b|i|code|s|u|/a)>', msg)):
            msg = f"<code>{msg}</code>"
        await sendMessage(message, msg, isSwitch=isSwitch)


@new_task
async def evaluate(client, message=False):
    message = message if message else client.event.message
    await send(await do(eval, message, not message), message, not message)


@new_task
async def execute(client, message=False):
    message = message if message else client.event.message
    await send(await do(exec, message, not message), message, not message)


def cleanup_code(code):
    if code.startswith('```') and code.endswith('```'):
        return '\n'.join(code.split('\n')[1:-1])
    return code.strip('` \n')


async def do(func, message, isSwitch=False):
    log_input(message, isSwitch)
    content = (message.message if isSwitch else message.text).split(maxsplit=1)[-1]
    body = cleanup_code(content)
    env = namespace_of(message, isSwitch)

    chdir(getcwd())
    async with aiopen(ospath.join(getcwd(), 'bot/modules/temp.txt'), 'w') as temp:
        await temp.write(body)

    stdout = StringIO()

    to_compile = f'async def func():\n{indent(body, "  ")}'

    try:
        exec(to_compile, env)
    except Exception as e:
        return f'{e.__class__.__name__}: {e}'

    func = env['func']

    try:
        with redirect_stdout(stdout):
            func_return = await func()
    except Exception as e:
        value = stdout.getvalue()
        return f'{value}{format_exc()}'
    else:
        value = stdout.getvalue()
        result = None
        if func_return is None:
            if value:
                result = f'{value}'
            else:
                with suppress(Exception):
                    result = f'{repr(eval(body, env))}'
        else:
            result = f'{value}{func_return}'
        if result:
            return result


async def clear(client, message=False):
    message = message if message else client.event.message
    log_input(message)
    global namespaces
    chat_id = message.group_id or message.user_id if not message else message.chat.id
    if chat_id in namespaces:
        del namespaces[chat_id]
        await send("<b>Cached Locals Cleared !</b>", message)
    else:
        await send("<b>No Cache Locals Found !</b>", message)

if bot:
    bot.add_handler(MessageHandler(evaluate, filters=command(
        BotCommands.EvalCommand) & CustomFilters.sudo))
    bot.add_handler(MessageHandler(execute, filters=command(
        BotCommands.ExecCommand) & CustomFilters.sudo))
    bot.add_handler(MessageHandler(clear, filters=command(
        BotCommands.ClearLocalsCommand) & CustomFilters.sudo))

if app:
    app.add_handler(
        CommandHandler(BotCommands.ExecCommand, execute, filter=CustomFilters.swi_owner)
    )
    app.add_handler(
        CommandHandler(BotCommands.EvalCommand, evaluate, filter=CustomFilters.swi_owner)
    )
    app.add_handler(
        CommandHandler(BotCommands.ClearLocalsCommand, clear, filter=CustomFilters.swi_owner)
    )
