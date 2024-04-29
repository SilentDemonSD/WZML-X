#!/usr/bin/env python3
import asyncio
import io
import logging

import pyrogram
from pyrogram.errors import RpcError
from pyrogram.handlers import MessageHandler, EditedMessageHandler
from pyrogram.filters import command

log = logging.getLogger(__name__)

@pyrogram.Session()
class ShellBot(pyrogram.Client):
    def __init__(self):
        super().__init__(
            name="ShellBot",
            api_id=YOUR_API_ID,
            api_hash=YOUR_API_HASH,
            bot_token=YOUR_BOT_TOKEN,
            plugins=dict(root="bot.plugins"),
        )

async def main():
    await ShellBot().start()
    await ShellBot().idle()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        log.info("Stopping...")

from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from bot import LOGGER, bot
from bot.helper.telegram_helper.message_utils import sendMessage, sendFile
from bot.helper.ext_utils.bot_utils import cmd_exec, new_task
from bot.helper.telegram_helper.filters import CustomFilters
from bot.helper.telegram_helper.bot_commands import BotCommands

class ShellBotPlugin:

    async def shell(self, client: ShellBot, message: Message):
        cmd = message.text.split(maxsplit=1)
        if len(cmd) == 1:
            await sendMessage(message, 'No command to execute was given.')
            return
        cmd = cmd[1]
        try:
            stdout, stderr, _ = await cmd_exec(cmd, shell=True)
        except RpcError as e:
            await sendMessage(message, f'Error: {e}')
            return
        reply = ''
        if len(stdout) != 0:
            reply += f"*Stdout*\n{stdout}\n"
            LOGGER.info(f"Shell - {cmd} - {stdout}")
        if len(stderr) != 0:
            reply += f"*Stderr*\n{stderr}"
            LOGGER.error(f"Shell - {cmd} - {stderr}")

        if len(reply) > 4096:
            if len(reply) != 0:
                with io.BytesIO(str.encode(reply)) as out_file:
                    out_file.name = "shell_output.txt"
                    await sendFile(message, out_file)
        else:
            await sendMessage(message, reply)

shell_plugin = ShellBotPlugin()

bot.add_handler(MessageHandler(shell_plugin.shell, filters=command(BotCommands.ShellCommand) & CustomFilters.sudo))
bot.add_handler(EditedMessageHandler(shell_plugin.shell, filters=command(BotCommands.ShellCommand) & CustomFilters.sudo))
