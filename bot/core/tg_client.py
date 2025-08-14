from pyrogram import Client, enums
from asyncio import Lock, gather
from inspect import signature

from .. import LOGGER
from .config_manager import Config


class TgClient:
    _lock = Lock()
    _hlock = Lock()

    bot = None
    user = None
    helper_bots = {}
    helper_loads = {}

    BNAME = ""
    ID = 0
    IS_PREMIUM_USER = False
    MAX_SPLIT_SIZE = 2097152000

    @classmethod
    def wztgClient(cls, *args, **kwargs):
        kwargs["api_id"] = Config.TELEGRAM_API
        kwargs["api_hash"] = Config.TELEGRAM_HASH
        kwargs["proxy"] = Config.TG_PROXY
        kwargs["parse_mode"] = enums.ParseMode.HTML
        kwargs["in_memory"] = True
        for param, value in {
            "max_concurrent_transmissions": 100,
            "skip_updates": False,
        }.items():
            if param in signature(Client.__init__).parameters:
                kwargs[param] = value
        return Client(*args, **kwargs)

    @classmethod
    async def start_hclient(cls, no, b_token):
        try:
            hbot = await cls.wztgClient(
                f"Beast-HBot{no}",
                bot_token=b_token,
                no_updates=True,
            ).start()
            LOGGER.info(f"Helper Bot [@{hbot.me.username}] Started!")
            cls.helper_bots[no], cls.helper_loads[no] = hbot, 0
        except Exception as e:
            LOGGER.error(f"Failed to start helper bot {no} from HELPER_TOKENS. {e}")
            cls.helper_bots.pop(no, None)

    @classmethod
    async def start_helper_bots(cls):
        if not Config.HELPER_TOKENS:
            return
        LOGGER.info("Generating helper client from HELPER_TOKENS")
        async with cls._hlock:
            await gather(
                *(
                    cls.start_hclient(no, b_token)
                    for no, b_token in enumerate(Config.HELPER_TOKENS.split(), start=1)
                )
            )

    @classmethod
    async def start_bot(cls):
        LOGGER.info("Generating client from BOT_TOKEN")
        cls.ID = Config.BOT_TOKEN.split(":", 1)[0]
        cls.bot = cls.wztgClient(
            f"Beast{cls.ID}",
            bot_token=Config.BOT_TOKEN,
            workdir="/usr/src/app",
        )
        await cls.bot.start()
        cls.BNAME = cls.bot.me.username
        cls.ID = Config.BOT_TOKEN.split(":", 1)[0]
        LOGGER.info(f"Beast : [@{cls.BNAME}] Started!")

    @classmethod
    async def start_user(cls):
        if Config.USER_SESSION_STRING:
            LOGGER.info("Generating client from USER_SESSION_STRING")
            try:
                cls.user = cls.wztgClient(
                    "Beast-User",
                    session_string=Config.USER_SESSION_STRING,
                    sleep_threshold=60,
                    no_updates=True,
                )
                await cls.user.start()
                cls.IS_PREMIUM_USER = cls.user.me.is_premium
                if cls.IS_PREMIUM_USER:
                    cls.MAX_SPLIT_SIZE = 4194304000
                uname = cls.user.me.username or cls.user.me.first_name
                LOGGER.info(f"Beast User : [{uname}] Started!")
            except Exception as e:
                LOGGER.error(f"Failed to start client from USER_SESSION_STRING. {e}")
                cls.IS_PREMIUM_USER = False
                cls.user = None

    @classmethod
    async def stop(cls):
        async with cls._lock:
            if cls.bot:
                await cls.bot.stop()
                cls.bot = None
            if cls.user:
                await cls.user.stop()
                cls.user = None
            if cls.helper_bots:
                await gather(*[h_bot.stop() for h_bot in cls.helper_bots.values()])
                cls.helper_bots = {}
            LOGGER.info("All Client(s) are stopped")

    @classmethod
    async def reload(cls):
        async with cls._lock:
            await cls.bot.restart()
            if cls.user:
                await cls.user.restart()
            if cls.helper_bots:
                await gather(*[h_bot.restart() for h_bot in cls.helper_bots.values()])
            LOGGER.info("All Client(s) are restarted")
