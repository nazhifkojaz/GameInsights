from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.collector_pool import CollectorPool
from app.config import Settings
from app.main import create_app


class TestClient(AsyncClient):
    """Extended AsyncClient with mock_collector attribute for testing."""

    mock_collector: Any
    mock_game_search: Any


class InMemoryCache:
    """Lightweight in-memory stub that emulates DatabaseCache interface for testing."""

    def __init__(self) -> None:
        self._store: dict[str, Any] = {}

    @staticmethod
    def make_key(endpoint: str, identifier: str, region: str, language: str) -> str:
        return f"{endpoint}:{identifier}:{region}:{language}"

    async def get(self, key: str) -> Any | None:
        return self._store.get(key)

    async def set(
        self,
        key: str,
        endpoint: str,
        identifier: str,
        region: str,
        language: str,
        data: Any,
    ) -> None:
        self._store[key] = data


@pytest.fixture
def mock_pool():
    pool = AsyncMock(spec=CollectorPool)
    mock_collector = MagicMock()
    pool.acquire.return_value.__aenter__ = AsyncMock(return_value=mock_collector)
    pool.acquire.return_value.__aexit__ = AsyncMock(return_value=False)
    type(pool).size = property(lambda self: 3)
    type(pool).available = property(lambda self: 3)
    return pool, mock_collector


@pytest.fixture
def mock_cache():
    return InMemoryCache()


@pytest.fixture
def mock_game_search():
    return MagicMock()


@pytest_asyncio.fixture
async def client(mock_pool, mock_cache, mock_game_search, monkeypatch):
    monkeypatch.setenv("GAMEINSIGHTS_DATABASE_URL", "postgresql://dummy")
    app = create_app()
    pool, mock_collector = mock_pool
    settings = Settings(steam_api_key="test", database_url="postgresql://dummy")
    app.state.pool = pool
    app.state.cache = mock_cache
    app.state.settings = settings
    app.state.game_search = mock_game_search
    from app.dependencies import get_cache, get_game_search, get_pool, get_settings

    app.dependency_overrides[get_pool] = lambda: pool
    app.dependency_overrides[get_cache] = lambda: mock_cache
    app.dependency_overrides[get_settings] = lambda: settings
    app.dependency_overrides[get_game_search] = lambda: mock_game_search

    async with TestClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        ac.mock_collector = mock_collector
        ac.mock_game_search = mock_game_search
        yield ac
