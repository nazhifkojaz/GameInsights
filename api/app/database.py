import importlib.resources

import asyncpg

from app.config import Settings


async def create_pool(settings: Settings) -> asyncpg.Pool:
    if not settings.database_url:
        raise ValueError("database_url is required")
    return await asyncpg.create_pool(
        settings.database_url,
        min_size=2,
        max_size=10,
    )


async def init_schema(pool: asyncpg.Pool) -> None:
    """Initialize database schema from SQL file."""
    sql = importlib.resources.read_text("app", "schema.sql")
    async with pool.acquire() as conn:
        await conn.execute(sql)
