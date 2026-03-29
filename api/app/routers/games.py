import asyncio
from typing import Any

from fastapi import APIRouter, Depends, Query
from gameinsights import GameNotFoundError
from gameinsights.utils.gamesearch import GameSearch

from app.collector_pool import CollectorPool
from app.config import Settings
from app.constants import Endpoint
from app.db_cache import DatabaseCache
from app.dependencies import get_cache, get_game_search, get_pool, get_settings
from app.schemas.games import (
    BatchRequest,
    GameResponse,
    PlayersResponse,
    SearchResult,
)

router = APIRouter(prefix="/games", tags=["games"])


@router.get("/search", response_model=list[SearchResult])
async def search_games(
    q: str,
    top_n: int = Query(default=5, ge=1, le=50),
    game_search: GameSearch = Depends(get_game_search),
) -> list[dict[str, Any]]:
    return await asyncio.to_thread(game_search.search_by_name, q, top_n=top_n)


@router.get("/{appid}", response_model=GameResponse)
async def get_game(
    appid: str,
    pool: CollectorPool = Depends(get_pool),
    cache: DatabaseCache = Depends(get_cache),
    settings: Settings = Depends(get_settings),
) -> dict[str, Any]:
    cache_key = cache.make_key(Endpoint.GAME, appid, settings.region, settings.language)
    cached = await cache.get(cache_key)
    if cached is not None:
        return cached

    async with pool.acquire() as collector:
        results = await asyncio.to_thread(
            collector.get_games_data,
            appid,
            raise_on_error=settings.collector_raise_on_error,
            verbose=settings.collector_verbose,
        )

    if not results:
        raise GameNotFoundError(identifier=appid)

    data = results[0]
    await cache.set(
        cache_key, Endpoint.GAME, appid, settings.region, settings.language, data
    )
    return data


@router.get("/{appid}/recap", response_model=GameResponse)
async def get_game_recap(
    appid: str,
    pool: CollectorPool = Depends(get_pool),
    cache: DatabaseCache = Depends(get_cache),
    settings: Settings = Depends(get_settings),
) -> dict[str, Any]:
    cache_key = cache.make_key(
        Endpoint.GAME_RECAP, appid, settings.region, settings.language
    )
    cached = await cache.get(cache_key)
    if cached is not None:
        return cached

    async with pool.acquire() as collector:
        results = await asyncio.to_thread(
            collector.get_games_data,
            appid,
            recap=True,
            raise_on_error=settings.collector_raise_on_error,
            verbose=settings.collector_verbose,
        )

    if not results:
        raise GameNotFoundError(identifier=appid)

    data = results[0]
    await cache.set(
        cache_key, Endpoint.GAME_RECAP, appid, settings.region, settings.language, data
    )
    return data


@router.get("/{appid}/reviews")
async def get_game_reviews(
    appid: str,
    pool: CollectorPool = Depends(get_pool),
    settings: Settings = Depends(get_settings),
) -> list[dict[str, Any]]:
    # Reviews are explicitly noted to have None TTL (no caching)
    async with pool.acquire() as collector:
        results = await asyncio.to_thread(
            collector.get_game_review,
            appid,
            return_as="list",
            verbose=settings.collector_verbose,
        )
    return results


@router.get("/{appid}/active-players", response_model=list[PlayersResponse])
async def get_game_active_players(
    appid: str,
    pool: CollectorPool = Depends(get_pool),
    cache: DatabaseCache = Depends(get_cache),
    settings: Settings = Depends(get_settings),
) -> list[dict[str, Any]]:
    cache_key = cache.make_key(
        Endpoint.GAME_PLAYERS, appid, settings.region, settings.language
    )
    cached = await cache.get(cache_key)
    if cached is not None:
        return cached

    async with pool.acquire() as collector:
        results = await asyncio.to_thread(
            collector.get_games_active_player_data,
            appid,
            return_as="list",
            verbose=settings.collector_verbose,
        )

    if not results:
        raise GameNotFoundError(identifier=appid)

    await cache.set(
        cache_key,
        Endpoint.GAME_PLAYERS,
        appid,
        settings.region,
        settings.language,
        results,
    )
    return results


@router.post("/batch", response_model=list[GameResponse])
async def get_games_batch(
    request: BatchRequest,
    pool: CollectorPool = Depends(get_pool),
    cache: DatabaseCache = Depends(get_cache),
    settings: Settings = Depends(get_settings),
) -> list[dict[str, Any]]:
    # For batch requests we can either map to individual cache items or cache the batch.
    # The spec states cache TTL is "Per-appid" so we will loop appids.

    results = []
    uncached_appids = []

    for appid in request.appids:
        cache_key = cache.make_key(
            Endpoint.GAME_RECAP if request.recap else Endpoint.GAME,
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
                raise_on_error=settings.collector_raise_on_error,
                verbose=settings.collector_verbose,
            )

            endpoint = Endpoint.GAME_RECAP if request.recap else Endpoint.GAME
            for i, data in enumerate(fetched_results):
                appid_i, key_i = uncached_appids[i]
                results.append(data)
                await cache.set(
                    key_i, endpoint, appid_i, settings.region, settings.language, data
                )

    return results
