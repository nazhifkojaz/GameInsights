import math
from datetime import datetime
from typing import Any, Callable

import pytest
from pydantic import ValidationError

from gameinsights.model.game_data import GameDataModel

Expectation = Callable[[Any], None] | Any


def assert_game_data_values(model: GameDataModel, expectations: dict[str, Expectation]) -> None:
    for field, expected in expectations.items():
        value = getattr(model, field)
        if callable(expected):
            outcome = expected(value)
            if outcome is not None:
                assert outcome, f"Expectation for {field} did not hold"
        else:
            assert value == expected, f"Expected {field} to be {expected}, got {value}"


def assert_model_field_count(model: GameDataModel) -> None:
    included_fields = {
        name for name, field in GameDataModel.model_fields.items() if not field.exclude
    }
    assert set(model.model_dump().keys()) == included_fields


class TestGameDataModel:
    def test_game_data_model_normal_data(self, raw_data_normal):
        game_data = GameDataModel(**raw_data_normal)

        # check if the model is created correctly
        assert isinstance(game_data, GameDataModel)

        assert_game_data_values(
            game_data,
            {
                "steam_appid": "12345",
                "release_date": lambda value: (
                    isinstance(value, datetime) and value == datetime(2025, 1, 1)
                ),
                "is_free": True,
                "is_coming_soon": False,
                "recommendations": 1000,
                "discount": 25.5,
            },
        )
        assert_model_field_count(game_data)

    def test_game_data_model_invalid_types(self, raw_data_invalid_types):
        game_data = GameDataModel(**raw_data_invalid_types)

        # check if the model is created correctly
        assert isinstance(game_data, GameDataModel)

        assert_game_data_values(
            game_data,
            {
                "release_date": lambda value: value is None,
                "average_playtime_h": lambda value: math.isnan(value),
                "average_playtime": lambda value: value is None,
                "steam_appid": "23456",
                "developers": ["devmock 3"],
                "price_final": 12.34,
                "owners": 1234,
            },
        )
        assert_model_field_count(game_data)

    def test_game_data_model_missing_steam_appid(self, raw_data_missing_steam_appid):
        # should raise a ValidationError if steam_appid is missing
        with pytest.raises(ValidationError):
            GameDataModel(**raw_data_missing_steam_appid)

    @pytest.mark.parametrize(
        "raw_data_fixture, expected_playtime, expected_days_since_release",
        [
            ("raw_data_normal", 1234 * 3600, (datetime.now() - datetime(2025, 1, 1)).days),
            ("raw_data_invalid_types", None, None),
        ],
        ids=["normal_data", "missing_playtime_and_days_since_release"],
    )
    def test_game_data_model_preprocess_data(
        self,
        request,
        raw_data_fixture,
        expected_playtime,
        expected_days_since_release,
    ):
        raw_data = request.getfixturevalue(raw_data_fixture)
        game_data = GameDataModel(**raw_data)

        # check if the model is created correctly
        assert isinstance(game_data, GameDataModel)

        # check if average_playtime is set correctly
        assert game_data.average_playtime == expected_playtime

        # check if days_since_release is set correctly
        assert game_data.days_since_release == expected_days_since_release

    def test_game_data_model_get_recap(self, raw_data_normal):
        game_data = GameDataModel(**raw_data_normal)

        # check if the recap data is correct
        recap_data = game_data.get_recap()
        assert isinstance(recap_data, dict)

        expectations = {
            "steam_appid": "12345",
            "name": "Mock Game: The Adventure",
            "developers": ["devmock_1", "devmock_2"],
            "release_date": datetime(2025, 1, 1),
            "price_final": 12.34,
            "owners": 1234,
            "tags": ["RPG", "MOBA"],
            "average_playtime": 1234 * 3600,
            "total_reviews": None,
            "is_free": True,
            # New recap fields
            "protondb_tier": "platinum",
            "early_access": False,
            "metacritic_score": 85,
        }

        for field, expected in expectations.items():
            assert recap_data[field] == expected, f"{field} expectation failed"

        # check the length of the recap data
        assert len(recap_data) == len(game_data._RECAP_FIELDS)
        assert "count_retired" not in recap_data  # this field should not be in recap data
