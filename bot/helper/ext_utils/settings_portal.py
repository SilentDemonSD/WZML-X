from json import dumps, loads

from ... import user_data
from .db_handler import database
from .session_crypt import SessionCrypt


class PortalError(Exception):
    pass


class SettingsPortal:
    VERSION = 1
    KIND = "wzmlx-user-settings"
    MAX_BYTES = 512 * 1024
    FILE_BACKED = frozenset(
        ("THUMBNAIL", "RCLONE_CONFIG", "TOKEN_PICKLE", "USER_COOKIE_FILE")
    )
    PRIVILEGED = frozenset(("AUTH", "SUDO", "BLACKLIST", "is_auth", "is_sudo"))
    TRANSIENT = frozenset(
        ("VERIFY_TOKEN", "VERIFY_TIME", "token", "time", "thread_ids", "_id")
    )
    BLOCKED = FILE_BACKED | PRIVILEGED | TRANSIENT

    @staticmethod
    def _wipe(key):
        if key:
            key[:] = bytes(len(key))

    @classmethod
    def snapshot(cls, user_id):
        mine = user_data.get(user_id) or {}
        return {
            name: value
            for name, value in mine.items()
            if name not in cls.BLOCKED and value not in (None, "")
        }

    @classmethod
    async def export(cls, user_id, passphrase):
        body = cls.snapshot(user_id)
        if not body:
            raise PortalError("Nothing is set yet, so there is nothing to export")
        record, key = await SessionCrypt.seal(
            passphrase,
            SessionCrypt.AAD_EXPORT,
            dumps(body, separators=(",", ":"), default=str),
        )
        cls._wipe(key)
        record["kind"] = cls.KIND
        record["count"] = len(body)
        return dumps(record, indent=1).encode(), len(body)

    @classmethod
    def _envelope(cls, raw):
        if len(raw) > cls.MAX_BYTES:
            raise PortalError("That file is too big to be a settings export")
        try:
            record = loads(raw)
        except Exception:
            raise PortalError("That file is not a settings export") from None
        if not isinstance(record, dict) or record.get("kind") != cls.KIND:
            raise PortalError("That file is not a settings export")
        if int(record.get("v") or 0) > cls.VERSION:
            raise PortalError("That export was made by a newer bot, update first")
        return record

    @classmethod
    async def restore(cls, user_id, raw, passphrase):
        record = cls._envelope(raw)
        plain, key = await SessionCrypt.unseal(
            passphrase, SessionCrypt.AAD_EXPORT, record
        )
        cls._wipe(key)
        try:
            body = loads(plain)
        except Exception:
            raise PortalError("The export is unreadable") from None
        if not isinstance(body, dict):
            raise PortalError("The export is unreadable")
        taken = {name: value for name, value in body.items() if name not in cls.BLOCKED}
        refused = sorted(set(body) - set(taken))
        if not taken:
            raise PortalError("The export holds nothing that can be restored")
        user_data.setdefault(user_id, {}).update(taken)
        await database.update_user_data(user_id)
        return len(taken), refused
