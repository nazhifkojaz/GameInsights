import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from gameinsights import GameInsightsError

from gameinsights.utils.gamesearch import GameSearch

from app.collector_pool import CollectorPool
from app.config import Settings
from app.database import create_pool, init_schema
from app.db_cache import DatabaseCache
from app.exceptions import gameinsights_exception_handler
from app.routers import games, health, users


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = Settings()
    pool = CollectorPool(settings)
    await pool.startup()

    db_pool = await create_pool(settings)
    await init_schema(db_pool)

    cache = DatabaseCache(db_pool)

    app.state.pool = pool
    app.state.db_pool = db_pool
    app.state.cache = cache
    app.state.settings = settings
    app.state.game_search = GameSearch()
    yield
    await pool.shutdown()
    await db_pool.close()


def create_app() -> FastAPI:
    settings = Settings()
    app = FastAPI(
        lifespan=lifespan, title=settings.api_title, version=settings.api_version
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_exception_handler(GameInsightsError, gameinsights_exception_handler)
    app.include_router(health.router)
    app.include_router(games.router)
    app.include_router(users.router)
    return app


if os.environ.get("GAMEINSIGHTS_DATABASE_URL") is None:
    os.environ["GAMEINSIGHTS_DATABASE_URL"] = "postgresql://dummy"

app = create_app()
