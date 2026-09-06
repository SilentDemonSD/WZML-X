from asyncio import Semaphore
from base64 import b64decode, b64encode
from hashlib import scrypt
from os import urandom

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from .bot_utils import sync_to_async


class SessionCryptError(Exception):
    pass


class BadPassphrase(SessionCryptError):
    pass


class SessionCrypt:
    VERSION = 1
    N = 1 << 15
    R = 8
    P = 1
    DKLEN = 32
    MAXMEM = 128 * 1024 * 1024
    SALT_LEN = 16
    NONCE_LEN = 12
    AAD_PREFIX = b"wzmlx.usess.v1:"

    _gate = Semaphore(2)

    @classmethod
    def aad(cls, user_id):
        return cls.AAD_PREFIX + str(int(user_id)).encode()

    @staticmethod
    def salt_of(record):
        return b64decode(record["salt"])

    @staticmethod
    def params_of(record):
        return int(record["n"]), int(record["r"]), int(record["p"])

    @classmethod
    def needs_reseal(cls, record):
        return cls.params_of(record) != (cls.N, cls.R, cls.P)

    @classmethod
    def derive(cls, passphrase, salt, n=0, r=0, p=0):
        if not passphrase:
            raise SessionCryptError("Passphrase is empty")
        return bytearray(
            scrypt(
                passphrase.encode() if isinstance(passphrase, str) else passphrase,
                salt=salt,
                n=n or cls.N,
                r=r or cls.R,
                p=p or cls.P,
                dklen=cls.DKLEN,
                maxmem=cls.MAXMEM,
            )
        )

    @classmethod
    async def derive_async(cls, passphrase, salt, n=0, r=0, p=0):
        async with cls._gate:
            return await sync_to_async(cls.derive, passphrase, salt, n, r, p)

    @classmethod
    async def derive_for(cls, passphrase, record):
        n, r, p = cls.params_of(record)
        return await cls.derive_async(passphrase, cls.salt_of(record), n, r, p)

    @classmethod
    def seal_with(cls, key, user_id, plaintext, salt):
        nonce = urandom(cls.NONCE_LEN)
        ct = AESGCM(bytes(key)).encrypt(nonce, plaintext.encode(), cls.aad(user_id))
        return {
            "v": cls.VERSION,
            "kdf": "scrypt",
            "n": cls.N,
            "r": cls.R,
            "p": cls.P,
            "salt": b64encode(salt).decode(),
            "nonce": b64encode(nonce).decode(),
            "ct": b64encode(ct).decode(),
        }

    @classmethod
    def open_with(cls, key, user_id, record):
        try:
            raw = AESGCM(bytes(key)).decrypt(
                b64decode(record["nonce"]),
                b64decode(record["ct"]),
                cls.aad(user_id),
            )
        except (InvalidTag, KeyError, TypeError, ValueError):
            raise BadPassphrase("Wrong passphrase or corrupted record") from None
        return raw.decode()

    @classmethod
    async def seal(cls, passphrase, user_id, plaintext):
        salt = urandom(cls.SALT_LEN)
        key = await cls.derive_async(passphrase, salt)
        return cls.seal_with(key, user_id, plaintext, salt), key

    @classmethod
    async def unseal(cls, passphrase, user_id, record):
        key = await cls.derive_for(passphrase, record)
        return cls.open_with(key, user_id, record), key
