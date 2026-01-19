"""Fixtures for HowLongToBeat source tests."""

import pytest


@pytest.fixture
def hltb_success_response_data():
    """Success response data for HowLongToBeat API search."""
    data = """
    {
    "count": 1,
    "pageCurrent": 1,
    "pageTotal": 1,
    "pageSize": 20,
    "data": [
        {
        "game_id": 1234,
        "game_name": "Mock Game: The Adventure",
        "game_type": "game"
        }
    ]
    }
    """

    return data


@pytest.fixture
def hltb_success_but_not_found_data():
    """Response data when game is not found on HowLongToBeat."""
    data = """
    {
    "count": 0,
    "pageCurrent": 1,
    "pageTotal": 1,
    "pageSize": 20,
    "data": []
    }
    """

    return data
