from ast import literal_eval
from pyrogram import Client, enums
from pyrogram.errors import FloodWait
from asyncio import Lock, gather, sleep
from hashlib import sha256
from inspect import signature

from .. import LOGGER, bot_loop
from .config_manager import Config

_DB_PARTITION_SALT = b"wzmlx_v3_db_partition_salt"


def db_partition_id(bot_id):
    raw = sha256(_DB_PARTITION_SALT + str(bot_id).encode("utf-8")).hexdigest()
    return f"p_{raw[:24]}"


class TgClient:
    _lock = Lock()
    _hlock = Lock()
    _ulock = Lock()
    _slock = Lock()

    bot = None
    user = None
    helper_bots = {}
    helper_loads = {}
    helper_users = {}
    helper_user_loads = {}
    stream_bots = {}
    stream_loads = {}

    BNAME = ""
    ID = 0
    PARTITION = ""
    IS_PREMIUM_USER = False
    MAX_SPLIT_SIZE = 2097152000

    @classmethod
    def wztgClient(cls, *args, proxy=None, **kwargs):
        kwargs["api_id"] = Config.TELEGRAM_API
        kwargs["api_hash"] = Config.TELEGRAM_HASH
        kwargs["proxy"] = Config.TG_PROXY if proxy is None else proxy
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
    def _parse_proxies(cls, raw):
        if not raw:
            return []
        proxies = []
        for line in raw.split("\n"):
            line = line.strip()
            if not line:
                proxies.append(None)
                continue
            try:
                parsed = literal_eval(line)
                proxies.append(parsed if isinstance(parsed, dict) else None)
            except (ValueError, SyntaxError):
                proxies.append(None)
        return proxies

    @classmethod
    async def _retry_hclient(cls, no, b_token, delay, proxy=None):
        await sleep(delay)
        try:
            hbot = cls.wztgClient(
                f"WZ-HBot{no}",
                bot_token=b_token,
                no_updates=True,
                proxy=proxy,
            )
            await hbot.start()
            LOGGER.info(f"Helper Bot [@{hbot.me.username}] Started!")
            cls.helper_bots[no], cls.helper_loads[no] = hbot, 0
        except FloodWait as e:
            LOGGER.warning(f"Helper Bot{no} FloodWait: Retrying in {e.value}s...")
            bot_loop.create_task(cls._retry_hclient(no, b_token, e.value, proxy))
        except Exception as e:
            LOGGER.error(f"Failed to start helper bot {no} from HELPER_TOKENS. {e}")

    @classmethod
    async def start_hclient(cls, no, b_token, proxy=None):
        try:
            hbot = cls.wztgClient(
                f"WZ-HBot{no}",
                bot_token=b_token,
                no_updates=True,
                proxy=proxy,
            )
            await hbot.start()
            LOGGER.info(f"Helper Bot [@{hbot.me.username}] Started!")
            cls.helper_bots[no], cls.helper_loads[no] = hbot, 0
        except FloodWait as e:
            LOGGER.warning(
                f"Helper Bot{no} FloodWait: Retrying in {e.value}s (non-blocking)..."
            )
            bot_loop.create_task(cls._retry_hclient(no, b_token, e.value, proxy))
        except Exception as e:
            LOGGER.error(f"Failed to start helper bot {no} from HELPER_TOKENS. {e}")
            cls.helper_bots.pop(no, None)

    @classmethod
    async def start_helper_bots(cls):
        if not Config.HELPER_TOKENS:
            return
        LOGGER.info("Generating helper client from HELPER_TOKENS")
        bot_proxies = cls._parse_proxies(Config.HELPER_BOT_PROXIES)
        async with cls._hlock:
            await gather(
                *(
                    cls.start_hclient(
                        no,
                        b_token,
                        bot_proxies[no - 1]
                        if bot_proxies and no - 1 < len(bot_proxies)
                        else None,
                    )
                    for no, b_token in enumerate(Config.HELPER_TOKENS.split(), start=1)
                )
            )

    @classmethod
    async def _retry_sclient(cls, no, b_token, delay, proxy=None):
        await sleep(delay)
        try:
            sbot = cls.wztgClient(
                f"WZ-SBot{no}",
                bot_token=b_token,
                no_updates=True,
                proxy=proxy,
            )
            await sbot.start()
            LOGGER.info(f"Stream Bot [@{sbot.me.username}] Started!")
            cls.stream_bots[no], cls.stream_loads[no] = sbot, 0
        except FloodWait as e:
            LOGGER.warning(f"Stream Bot{no} FloodWait: Retrying in {e.value}s...")
            bot_loop.create_task(cls._retry_sclient(no, b_token, e.value, proxy))
        except Exception as e:
            LOGGER.error(f"Failed to start stream bot {no} from STREAM_TOKENS. {e}")

    @classmethod
    async def start_sclient(cls, no, b_token, proxy=None):
        try:
            sbot = cls.wztgClient(
                f"WZ-SBot{no}",
                bot_token=b_token,
                no_updates=True,
                proxy=proxy,
            )
            await sbot.start()
            LOGGER.info(f"Stream Bot [@{sbot.me.username}] Started!")
            cls.stream_bots[no], cls.stream_loads[no] = sbot, 0
        except FloodWait as e:
            LOGGER.warning(
                f"Stream Bot{no} FloodWait: Retrying in {e.value}s (non-blocking)..."
            )
            bot_loop.create_task(cls._retry_sclient(no, b_token, e.value, proxy))
        except Exception as e:
            LOGGER.error(f"Failed to start stream bot {no} from STREAM_TOKENS. {e}")
            cls.stream_bots.pop(no, None)

    @classmethod
    async def start_stream_bots(cls):
        if not Config.STREAM_TOKENS:
            return
        LOGGER.info("Generating stream client from STREAM_TOKENS")
        async with cls._slock:
            await gather(
                *(
                    cls.start_sclient(no, b_token)
                    for no, b_token in enumerate(
                        Config.STREAM_TOKENS.split(), start=1
                    )
                )
            )

    @classmethod
    async def _retry_huser(cls, no, session_string, delay, proxy=None):
        await sleep(delay)
        try:
            huser = cls.wztgClient(
                f"WZ-HUser{no}",
                session_string=session_string,
                sleep_threshold=60,
                no_updates=True,
                proxy=proxy,
            )
            await huser.start()
            uname = huser.me.username or huser.me.first_name
            LOGGER.info(f"Helper User [{uname}] Started!")
            cls.helper_users[no], cls.helper_user_loads[no] = huser, 0
        except FloodWait as e:
            LOGGER.warning(f"Helper User{no} FloodWait: Retrying in {e.value}s...")
            bot_loop.create_task(cls._retry_huser(no, session_string, e.value, proxy))
        except Exception as e:
            LOGGER.error(f"Failed to start helper user {no} from HELPER_STRINGS. {e}")

    @classmethod
    async def start_huser(cls, no, session_string, proxy=None):
        try:
            huser = cls.wztgClient(
                f"WZ-HUser{no}",
                session_string=session_string,
                sleep_threshold=60,
                no_updates=True,
                proxy=proxy,
            )
            await huser.start()
            uname = huser.me.username or huser.me.first_name
            LOGGER.info(f"Helper User [{uname}] Started!")
            cls.helper_users[no], cls.helper_user_loads[no] = huser, 0
        except FloodWait as e:
            LOGGER.warning(
                f"Helper User{no} FloodWait: Retrying in {e.value}s (non-blocking)..."
            )
            bot_loop.create_task(cls._retry_huser(no, session_string, e.value, proxy))
        except Exception as e:
            LOGGER.error(f"Failed to start helper user {no} from HELPER_STRINGS. {e}")
            cls.helper_users.pop(no, None)

    @classmethod
    async def start_helper_users(cls):
        if not Config.HELPER_STRINGS:
            return
        LOGGER.info("Generating helper client from HELPER_STRINGS")
        user_proxies = cls._parse_proxies(Config.HELPER_USER_PROXIES)
        async with cls._ulock:
            await gather(
                *(
                    cls.start_huser(
                        no,
                        session_string,
                        user_proxies[no - 1]
                        if user_proxies and no - 1 < len(user_proxies)
                        else None,
                    )
                    for no, session_string in enumerate(
                        Config.HELPER_STRINGS.split(), start=1
                    )
                )
            )

    @classmethod
    async def start_bot(cls):
        LOGGER.info("Generating client from BOT_TOKEN")
        cls.ID = Config.BOT_TOKEN.split(":", 1)[0]
        cls.PARTITION = db_partition_id(cls.ID)
        cls.bot = cls.wztgClient(
            f"WZ-Bot{cls.ID}",
            bot_token=Config.BOT_TOKEN,
            workdir="/usr/src/app",
        )
        while True:
            try:
                await cls.bot.start()
                break
            except FloodWait as e:
                LOGGER.warning(f"FloodWait: Sleeping for {e.value} seconds...")
                await sleep(e.value)
        cls.BNAME = cls.bot.me.username
        cls.ID = Config.BOT_TOKEN.split(":", 1)[0]
        LOGGER.info(f"WZ Bot : [@{cls.BNAME}] Started!")

    @classmethod
    async def _retry_user(cls, delay):
        await sleep(delay)
        try:
            cls.user = cls.wztgClient(
                "WZ-User",
                session_string=Config.USER_SESSION_STRING,
                sleep_threshold=60,
                no_updates=True,
            )
            await cls.user.start()
            cls.IS_PREMIUM_USER = cls.user.me.is_premium
            if cls.IS_PREMIUM_USER:
                cls.MAX_SPLIT_SIZE = 4194304000
            uname = cls.user.me.username or cls.user.me.first_name
            LOGGER.info(f"WZ User : [{uname}] Started!")
        except FloodWait as e:
            LOGGER.warning(f"User client FloodWait: Retrying in {e.value}s...")
            bot_loop.create_task(cls._retry_user(e.value))
        except Exception as e:
            LOGGER.error(f"Failed to start client from USER_SESSION_STRING. {e}")
            cls.IS_PREMIUM_USER = False
            cls.MAX_SPLIT_SIZE = 2097152000
            cls.user = None

    @classmethod
    async def start_user(cls):
        if Config.USER_SESSION_STRING:
            LOGGER.info("Generating client from USER_SESSION_STRING")
            try:
                cls.user = cls.wztgClient(
                    "WZ-User",
                    session_string=Config.USER_SESSION_STRING,
                    sleep_threshold=60,
                    no_updates=True,
                )
                await cls.user.start()
                cls.IS_PREMIUM_USER = cls.user.me.is_premium
                if cls.IS_PREMIUM_USER:
                    cls.MAX_SPLIT_SIZE = 4194304000
                uname = cls.user.me.username or cls.user.me.first_name
                LOGGER.info(f"WZ User : [{uname}] Started!")
            except FloodWait as e:
                LOGGER.warning(
                    f"User client FloodWait: Retrying in {e.value}s (non-blocking)..."
                )
                bot_loop.create_task(cls._retry_user(e.value))
            except Exception as e:
                LOGGER.error(f"Failed to start client from USER_SESSION_STRING. {e}")
                cls.IS_PREMIUM_USER = False
                cls.MAX_SPLIT_SIZE = 2097152000
                cls.user = None

    @classmethod
    async def stop(cls):
        async with cls._lock:
            clients = []
            if cls.bot:
                clients.append(cls.bot.stop())
                cls.bot = None
            if cls.user:
                clients.append(cls.user.stop())
                cls.user = None
            if cls.helper_bots:
                clients.extend(h_bot.stop() for h_bot in cls.helper_bots.values())
                cls.helper_bots = {}
            if cls.helper_users:
                clients.extend(h_user.stop() for h_user in cls.helper_users.values())
                cls.helper_users = {}
            if cls.stream_bots:
                clients.extend(s_bot.stop() for s_bot in cls.stream_bots.values())
                cls.stream_bots = {}
            if clients:
                await gather(*clients, return_exceptions=True)
            LOGGER.info("All Client(s) stopped")

    @classmethod
    async def reload(cls):
        async with cls._lock:
            await cls.bot.restart()
            if cls.user:
                await cls.user.restart()
            if cls.helper_bots:
                await gather(*[h_bot.restart() for h_bot in cls.helper_bots.values()])
            if cls.helper_users:
                await gather(
                    *[h_user.restart() for h_user in cls.helper_users.values()]
                )
            if cls.stream_bots:
                await gather(*[s_bot.restart() for s_bot in cls.stream_bots.values()])
            LOGGER.info("All Client(s) restarted")
