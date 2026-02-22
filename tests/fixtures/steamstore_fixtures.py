"""Fixtures for SteamStore source tests."""

import pytest


@pytest.fixture
def steamstore_success_response_data():
    """Success response data for Steam Store API."""
    return {
        "12345": {
            "success": True,
            "data": {
                "type": "mock",
                "name": "Mock Game: The Adventure",
                "steam_appid": 12345,
                "is_free": True,
                "is_coming_soon": False,
                "recommendations": {"total": 1234},
                "release_date": {"coming_soon": False, "date": "Jan 1, 2025"},
                "ratings": {"pegi": {"rating": "12", "descriptors": "Bad Language"}},
            },
        }
    }


@pytest.fixture
def steamstore_success_partial_unexpected_data():
    """Success response with partial unexpected data for testing robustness."""
    return {
        "12345": {
            "success": True,
            "data": {
                "type": "mock",
                "name": "Mock Game: The Adventure",
                "steam_appid": 12345,
                "categories": [{"id": 1, "unexpected_label": "unexpected_value"}],
                "price_overview": [],  # unexpected data type
                "ratings": None,  # this as well
            },
        }
    }


@pytest.fixture
def steamstore_not_found_response_data():
    """Error response when game is not found on Steam Store."""
    return {"12345": {"success": False}}
