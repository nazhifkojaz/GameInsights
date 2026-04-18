import ssl
import os
from urllib.parse import urlparse, parse_qsl, urlencode, urlunparse

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.config import Settings


def create_engine(settings: Settings) -> AsyncEngine:
    if not settings.database_url:
        raise ValueError("database_url is required")
    url = _ensure_async_driver(settings.database_url)
    connect_args = _build_connect_args(settings.database_url)
    return create_async_engine(url, pool_size=2, max_overflow=8, connect_args=connect_args)


def create_session_factory(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(engine, expire_on_commit=False)


def _ensure_async_driver(url: str) -> str:
    """Ensure the URL uses the asyncpg driver prefix and remove asyncpg-incompatible query params."""
    if "+asyncpg://" not in url:
        scheme, _, rest = url.partition("://")
        base = scheme.split("+")[0]
        url = f"{base}+asyncpg://{rest}"
    # asyncpg doesn't accept sslmode as a query parameter — remove all sslmode params
    parsed = urlparse(url)
    params = [
        (k, v)
        for k, v in parse_qsl(parsed.query, keep_blank_values=True)
        if k.lower() != "sslmode"
    ]
    url = urlunparse(parsed._replace(query=urlencode(params)))
    return url


def _build_connect_args(url: str) -> dict:
    """Build asyncpg connect_args for SSL if needed."""
    if "sslmode=require" in url:
        ctx = ssl.create_default_context()
        cafile = os.environ.get("GAMEINSIGHTS_DB_CAFILE")
        if cafile:
            ctx.load_verify_locations(cafile=cafile)
        return {"ssl": ctx}
    return {}
