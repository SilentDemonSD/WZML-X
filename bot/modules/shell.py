from subprocess import Popen, PIPE
from pyrogram import filters, Client
from pyrogram.types import Message
from pyrogram.enums import ParseMode
from bot import LOGGER, bot
from bot.helper.telegram_helper.filters import CustomFilters
from bot.helper.telegram_helper.bot_commands import BotCommands


@bot.on_message(filters.command(BotCommands.ShellCommand) & (CustomFilters.owner_filter | CustomFilters.sudo_user))
async def shell(c: Client, m: Message):
    cmd = m.text.split(maxsplit=1)
    if len(cmd) == 1:
        return await m.reply_text('No command to execute was given.', parse_mode=ParseMode.HTML)
    cmd = cmd[1].strip()
    process = Popen(cmd, stdout=PIPE, stderr=PIPE, shell=True)
    stdout, stderr = process.communicate()
    reply = ''
    stderr = stderr.decode()
    stdout = stdout.decode()
    if len(stdout) != 0:
        reply += f"*Stdout*\n`{stdout}`\n"
        LOGGER.info(f"Shell - {cmd} - {stdout}")
    if len(stderr) != 0:
        reply += f"*Stderr*\n`{stderr}`\n"
        LOGGER.error(f"Shell - {cmd} - {stderr}")
    if len(reply) > 3000:
        with open('shell_output.txt', 'w') as file:
            file.write(reply)
        with open('shell_output.txt', 'rb') as doc:
            await c.send_document(
                chat_id=m.chat.id,
                document=doc,
                file_name=doc.name,
                reply_to_message_id=m.id
            )
    elif len(reply) != 0:
        await m.reply_text(reply, parse_mode=ParseMode.MARKDOWN)
    else:
        await m.reply_text('No Reply', parse_mode=ParseMode.MARKDOWN)
