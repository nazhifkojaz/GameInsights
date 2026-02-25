import pytest
from unittest.mock import AsyncMock, MagicMock
from httpx import AsyncClient, ASGITransport

from app.main import create_app
from app.collector_pool import CollectorPool
from app.cache import ResponseCache
from app.config import Settings


@pytest.fixture
def mock_pool():
    pool = AsyncMock(spec=CollectorPool)
    mock_collector = MagicMock()
    pool.acquire.return_value.__aenter__ = AsyncMock(return_value=mock_collector)
    pool.acquire.return_value.__aexit__ = AsyncMock(return_value=False)
    # mock size and available properties
    type(pool).size = property(lambda self: 3)
    type(pool).available = property(lambda self: 3)
    return pool, mock_collector


@pytest.fixture
def mock_cache():
    return ResponseCache(maxsize=10, ttl=60)


@pytest.fixture
async def client(mock_pool, mock_cache):
    app = create_app()
    pool, mock_collector = mock_pool
    app.state.pool = pool
    app.state.cache = mock_cache
    app.state.settings = Settings(steam_api_key="test")

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        ac.mock_collector = mock_collector
        yield ac
