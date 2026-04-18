import pytest
from httpx import HTTPStatusError, Request, Response
from app.cogs.games import GamesCog


@pytest.mark.asyncio
async def test_game_command_success(mock_bot, mock_ctx, mock_api):
    mock_data = {"steam_appid": "570", "name": "Dota 2", "is_free": True}
    mock_api.get_game.return_value = mock_data

    cog = GamesCog(mock_bot)

    await getattr(cog.game, "callback")(cog, mock_ctx, "570")

    mock_ctx.defer.assert_called_once()

    mock_api.get_game.assert_called_once_with("570")

    sent_embed = mock_ctx.followup.send.call_args.kwargs["embed"]
    assert sent_embed.title == "Dota 2"


@pytest.mark.asyncio
async def test_game_command_http_error(mock_bot, mock_ctx, mock_api):
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

    sent_embed = mock_ctx.followup.send.call_args.kwargs["embed"]
    assert sent_embed.title == "Error"
    assert sent_embed.description == "Game not found"
