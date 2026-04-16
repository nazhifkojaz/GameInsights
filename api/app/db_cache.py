from typing import Any

from sqlalchemy import select, text
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.constants import ENDPOINT_TTL, Endpoint
from app.models import GameCache


class DatabaseCache:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    @staticmethod
    def make_key(
        endpoint: Endpoint, identifier: str, region: str, language: str
    ) -> str:
        """Generate a human-readable cache key."""
        return f"{endpoint}:{identifier}:{region}:{language}"

    async def get(self, key: str) -> Any | None:
        async with self._session_factory() as session:
            stmt = select(GameCache).where(
                GameCache.cache_key == key,
                text(
                    "game_cache.cached_at + (game_cache.ttl_seconds || ' seconds')::interval > NOW()"
                ),
            )
            result = await session.execute(stmt)
            entry = result.scalar_one_or_none()
            return entry.data if entry else None

    async def set(
        self,
        key: str,
        endpoint: Endpoint,
        identifier: str,
        region: str,
        language: str,
        data: Any,
    ) -> None:
        ttl = ENDPOINT_TTL.get(endpoint, 3600)
        async with self._session_factory() as session:
            stmt = (
                pg_insert(GameCache)
                .values(
                    cache_key=key,
                    endpoint=endpoint,
                    identifier=identifier,
                    region=region,
                    language=language,
                    data=data,
                    ttl_seconds=ttl,
                )
                .on_conflict_do_update(
                    index_elements=["cache_key"],
                    set_={
                        "data": data,
                        "cached_at": text("NOW()"),
                        "ttl_seconds": ttl,
                    },
                )
            )
            await session.execute(stmt)
            await session.commit()
