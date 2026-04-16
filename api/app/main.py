from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from gameinsights import GameInsightsError

from app.collector_pool import CollectorPool
from app.config import Settings
from app.database import create_engine, create_session_factory
from app.db_cache import DatabaseCache
from app.exceptions import gameinsights_exception_handler
from app.game_search import GameSearch
from app.routers import games, health, users


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings: Settings = app.state.settings
    pool = CollectorPool(settings)
    await pool.startup()

    try:
        engine = create_engine(settings)
        session_factory = create_session_factory(engine)
        cache = DatabaseCache(session_factory)
    except Exception:
        await pool.shutdown()
        raise

    app.state.pool = pool
    app.state.engine = engine
    app.state.cache = cache
    app.state.game_search = GameSearch(
        settings.steam_api_key.get_secret_value() if settings.steam_api_key else ""
    )
    yield
    await pool.shutdown()
    await engine.dispose()


def create_app() -> FastAPI:
    settings = Settings()

    app = FastAPI(
        lifespan=lifespan, title=settings.api_title, version=settings.api_version
    )
    app.state.settings = settings
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
