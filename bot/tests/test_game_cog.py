import pytest
from httpx import HTTPStatusError, Request, Response
from app.cogs.games import GamesCog


@pytest.mark.asyncio
async def test_game_command_success(mock_bot, mock_ctx, mock_api):
    # Setup mock data for success
    mock_data = {"steam_appid": "570", "name": "Dota 2", "is_free": True}
    mock_api.get_game.return_value = mock_data

    # Initialize cog
    cog = GamesCog(mock_bot)

    # Call the command callback directly
    await getattr(cog.game, "callback")(cog, mock_ctx, "570")

    # Assert defer was called
    mock_ctx.defer.assert_called_once()

    # Assert API was called correctly
    mock_api.get_game.assert_called_once_with("570")

    # Assert followup send was called with an embed
    sent_embed = mock_ctx.followup.send.call_args.kwargs["embed"]
    assert sent_embed.title == "Dota 2"


@pytest.mark.asyncio
async def test_game_command_http_error(mock_bot, mock_ctx, mock_api):
    # Setup mock for HTTP error
    error_response = Response(
        404, json={"error": "not_found", "message": "Game not found"}
    )
    mock_err = HTTPStatusError(
        "Not found", request=Request("GET", "http://test"), response=error_response
    )
    mock_api.get_game.side_effect = mock_err

    cog = GamesCog(mock_bot)

    await getattr(cog.game, "callback")(cog, mock_ctx, "999")

    mock_ctx.defer.assert_called_once()
    mock_api.get_game.assert_called_once_with("999")

    # Should send error embed
    sent_embed = mock_ctx.followup.send.call_args.kwargs["embed"]
    assert sent_embed.title == "Error"
    assert sent_embed.description == "Game not found"
