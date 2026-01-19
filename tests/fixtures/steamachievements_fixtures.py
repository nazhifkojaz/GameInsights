"""Fixtures for SteamAchievements source tests."""

import pytest


@pytest.fixture
def achievements_success_response_data():
    """Success response data for achievements API."""
    return {
        "achievementpercentages": {
            "achievements": [
                {"name": "Mock_1", "percent": "12.3"},
                {"name": "Mock_2", "percent": "12.3"},
            ]
        }
    }


@pytest.fixture
def achievements_success_with_unexpected_data():
    """Response data with unexpected field names for testing robustness."""
    return {
        "achievementpercentages": {
            "achievements": [
                {"nama": "Mock_1", "percent": "12.3"},  # incorrect 'name' label
                {"name": "Mock_2", "percen": "12.3"},  # incorrect 'percent' label
                {"name": "Mock_3", "percent": "12.3"},  # correct label
            ]
        }
    }


@pytest.fixture
def scheme_success_response_data():
    """Success response data for schema API."""
    return {
        "game": {
            "gameName": "Mock Game: The Adventure",
            "gameVersion": "1",
            "availableGameStats": {
                "achievements": [
                    {
                        "name": "Mock_1",
                        "defaultValue": 0,
                        "displayName": "Mock One",
                        "hidden": 0,
                        "description": "Clear Mock One",
                        "icon": "https://someurl.com",
                        "icongray": "https://anotherurl.com",
                    },
                    {
                        "name": "Mock_2",
                        "defaultValue": 0,
                        "displayName": "Mock Two",
                        "hidden": 1,
                        "icon": "https://someurl.com",
                        "icongray": "https://anotherurl.com",
                    },
                ]
            },
        }
    }
