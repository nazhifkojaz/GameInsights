import pytest
from gameinsights import GameNotFoundError, SourceUnavailableError


@pytest.mark.asyncio
async def test_get_game_success(client):
    mock_data = {"steam_appid": "570", "name": "Dota 2"}
    client.mock_collector.get_games_data.return_value = [mock_data]

    response = await client.get("/games/570")
    assert response.status_code == 200
    assert response.json() == mock_data
    client.mock_collector.get_games_data.assert_called_once_with(
        "570", raise_on_error=True, verbose=False
    )


@pytest.mark.asyncio
async def test_get_game_not_found(client):
    client.mock_collector.get_games_data.side_effect = GameNotFoundError("99999999")

    response = await client.get("/games/99999999")
    assert response.status_code == 404
    assert response.json() == {
        "error": "not_found",
        "message": "Game with identifier '99999999' was not found.",
        "identifier": "99999999",
    }


@pytest.mark.asyncio
async def test_get_game_source_unavailable(client):
    client.mock_collector.get_games_data.side_effect = SourceUnavailableError(
        source="Steam", reason="Timeout"
    )

    response = await client.get("/games/570")
    assert response.status_code == 503
    assert response.json() == {
        "error": "source_unavailable",
        "message": "Source 'Steam' is unavailable: Timeout",
        "source": "Steam",
    }


@pytest.mark.asyncio
async def test_get_game_cached(client):
    mock_data = {"steam_appid": "570", "name": "Dota 2"}
    client.mock_collector.get_games_data.return_value = [mock_data]

    # First request
    response1 = await client.get("/games/570")
    assert response1.status_code == 200

    # Second request
    response2 = await client.get("/games/570")
    assert response2.status_code == 200
    assert response2.json() == mock_data

    # Should only be called once due to caching
    client.mock_collector.get_games_data.assert_called_once()
