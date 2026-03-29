from app.embeds.game_embed import build_game_embed, build_players_graph
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


def test_build_players_graph():
    """Test that player graph generation works with monthly data."""
    data = [
        {
            "name": "Test Game",
            "peak_active_player_all_time": 100000,
            "2024-01": 50000,
            "2024-02": 55000,
            "2024-03": 60000,
            "2024-04": 58000,
            "2024-05": 62000,
        }
    ]

    file = build_players_graph(data, appid="123")
    assert file.filename == "player_history.png"
    assert file.fp is not None


def test_build_players_graph_empty_data():
    """Test that empty data is handled gracefully."""
    file = build_players_graph([], appid="123")
    assert file.filename == "player_history.png"


def test_build_players_graph_no_monthly_data():
    """Test handling of data without monthly player counts."""
    data = [
        {
            "name": "Test Game",
            "peak_active_player_all_time": 100000,
        }
    ]

    file = build_players_graph(data, appid="123")
    assert file.filename == "player_history.png"
