"""Fixtures for Gamalytic source tests."""

import pytest


@pytest.fixture
def gamalytic_success_response_data():
    """Success response data for Gamalytic API."""
    return {
        "steamId": "12345",
        "name": "Mock Game: The Adventure",
        "price": 12.34,
        "reviews": 1234,
        "reviewsSteam": 1234,
        "followers": 1234,
        "avgPlaytime": 12.34,
    }
