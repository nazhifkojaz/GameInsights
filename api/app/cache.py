import asyncio
import hashlib
from typing import Any
from cachetools import TTLCache


class ResponseCache:
    def __init__(self, maxsize: int = 256, ttl: int = 600) -> None:
        self._cache: TTLCache[str, Any] = TTLCache(maxsize=maxsize, ttl=ttl)
        self._lock = asyncio.Lock()

    @staticmethod
    def make_key(endpoint: str, identifier: str, region: str, language: str) -> str:
        raw = f"{endpoint}:{identifier}:{region}:{language}"
        return hashlib.md5(raw.encode()).hexdigest()

    async def get(self, key: str) -> Any | None:
        async with self._lock:
            return self._cache.get(key)

    async def set(self, key: str, value: Any) -> None:
        async with self._lock:
            self._cache[key] = value

    async def clear(self) -> None:
        async with self._lock:
            self._cache.clear()
