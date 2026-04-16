import functools

import pytest
import pytest_asyncio

from app.constants import ENDPOINT_TTL, Endpoint
from app.db_cache import DatabaseCache


@functools.lru_cache(maxsize=1)
def is_docker_available() -> bool:
    try:
        import docker
    except ImportError:
        return False
    try:
        client = docker.from_env()
        client.ping()
    except docker.errors.DockerException:
        return False
    return True


@pytest.mark.asyncio
async def test_make_key_consistency():
    key1 = DatabaseCache.make_key(Endpoint.GAME, "570", "us", "english")
    key2 = DatabaseCache.make_key(Endpoint.GAME, "570", "us", "english")
    assert key1 == key2
    # Keys should be human-readable, not MD5 hashes
    assert "570" in key1
    assert "us" in key1
    assert "english" in key1


@pytest.mark.asyncio
async def test_make_key_different_params():
    key1 = DatabaseCache.make_key(Endpoint.GAME, "570", "us", "english")
    key2 = DatabaseCache.make_key(Endpoint.GAME, "570", "eu", "english")
    assert key1 != key2


@pytest.mark.asyncio
async def test_ttl_values():
    assert ENDPOINT_TTL[Endpoint.GAME] == 21600
    assert ENDPOINT_TTL[Endpoint.GAME_RECAP] == 21600
    assert ENDPOINT_TTL[Endpoint.GAME_REVIEWS] == 43200
    assert ENDPOINT_TTL[Endpoint.GAME_PLAYERS] == 3600
    assert ENDPOINT_TTL[Endpoint.USER] == 86400


@pytest.mark.skipif(not is_docker_available(), reason="Docker not available")
class TestDatabaseCacheIntegration:
    """Integration tests requiring Docker/testcontainers."""

    @pytest.fixture(scope="module")
    def postgres_url(self):
        from testcontainers.postgres import PostgresContainer

        with PostgresContainer("postgres:16-alpine") as postgres:
            yield postgres.get_connection_url()

    @pytest_asyncio.fixture(loop_scope="function")
    async def cache(self, postgres_url):
        from app.config import Settings
        from app.database import create_engine, create_session_factory
        from app.models import Base

        settings = Settings(database_url=postgres_url)
        engine = create_engine(settings)
        session_factory = create_session_factory(engine)
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
            await conn.run_sync(Base.metadata.create_all)
        yield DatabaseCache(session_factory)
        await engine.dispose()

    @pytest.mark.asyncio
    async def test_get_missing_key(self, cache):
        result = await cache.get("nonexistent_key")
        assert result is None

    @pytest.mark.asyncio
    async def test_set_and_get(self, cache):
        key = cache.make_key(Endpoint.GAME, "570", "us", "english")
        data = {"steam_appid": "570", "name": "Dota 2"}

        await cache.set(key, Endpoint.GAME, "570", "us", "english", data)
        result = await cache.get(key)

        assert result == data

    @pytest.mark.asyncio
    async def test_set_updates_existing(self, cache):
        key = cache.make_key(Endpoint.GAME, "570", "us", "english")
        data_v1 = {"steam_appid": "570", "name": "Dota 2"}
        data_v2 = {"steam_appid": "570", "name": "Dota 2 Updated"}

        await cache.set(key, Endpoint.GAME, "570", "us", "english", data_v1)
        await cache.set(key, Endpoint.GAME, "570", "us", "english", data_v2)
        result = await cache.get(key)

        assert result == data_v2
