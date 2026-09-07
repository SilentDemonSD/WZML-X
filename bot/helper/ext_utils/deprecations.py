from logging import getLogger

LOGGER = getLogger("bot")


class Deprecations:
    OWNER_MAP = {"LEECH_DUMP_CHAT": "LEECH_LOG_CHAT"}
    USER_MAP = {
        "LEECH_DUMP_CHAT": "Leech Dump Chats in Leech Settings",
        "ldump": "Leech Dump Chats in Leech Settings",
        "usess": "User Session in Clone Settings",
        "METADATA_CMDS": "Metadata in FF Media Settings",
    }
    DUMP_KEYS = ("LEECH_DUMP_CHAT", "ldump")
    DEAD_KEYS = ("LEECH_DUMP_CHAT", "ldump", "METADATA_CMDS")
    KEPT_KEYS = ("usess",)
    PREFIXES = ("b:", "u:", "h:")

    @classmethod
    def note(cls, key, instead, moved=False):
        tail = "moved for you" if moved else "set it again"
        LOGGER.warning(f"{key} is deprecated, use {instead} instead ({tail})")

    @classmethod
    def adopt_owner(cls, config, key, value, convert=None, shadowed=None):
        instead = cls.OWNER_MAP.get(key)
        if not instead or not value:
            return False
        if shadowed is None:
            shadowed = bool(getattr(config, instead, None))
        taken = not shadowed
        cls.note(key, instead, taken)
        if not taken:
            return False
        if convert is not None:
            value = convert(instead, value)
        elif isinstance(value, str):
            value = value.strip()
        setattr(config, instead, value)
        return True

    @classmethod
    def plain(cls, value):
        text = str(value or "").strip()
        for tag in cls.PREFIXES:
            if text.startswith(tag):
                return text[len(tag) :].strip()
        return text

    @classmethod
    def usable(cls, value):
        plain = cls.plain(value)
        return bool(plain) and plain.casefold() != "pm"

    @classmethod
    def migrate_user(cls, row):
        for key in cls.KEPT_KEYS:
            if key in row:
                cls.note(key, cls.USER_MAP[key])
        dead = [key for key in cls.DEAD_KEYS if key in row]
        if not dead:
            return []
        chats = row.get("LEECH_DUMP_CHATS") or {}
        for key in dead:
            value = row.pop(key)
            if key not in cls.DUMP_KEYS or chats:
                continue
            if isinstance(value, dict):
                chats = {
                    str(name): cls.plain(one)
                    for name, one in value.items()
                    if cls.usable(one)
                }
            elif cls.usable(value):
                chats = {"Default": cls.plain(value)}
        if chats:
            row["LEECH_DUMP_CHATS"] = chats
        for key in dead:
            cls.note(key, cls.USER_MAP[key], key in cls.DUMP_KEYS)
        return dead
