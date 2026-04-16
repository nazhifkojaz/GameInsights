import pytest


@pytest.mark.asyncio
async def test_search_games_returns_results(client):
    client.mock_game_search.search_by_name.return_value = [
        {"appid": "570", "name": "Dota 2", "search_score": 95.0},
        {"appid": "236930", "name": "DOTA 2 Workshop Tools DLC", "search_score": 72.0},
    ]

    response = await client.get("/games/search?q=dota")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    assert data[0]["appid"] == "570"
    assert data[0]["name"] == "Dota 2"
    assert data[0]["search_score"] == 95.0


@pytest.mark.asyncio
async def test_search_games_empty_results(client):
    client.mock_game_search.search_by_name.return_value = []

    response = await client.get("/games/search?q=zzznonexistent")
    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.asyncio
async def test_search_games_missing_query(client):
    response = await client.get("/games/search")
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_search_games_custom_top_n(client):
    client.mock_game_search.search_by_name.return_value = [
        {"appid": "570", "name": "Dota 2", "search_score": 95.0},
    ]

    response = await client.get("/games/search?q=dota&top_n=1")
    assert response.status_code == 200
    assert len(response.json()) == 1
    client.mock_game_search.search_by_name.assert_called_once_with("dota", top_n=1)
