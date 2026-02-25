from app.embeds.game_embed import build_game_embed
from app.embeds.error_embed import build_error_embed
import discord


def test_build_game_embed():
    data = {
        "name": "Test Game",
        "steam_appid": "123",
        "is_free": False,
        "price_final": 19.99,
        "ccu": 500,
    }

    embed = build_game_embed(data)
    assert embed.title == "Test Game"
    assert embed.url == "https://store.steampowered.com/app/123"

    fields = {f.name: f.value for f in embed.fields}
    assert fields["Price"] == "$19.99"
    assert fields["Current Players (24h)"] == "500"


def test_build_error_embed():
    data = {
        "error": "not_found",
        "message": "Game could not be found.",
        "identifier": "999",
    }

    embed = build_error_embed(data)
    assert embed.title == "Error"
    assert embed.description == "Game could not be found."
    assert embed.color == discord.Color.orange()

    fields = {f.name: f.value for f in embed.fields}
    assert fields["Identifier"] == "999"
