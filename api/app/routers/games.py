import asyncio
from typing import Any
from fastapi import APIRouter, Depends
from gameinsights import GameNotFoundError

from app.dependencies import get_pool, get_cache, get_settings
from app.collector_pool import CollectorPool
from app.cache import ResponseCache
from app.config import Settings
from app.schemas.games import BatchRequest

router = APIRouter(prefix="/games", tags=["games"])


@router.get("/{appid}")
async def get_game(
    appid: str,
    pool: CollectorPool = Depends(get_pool),
    cache: ResponseCache = Depends(get_cache),
    settings: Settings = Depends(get_settings),
) -> dict[str, Any]:
    cache_key = cache.make_key("game", appid, settings.region, settings.language)
    cached = await cache.get(cache_key)
    if cached is not None:
        return cached

    async with pool.acquire() as collector:
        results = await asyncio.to_thread(
            collector.get_games_data, appid, raise_on_error=True, verbose=False
        )

    if not results:
        raise GameNotFoundError(appid=appid)

    data = results[0]
    await cache.set(cache_key, data)
    return data


@router.get("/{appid}/recap")
async def get_game_recap(
    appid: str,
    pool: CollectorPool = Depends(get_pool),
    cache: ResponseCache = Depends(get_cache),
    settings: Settings = Depends(get_settings),
) -> dict[str, Any]:
    cache_key = cache.make_key("game_recap", appid, settings.region, settings.language)
    cached = await cache.get(cache_key)
    if cached is not None:
        return cached

    async with pool.acquire() as collector:
        results = await asyncio.to_thread(
            collector.get_games_data,
            appid,
            recap=True,
            raise_on_error=True,
            verbose=False,
        )

    if not results:
        raise GameNotFoundError(appid=appid)

    data = results[0]
    await cache.set(cache_key, data)
    return data


@router.get("/{appid}/reviews")
async def get_game_reviews(
    appid: str,
    pool: CollectorPool = Depends(get_pool),
) -> list[dict[str, Any]]:
    # Reviews are explicitly noted to have None TTL (no caching)
    async with pool.acquire() as collector:
        results = await asyncio.to_thread(
            collector.get_game_review, appid, return_as="list", verbose=False
        )
    return results


@router.get("/{appid}/active-players")
async def get_game_active_players(
    appid: str,
    pool: CollectorPool = Depends(get_pool),
    cache: ResponseCache = Depends(get_cache),
    settings: Settings = Depends(get_settings),
) -> list[dict[str, Any]]:
    cache_key = cache.make_key(
        "game_players", appid, settings.region, settings.language
    )
    cached = await cache.get(cache_key)
    if cached is not None:
        return cached

    async with pool.acquire() as collector:
        results = await asyncio.to_thread(
            collector.get_games_active_player_data,
            appid,
            return_as="list",
            verbose=False,
        )

    if not results:
        raise GameNotFoundError(appid=appid)

    await cache.set(cache_key, results)
    return results


@router.post("/batch")
async def get_games_batch(
    request: BatchRequest,
    pool: CollectorPool = Depends(get_pool),
    cache: ResponseCache = Depends(get_cache),
    settings: Settings = Depends(get_settings),
) -> list[dict[str, Any]]:
    # For batch requests we can either map to individual cache items or cache the batch.
    # The spec states cache TTL is "Per-appid" so we will loop appids.

    results = []
    uncached_appids = []

    for appid in request.appids:
        cache_key = cache.make_key(
            "game_recap" if request.recap else "game",
            appid,
            settings.region,
            settings.language,
        )
        cached = await cache.get(cache_key)
        if cached is not None:
            results.append(cached)
        else:
            uncached_appids.append((appid, cache_key))

    if uncached_appids:
        appids_to_fetch = [appid for appid, _ in uncached_appids]
        async with pool.acquire() as collector:
            fetched_results = await asyncio.to_thread(
                collector.get_games_data,
                appids_to_fetch,
                recap=request.recap,
                raise_on_error=True,
                verbose=False,
            )

        for i, data in enumerate(fetched_results):
            results.append(data)
            await cache.set(uncached_appids[i][1], data)

    return results
