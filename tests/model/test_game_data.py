import json
from datetime import datetime
from typing import Any, Callable

import pytest
from pydantic import ValidationError

from gameinsights.model.game_data import GameDataModel


def assert_game_data_values(
    model: GameDataModel, expectations: dict[str, Any | Callable[[Any], bool]]
) -> None:
    """Assert model fields match expected values or pass callable validators.

    Args:
        model: The GameDataModel instance to validate
        expectations: Dict mapping field names to either expected values or
            callable validators that receive the field value and must return bool

    Note:
        Callable validators must return bool explicitly. Any non-bool return
        (including None) will raise an AssertionError before the assertion check.
    """
    for field, expected in expectations.items():
        value = getattr(model, field)
        if callable(expected):
            outcome = expected(value)
            # Require validators to return bool explicitly
            if not isinstance(outcome, bool):
                raise AssertionError(
                    f"Validator for {field} must return bool, got {type(outcome).__name__}"
                )
            assert outcome, f"Expectation for {field} did not hold (value: {value})"
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
                "average_playtime_h": lambda value: value is None,
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
            "release_date": "2025-01-01T00:00:00",
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
        # Verify that fields marked with exclude=True are not in recap
        assert "discount" not in recap_data
        assert "average_playtime_h" not in recap_data

    def test_game_data_model_dump_json_is_serializable(self):
        """Verify model_dump(mode="json") produces valid JSON-serializable output."""
        model = GameDataModel(steam_appid="test")
        json_dict = model.model_dump(mode="json")

        # Should not raise any exceptions
        json_str = json.dumps(json_dict)

        # Verify no NaN in output
        assert "NaN" not in json_str
        assert "Infinity" not in json_str

    def test_game_data_model_get_recap_release_date_is_string(self, raw_data_normal):
        """Verify get_recap() returns ISO string for release_date."""
        model = GameDataModel(**raw_data_normal)
        recap = model.get_recap()

        assert isinstance(recap["release_date"], str)
        assert recap["release_date"] == "2025-01-01T00:00:00"

    def test_game_data_model_float_fields_default_to_none(self):
        """Verify float fields default to None."""
        model = GameDataModel(steam_appid="test")

        assert model.price_initial is None
        assert model.price_final is None
        assert model.average_playtime_h is None
        assert model.achievements_percentage_average is None
        assert model.discount is None

    def test_game_data_model_float_validator_rejects_nan_inf(self):
        """Verify NaN and inf values are converted to None."""
        model = GameDataModel(
            steam_appid="test",
            price_initial=float("nan"),
            price_final=float("inf"),
            average_playtime_h=float("-inf"),
        )

        assert model.price_initial is None
        assert model.price_final is None
        assert model.average_playtime_h is None
