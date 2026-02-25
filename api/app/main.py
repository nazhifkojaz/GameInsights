from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from gameinsights import GameInsightsError

from app.config import Settings
from app.collector_pool import CollectorPool
from app.cache import ResponseCache
from app.exceptions import gameinsights_exception_handler
from app.routers import health, games, users


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = Settings()
    pool = CollectorPool(settings)
    await pool.startup()
    cache = ResponseCache(
        maxsize=settings.cache_max_size, ttl=settings.cache_ttl_seconds
    )
    app.state.pool = pool
    app.state.cache = cache
    app.state.settings = settings
    yield
    await pool.shutdown()


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


app = create_app()
