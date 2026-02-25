import asyncio
from typing import Any
from fastapi import APIRouter, Depends

from app.dependencies import get_pool, get_cache, get_settings
from app.collector_pool import CollectorPool
from app.cache import ResponseCache
from app.config import Settings

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/{steamid}")
async def get_user(
    steamid: str,
    pool: CollectorPool = Depends(get_pool),
    cache: ResponseCache = Depends(get_cache),
    settings: Settings = Depends(get_settings),
) -> list[dict[str, Any]]:
    cache_key = cache.make_key("user", steamid, settings.region, settings.language)
    cached = await cache.get(cache_key)
    if cached is not None:
        return cached

    async with pool.acquire() as collector:
        # get_user_data usually accepts a list of steamids but we query one by one from API
        results = await asyncio.to_thread(
            collector.get_user_data, steamid, return_as="list", verbose=False
        )

    if not results:
        # In this specific context we just return empty list or raise generic error
        # based on gameinsights' underlying behavior
        return []

    await cache.set(cache_key, results)
    return results
