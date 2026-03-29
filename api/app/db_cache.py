import json
from typing import Any

import asyncpg

from app.constants import ENDPOINT_TTL, Endpoint


class DatabaseCache:
    def __init__(self, pool: asyncpg.Pool) -> None:
        self._pool = pool

    @staticmethod
    def make_key(
        endpoint: Endpoint, identifier: str, region: str, language: str
    ) -> str:
        """Generate a human-readable cache key."""
        return f"{endpoint}:{identifier}:{region}:{language}"

    async def get(self, key: str) -> Any:
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT data FROM game_cache
                WHERE cache_key = $1
                AND cached_at + (ttl_seconds || ' seconds')::interval > NOW()
                """,
                key,
            )
            # asyncpg returns strings for JSONB if not configured using set_type_codec
            # So we parse json here directly.
            return json.loads(row["data"]) if row else None

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
        async with self._pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO game_cache
                    (cache_key, endpoint, identifier, region, language, data, ttl_seconds)
                VALUES ($1, $2, $3, $4, $5, $6, $7)
                ON CONFLICT (cache_key) DO UPDATE SET
                    data = EXCLUDED.data,
                    cached_at = NOW(),
                    ttl_seconds = EXCLUDED.ttl_seconds
                """,
                key,
                endpoint,
                identifier,
                region,
                language,
                json.dumps(data),
                ttl,
            )
