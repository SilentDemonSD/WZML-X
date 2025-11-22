from bot import bot_loop
from bot.modules.mirror_leech import Mirror


async def uphoster(client, message):
    bot_loop.create_task(Mirror(client, message, is_uphoster=True).new_event())
