"""Fixtures for GameDataModel tests."""

import pytest


@pytest.fixture
def raw_data_normal():
    """Normal raw_data with correct data types for GameDataModel."""
    return {
        "steam_appid": "12345",
        "name": "Mock Game: The Adventure",
        "developers": ["devmock_1", "devmock_2"],
        "price_final": 12.34,
        "owners": 1234,
        "tags": ["RPG", "MOBA"],
        "average_playtime_h": 1234,
        "release_date": "Jan 1, 2025",
        "is_free": True,
        "is_coming_soon": False,
        "recommendations": 1000,
        "discount": 25.5,
    }


@pytest.fixture
def raw_data_invalid_types():
    """Raw data with some invalid types for testing validation."""
    return {
        "steam_appid": 23456,  # should be a string,
        "name": "mock game 2",  # correct type
        "developers": "devmock 3",  # should be a list of string
        "price_final": "12.34",  # should be a float
        "owners": "1234",  # should be an integer
        "tags": ["RPG", "MOBA"],
        "release_date": "Not a date",  # should be a None
    }


@pytest.fixture
def raw_data_missing_steam_appid():
    """Raw data missing the required steam_appid field."""
    return {
        "name": "mock game 3",
        "developers": ["devmock_4"],
        "price_final": 12.34,
        "owners": 1234,  # missing steam_appid
    }
