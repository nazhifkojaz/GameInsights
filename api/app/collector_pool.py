import asyncio
from contextlib import asynccontextmanager
from collections.abc import AsyncIterator
from gameinsights import Collector
from app.config import Settings


class CollectorPool:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._queue: asyncio.Queue[Collector] = asyncio.Queue(
            maxsize=settings.collector_pool_size
        )
        self._collectors: list[Collector] = []
        self._closed = False

    async def startup(self) -> None:
        for _ in range(self._settings.collector_pool_size):
            collector = Collector(
                region=self._settings.region,
                language=self._settings.language,
                steam_api_key=(
                    self._settings.steam_api_key.get_secret_value()
                    if self._settings.steam_api_key
                    else None
                ),
                calls=self._settings.rate_limit_calls,
                period=self._settings.rate_limit_period,
            )
            self._collectors.append(collector)
            await self._queue.put(collector)

    async def shutdown(self) -> None:
        self._closed = True
        # Drain the queue so no waiters can acquire stale collectors
        while not self._queue.empty():
            self._queue.get_nowait()
        for collector in self._collectors:
            collector.close()
        self._collectors.clear()

    @asynccontextmanager
    async def acquire(self) -> AsyncIterator[Collector]:
        if self._closed:
            raise RuntimeError("CollectorPool is closed")
        collector = await self._queue.get()
        try:
            yield collector
        finally:
            if not self._closed:
                await self._queue.put(collector)

    @property
    def size(self) -> int:
        return len(self._collectors)

    @property
    def available(self) -> int:
        return self._queue.qsize()
