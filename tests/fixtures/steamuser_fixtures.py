"""Fixtures for SteamUser source tests."""

import pytest


@pytest.fixture
def usersummary_success_response_open_profile():
    """Success response for user summary with public profile."""
    return {
        "response": {
            "players": [
                {
                    "steamid": "12345",
                    "communityvisibilitystate": 3,
                    "profilestate": 1,
                    "personaname": "Mock Player",
                    "profileurl": "https://mocksteam.com/profiles/12345",
                    "lastlogoff": 123456789,
                    "realname": "Mock Player The Third",
                    "timecreated": 123456789,
                    "loccountrycode": "MO",
                    "locstatecode": "CK",
                    "loccityid": 12,
                }
            ]
        }
    }


@pytest.fixture
def usersummary_success_response_closed_profile():
    """Success response for user summary with private profile."""
    return {
        "response": {
            "players": [
                {
                    "steamid": "12345",
                    "communityvisibilitystate": 1,
                    "profilestate": 1,
                    "personaname": "Private Mockو",
                    "profileurl": "https://mocksteam.com/profiles/12345",
                    "personastate": 0,
                }
            ]
        }
    }


@pytest.fixture
def usersummary_not_found_response_data():
    """Error response when user is not found."""
    return {"response": {"players": []}}


@pytest.fixture
def owned_games_exclude_free_response():
    """Response for owned games excluding free games."""
    return {
        "response": {
            "game_count": 2,
            "games": [
                {"appid": 12345, "playtime_forever": 123},
                {"appid": 23456, "playtime_forever": 1234},
            ],
        }
    }


@pytest.fixture
def owned_games_include_free_response():
    """Response for owned games including free games."""
    return {
        "response": {
            "game_count": 3,
            "games": [
                {"appid": 12345, "playtime_forever": 123},
                {"appid": 23456, "playtime_forever": 1234},
                {"appid": 570, "playtime_forever": 12345},  # free game / Dota 2
            ],
        }
    }


@pytest.fixture
def owned_games_no_games_owned():
    """Response when user owns no games."""
    return {"response": {}}


@pytest.fixture
def owned_games_only_own_free_games():
    """Response when user only owns free games."""
    return {
        "response": {
            "game_count": 1,
            "games": [
                {
                    "appid": 570,
                    "playtime_forever": 12345,
                }
            ],
        }
    }


@pytest.fixture
def recently_played_games_active_player_response_data():
    """Response for recently played games by an active player."""
    return {
        "response": {
            "total_count": 2,
            "games": [
                {
                    "appid": 12345,
                    "name": "Mock Game",
                    "playtime_2weeks": 12,
                    "playtime_forever": 123,
                },
                {
                    "appid": 23456,
                    "name": "Mock Online",
                    "playtime_2weeks": 1,
                    "playtime_forever": 1234,
                },
            ],
        }
    }


@pytest.fixture
def recently_played_games_free_player_response_data():
    """Response for recently played games by a free-only player."""
    return {
        "response": {
            "total_count": 1,
            "games": [
                {
                    "appid": 570,
                    "name": "Dota 2",
                    "playtime_2weeks": 1234,
                    "playtime_forever": 12345,
                }
            ],
        }
    }


@pytest.fixture
def recently_played_games_inactive_player_response_data():
    """Response for recently played games by an inactive player."""
    return {"response": {}}
