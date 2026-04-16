import pytest

from app.config import Settings


@pytest.mark.asyncio
async def test_health_check(client):
    response = await client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "api_title" in data
    assert "pool_size" in data
    assert data["pool_size"] == Settings.model_fields["collector_pool_size"].default
