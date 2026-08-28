from collections import OrderedDict
from time import time

from bot import LOGGER

from .queries import ANIME_GRAPHQL_QUERY, CHARACTER_QUERY, MANGA_QUERY

ANILIST_URL = "https://graphql.anilist.co"
TIMEOUT = 20
CACHE_TTL = 300
CACHE_MAX = 32
_cache = OrderedDict()


def _cached(key):
    hit = _cache.get(key)
    if hit is None:
        return None
    stamp, value = hit
    if time() - stamp > CACHE_TTL:
        _cache.pop(key, None)
        return None
    _cache.move_to_end(key)
    return value


def _store(key, value):
    if value is None:
        return value
    _cache[key] = (time(), value)
    _cache.move_to_end(key)
    while len(_cache) > CACHE_MAX:
        _cache.popitem(last=False)
    return value


def cache_bytes():
    return sum(len(str(v)) for _, v in _cache.values())


def cache_clear(aggressive=False):
    if aggressive:
        _cache.clear()
        return
    while len(_cache) > CACHE_MAX // 2:
        _cache.popitem(last=False)


async def _graphql(query, variables):
    from niquests import AsyncSession

    try:
        async with AsyncSession() as session:
            response = await session.post(
                ANILIST_URL,
                json={"query": query, "variables": variables},
                timeout=TIMEOUT,
            )
            if response.status_code != 200:
                LOGGER.error(f"anilist: HTTP {response.status_code}")
                return None
            payload = response.json()
    except Exception as err:
        LOGGER.error(f"anilist: {err}")
        return None
    if not isinstance(payload, dict):
        return None
    for problem in payload.get("errors") or []:
        LOGGER.error(f"anilist: {problem.get('message')}")
    return payload.get("data")


async def fetch_anime(**variables):
    key = ("anime", variables.get("id"), variables.get("search"))
    hit = _cached(key)
    if hit is not None:
        return hit
    data = await _graphql(ANIME_GRAPHQL_QUERY, variables)
    return _store(key, (data or {}).get("Media"))


async def fetch_character(**variables):
    key = ("char", variables.get("id"), variables.get("search"))
    hit = _cached(key)
    if hit is not None:
        return hit
    data = await _graphql(CHARACTER_QUERY, variables)
    return _store(key, (data or {}).get("Character"))


async def fetch_manga(**variables):
    data = await _graphql(MANGA_QUERY, variables)
    return (data or {}).get("Media")
