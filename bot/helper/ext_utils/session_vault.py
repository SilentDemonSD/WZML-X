from asyncio import CancelledError, Lock, get_running_loop, shield, sleep
from time import monotonic

from ... import LOGGER, bot_loop, user_data
from ...core.config_manager import Config
from ...core.tg_client import UserSessionPool
from ..telegram_helper.prompt import STOP, ask_in_pm
from .bot_utils import update_user_ldata
from .db_handler import database
from .exceptions import TgLinkException
from .mem_guard import register_cache
from .session_crypt import BadPassphrase, SessionCrypt


class SessionLocked(Exception):
    pass


class VaultEntry:
    __slots__ = ("key", "salt", "expires")

    def __init__(self, key, salt, expires):
        self.key = key
        self.salt = salt
        self.expires = expires


class KeyVault:
    def __init__(self):
        self._keys = {}
        self._pending = {}
        self._lock = Lock()

    def __len__(self):
        return len(self._keys)

    @staticmethod
    def _fail_and_consume(waiter, err):
        waiter.set_exception(err)
        waiter.exception()

    @staticmethod
    def _wipe(entry):
        buf = entry.key
        for i in range(len(buf)):
            buf[i] = 0

    def has(self, user_id):
        return self.get(user_id) is not None

    def get(self, user_id):
        entry = self._keys.get(user_id)
        if entry is None:
            return None
        if monotonic() >= entry.expires:
            self._wipe(entry)
            del self._keys[user_id]
            return None
        return entry.key

    def ttl_left(self, user_id):
        entry = self._keys.get(user_id)
        if entry is None:
            return 0
        return max(0, int(entry.expires - monotonic()))

    def put(self, user_id, key, salt):
        old = self._keys.get(user_id)
        if old is not None:
            self._wipe(old)
        ttl = Config.USER_SESSION_KEY_TTL or 43200
        self._keys[user_id] = VaultEntry(key, salt, monotonic() + ttl)

    def purge(self, user_id):
        entry = self._keys.pop(user_id, None)
        if entry is None:
            return False
        self._wipe(entry)
        return True

    def reap(self):
        now = monotonic()
        dead = [uid for uid, e in self._keys.items() if now >= e.expires]
        for uid in dead:
            self._wipe(self._keys.pop(uid))
        return len(dead)

    def trim(self, aggressive=False):
        if aggressive:
            for uid in list(self._keys):
                self._wipe(self._keys.pop(uid))
            return
        self.reap()

    async def ensure(self, user_id, unlock):
        key = self.get(user_id)
        if key is not None:
            return key
        async with self._lock:
            waiter = self._pending.get(user_id)
            mine = waiter is None
            if mine:
                waiter = self._pending[user_id] = get_running_loop().create_future()
        if not mine:
            return await shield(waiter)
        try:
            key = await unlock()
        except BaseException as err:
            self._fail_and_consume(waiter, err)
            async with self._lock:
                self._pending.pop(user_id, None)
            raise
        waiter.set_result(key)
        async with self._lock:
            self._pending.pop(user_id, None)
        return key


class SessionReaper:
    INTERVAL = 60
    _task = None

    @classmethod
    def start(cls):
        if cls._task is None or cls._task.done():
            cls._task = bot_loop.create_task(cls._run())
        return cls._task

    @classmethod
    async def stop(cls):
        if cls._task is not None:
            cls._task.cancel()
            cls._task = None
        vault.trim(True)
        await UserSessionPool.stop_all()

    @classmethod
    async def _run(cls):
        while True:
            await sleep(cls.INTERVAL)
            try:
                vault.reap()
                await UserSessionPool.reap_idle()
            except CancelledError:
                raise
            except Exception as err:
                LOGGER.warning(f"session reaper: {err}")


vault = KeyVault()
register_cache("usess_keys", vault.__len__, vault.trim)


class UserSession:
    KEY = "USER_SESSION"

    @classmethod
    def record(cls, user_id):
        return (user_data.get(user_id) or {}).get(cls.KEY)

    @classmethod
    def exists(cls, user_id):
        return bool(cls.record(user_id))

    @classmethod
    def unlocked(cls, user_id):
        return vault.has(user_id)

    @classmethod
    async def _ask(cls, user_id, record):
        answer = await ask_in_pm(
            user_id,
            "⌬ <b><u>Unlock Your Session</u></b>\n│\n"
            "┟ <i>Send the passphrase you sealed it with.</i>\n"
            "┠ <i>The message is deleted the moment it arrives.</i>\n"
            "┖ <b>Timeout:</b> <code>120 sec</code>",
        )
        if answer is None:
            raise TgLinkException("Timed out waiting for your passphrase")
        if answer == STOP:
            raise TgLinkException("Unlock cancelled")
        try:
            plain, key = await SessionCrypt.unseal(answer, user_id, record)
        except BadPassphrase:
            raise TgLinkException(
                "Wrong passphrase, or the stored session was modified"
            ) from None
        vault.put(user_id, key, SessionCrypt.salt_of(record))
        if SessionCrypt.needs_reseal(record):
            fresh, fresh_key = await SessionCrypt.seal(answer, user_id, plain)
            update_user_ldata(user_id, cls.KEY, fresh)
            vault.put(user_id, fresh_key, SessionCrypt.salt_of(fresh))
            await database.update_user_data(user_id)
        return vault.get(user_id)

    @classmethod
    async def unlock(cls, user_id, prompt=True):
        record = cls.record(user_id)
        if not record:
            raise TgLinkException("No session is stored for you")
        key = vault.get(user_id)
        if key is not None:
            return key
        if not prompt:
            raise SessionLocked(user_id)
        return await vault.ensure(user_id, lambda: cls._ask(user_id, record))

    @classmethod
    async def _string(cls, user_id):
        record = cls.record(user_id)
        key = vault.get(user_id)
        if record is None or key is None:
            raise SessionLocked(user_id)
        return SessionCrypt.open_with(key, user_id, record)

    @classmethod
    def borrow(cls, user_id):
        return UserSessionPool.borrow(user_id, lambda: cls._string(user_id))

    @classmethod
    async def forget(cls, user_id):
        vault.purge(user_id)
        await UserSessionPool.drop(user_id)
