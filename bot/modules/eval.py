from os import path as ospath, getcwd, chdir
from traceback import format_exc
from textwrap import indent
from io import StringIO, BytesIO

from pyrogram import Client
from pyrogram.types import Message
from pyrogram.enums import ParseMode
from pyrogram.filters import command
from contextlib import redirect_stdout

from bot.helper.telegram_helper.filters import CustomFilters
from bot.helper.telegram_helper.bot_commands import BotCommands
from bot import LOGGER, bot

namespaces = {}

def namespace_of(chat, message, bot):
    if chat not in namespaces:
        namespaces[chat] = {
            '__builtins__': globals()['__builtins__'],
            'client': bot,
            'bot': bot,
            'message': message,
            'from_user': message.from_user,
            'chat': message.chat
        }
    return namespaces[chat]

async def log_input(message):
    user = message.from_user.id
    chat = message.chat.id
    LOGGER.info(f"IN: {message.text} ( User={user}, Chat={chat} )")

async def send(msg, bot, m):
    if len(str(msg)) > 2000:
        with BytesIO(str.encode(msg)) as out_file:
            out_file.name = "output.txt"
            await bot.send_document(chat_id=m.chat.id, document=out_file)
    else:
        LOGGER.info(f"OUT: '{msg}'")
        await bot.send_message(
            chat_id=m.chat.id,
            text=f"`{msg}`",
            parse_mode=ParseMode.MARKDOWN)

@bot.on_message(command(BotCommands.EvalCommand) & (CustomFilters.owner_filter | CustomFilters.sudo_user))
async def evaluate(c: Client, m: Message):
    doResult = await do(eval, c, m)
    await send(doResult, c, m)

@bot.on_message(command(BotCommands.ExecCommand) & (CustomFilters.owner_filter | CustomFilters.sudo_user))
async def execute(c: Client, m: Message):
    doResult = await do(eval, c, m)
    await send(doResult, c, m)

async def cleanup_code(code):
    if code.startswith('```') and code.endswith('```'):
        return '\n'.join(code.split('\n')[1:-1])
    return code.strip('` \n')

async def do(func, bot, message):
    await log_input(message)
    content = message.text.split(maxsplit=1)[-1]
    body = await cleanup_code(content)
    env = namespace_of(message.chat.id, message, bot)

    chdir(getcwd())
    with open(ospath.join(getcwd(), 'bot/modules/temp.txt'), 'w') as temp:
        temp.write(body)

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
                try:
                    result = f'{repr(eval(body, env))}'
                except:
                    pass
        else:
            result = f'{value}{func_return}'
        if result:
            return result

@bot.on_message(command(BotCommands.ClearLocalsCommand) & (CustomFilters.owner_filter | CustomFilters.sudo_user))
async def clear(c: Client, m: Message):
    await log_input(m)
    global namespaces
    if m.chat.id in namespaces:
        del namespaces[m.chat.id]
    send("Cleared locals.", c, m)
