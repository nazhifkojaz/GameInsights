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

    async def startup(self) -> None:
        for _ in range(self._settings.collector_pool_size):
            collector = Collector(
                region=self._settings.region,
                language=self._settings.language,
                steam_api_key=self._settings.steam_api_key,
                gamalytic_api_key=self._settings.gamalytic_api_key,
                calls=self._settings.rate_limit_calls,
                period=self._settings.rate_limit_period,
            )
            self._collectors.append(collector)
            await self._queue.put(collector)

    async def shutdown(self) -> None:
        for collector in self._collectors:
            collector.close()
        self._collectors.clear()

    @asynccontextmanager
    async def acquire(self) -> AsyncIterator[Collector]:
        collector = await self._queue.get()
        try:
            yield collector
        finally:
            await self._queue.put(collector)

    @property
    def size(self) -> int:
        return len(self._collectors)

    @property
    def available(self) -> int:
        return self._queue.qsize()
