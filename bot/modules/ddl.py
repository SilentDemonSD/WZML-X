from bot import bot_loop
from bot.modules.mirror_leech import Mirror


async def ddl(client, message):
    bot_loop.create_task(Mirror(client, message, is_ddl=True).new_event())
