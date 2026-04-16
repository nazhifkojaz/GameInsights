import asyncio
from typing import Any

from fastapi import APIRouter, Depends

from app.collector_pool import CollectorPool
from app.config import Settings
from app.constants import Endpoint
from app.db_cache import DatabaseCache
from app.dependencies import get_cache, get_pool, get_settings
from app.schemas.users import UserResponse

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/{steamid}", response_model=list[UserResponse])
async def get_user(
    steamid: str,
    pool: CollectorPool = Depends(get_pool),
    cache: DatabaseCache = Depends(get_cache),
    settings: Settings = Depends(get_settings),
) -> list[dict[str, Any]]:
    cache_key = cache.make_key(
        Endpoint.USER, steamid, settings.region, settings.language
    )
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

    await cache.set(
        cache_key, Endpoint.USER, steamid, settings.region, settings.language, results
    )
    return results
