from pyrogram import Client, enums
from asyncio import Lock
from inspect import signature

from .. import LOGGER
from .config_manager import Config


class TgClient:
    _lock = Lock()
    _hlock = Lock()
    bot = None
    user = None
    helper_bots = {}
    BNAME = ""
    ID = 0
    IS_PREMIUM_USER = False
    MAX_SPLIT_SIZE = 2097152000

    @classmethod
    def wztgClient(cls, *args, **kwargs):
        kwargs["parse_mode"] = enums.ParseMode.HTML
        if "max_concurrent_transmissions" in signature(Client.__init__).parameters:
            kwargs["max_concurrent_transmissions"] = 100
        return Client(*args, **kwargs)

    @classmethod
    async def start_helper_bot(cls, b_token):
        LOGGER.info("Generating helper client from HELPER_TOKENS")
        async with cls._hlock:
            cls.helper_bots[b_token] = cls.wztgClient(
                f"WZ-HBot{b_token}",
                Config.TELEGRAM_API,
                Config.TELEGRAM_HASH,
                bot_token=b_token,
                no_updates=True,
            )
            await cls.helper_bots[b_token].start()
            LOGGER.info(
                f"Helper Bot [@{cls.helper_bots[b_token].me.username}] Started!"
            )

    @classmethod
    async def start_bot(cls):
        LOGGER.info("Generating client from BOT_TOKEN")
        cls.ID = Config.BOT_TOKEN.split(":", 1)[0]
        cls.bot = cls.wztgClient(
            f"WZ-Bot{cls.ID}",
            Config.TELEGRAM_API,
            Config.TELEGRAM_HASH,
            proxy=Config.TG_PROXY,
            bot_token=Config.BOT_TOKEN,
            workdir="/usr/src/app",
            parse_mode=enums.ParseMode.HTML,
        )
        await cls.bot.start()
        cls.BNAME = cls.bot.me.username
        cls.ID = Config.BOT_TOKEN.split(":", 1)[0]
        LOGGER.info(f"WZ Bot [@{cls.BNAME}] Started!")

    @classmethod
    async def start_user(cls):
        if Config.USER_SESSION_STRING:
            LOGGER.info("Generating client from USER_SESSION_STRING")
            try:
                cls.user = cls.wztgClient(
                    "WZ-User",
                    Config.TELEGRAM_API,
                    Config.TELEGRAM_HASH,
                    proxy=Config.TG_PROXY,
                    session_string=Config.USER_SESSION_STRING,
                    in_memory=False,
                    parse_mode=enums.ParseMode.HTML,
                    sleep_threshold=60,
                    no_updates=True,
                )
                await cls.user.start()
                cls.IS_PREMIUM_USER = cls.user.me.is_premium
                if cls.IS_PREMIUM_USER:
                    cls.MAX_SPLIT_SIZE = 4194304000
                LOGGER.info(f"WZ User [@{cls.user.me.username}] Started!")
            except Exception as e:
                LOGGER.error(f"Failed to start client from USER_SESSION_STRING. {e}")
                cls.IS_PREMIUM_USER = False
                cls.user = None

    @classmethod
    async def stop(cls):
        async with cls._lock:
            if cls.bot:
                await cls.bot.stop()
            if cls.user:
                await cls.user.stop()
            LOGGER.info("Client(s) stopped")

    @classmethod
    async def reload(cls):
        async with cls._lock:
            await cls.bot.restart()
            if cls.user:
                await cls.user.restart()
            LOGGER.info("Client(s) restarted")
