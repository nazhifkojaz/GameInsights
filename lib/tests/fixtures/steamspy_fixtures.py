"""Fixtures for SteamSpy source tests."""

import pytest


@pytest.fixture
def steamspy_success_response_data():
    """Success response data for SteamSpy API."""
    return {
        "appid": 12345,
        "name": "Mock Game: The Adventure",
        "positive": 1234,
        "negative": 12,
        "discount": 25.5,
    }


@pytest.fixture
def steamspy_success_unexpected_data():
    """Response data with unexpected types for testing robustness."""
    return {
        "appid": 12345,
        "name": "Mock Game: The Adventure",
        "positive": [1234],
        "negative": 12,
        "tags": None,  # unexpected None value
    }


@pytest.fixture
def steamspy_not_found_response_data():
    """Response data when game is not found on SteamSpy."""
    return {
        "appid": 12345,
        "name": None,
        "developer": "",
        "publisher": "",
        "positive": 0,
        "negative": 0,
    }
