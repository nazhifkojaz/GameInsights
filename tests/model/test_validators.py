"""Tests for GameDataModel validators with edge cases."""

import datetime
import json

from gameinsights.model.game_data import GameDataModel


class TestValidatorsEdgeCases:
    """Tests for validator edge cases and special inputs."""

    def test_parse_release_date_with_unix_timestamp(self):
        """Test that Unix timestamps are correctly converted to datetime."""
        # Use datetime.fromtimestamp() to compute the expected value,
        # which matches the behavior in GameDataModel.parse_release_date
        unix_ts = 1735689600
        expected = datetime.datetime.fromtimestamp(unix_ts)

        model = GameDataModel(steam_appid="test", release_date=unix_ts)

        assert isinstance(model.release_date, datetime.datetime)
        assert model.release_date == expected

    def test_handle_integers_with_string_numbers(self):
        """Test that string numbers are converted to integers."""
        model = GameDataModel(
            steam_appid="test",
            recommendations="1000",  # String number
            owners="5000",
            followers="250",
        )

        assert model.recommendations == 1000
        assert model.owners == 5000
        assert model.followers == 250

    def test_handle_float_with_string_numbers(self):
        """Test that string floats are converted to float."""
        model = GameDataModel(
            steam_appid="test",
            price_initial="10.50",
            price_final="5.25",
            average_playtime_h="2.5",
        )

        assert model.price_initial == 10.50
        assert model.price_final == 5.25
        assert model.average_playtime_h == 2.5

    def test_ensure_string_with_numeric_input(self):
        """Test that numeric inputs are converted to strings."""
        model = GameDataModel(
            steam_appid="test",
            name=12345,  # Numeric input
        )

        assert model.name == "12345"

    def test_ensure_list_with_string_input(self):
        """Test that string input is converted to single-element list."""
        model = GameDataModel(
            steam_appid="test",
            developers="Single Developer",  # String instead of list
            publishers="Single Publisher",
        )

        assert model.developers == ["Single Developer"]
        assert model.publishers == ["Single Publisher"]

    def test_parse_release_date_with_invalid_string(self):
        """Test that invalid date strings are handled gracefully."""
        model = GameDataModel(
            steam_appid="test",
            release_date="invalid-date-string",
        )

        # Invalid dates should be converted to None
        assert model.release_date is None

    def test_parse_release_date_with_empty_string(self):
        """Test that empty string for date is handled."""
        model = GameDataModel(
            steam_appid="test",
            release_date="",
        )

        assert model.release_date is None

    def test_handle_integers_with_invalid_string(self):
        """Test that non-numeric strings are handled."""
        model = GameDataModel(
            steam_appid="test",
            recommendations="not-a-number",
        )

        # Invalid integer strings should be converted to None
        assert model.recommendations is None

    def test_handle_float_with_invalid_string(self):
        """Test that invalid float strings are handled."""
        model = GameDataModel(
            steam_appid="test",
            price_final="not-a-float",
        )

        # Invalid float strings should be converted to None
        assert model.price_final is None


class TestComputedPropertiesWithNone:
    """Tests for computed properties when inputs are None."""

    def test_compute_average_playtime_with_none(self):
        """Test that average_playtime is not set when average_playtime_h is None."""
        model = GameDataModel(
            steam_appid="test",
            average_playtime_h=None,
        )

        # average_playtime should remain None
        assert model.average_playtime is None

    def test_compute_days_since_release_with_none(self):
        """Test that days_since_release is not set when release_date is None."""
        model = GameDataModel(
            steam_appid="test",
            release_date=None,
        )

        # days_since_release should remain None
        assert model.days_since_release is None

    def test_compute_average_playtime_with_zero(self):
        """Test that zero playtime is handled correctly."""
        model = GameDataModel(
            steam_appid="test",
            average_playtime_h=0,
        )

        # average_playtime should be 0 (0 * 3600 = 0)
        assert model.average_playtime == 0

    def test_compute_days_since_release_with_future_date(self):
        """Test that future dates produce negative days_since_release."""
        future_date = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=30)
        model = GameDataModel(
            steam_appid="test",
            release_date=future_date.replace(tzinfo=None),
        )

        # days_since_release should be negative for future dates
        assert model.days_since_release < 0


class TestJSONSerializationEdgeCases:
    """Tests for JSON serialization with various data types."""

    def test_json_serialization_with_datetime(self):
        """Test that datetime is serialized to ISO string."""
        model = GameDataModel(
            steam_appid="test",
            release_date=datetime.datetime(2025, 1, 1, 12, 30, 45),
        )

        json_dict = model.model_dump(mode="json")
        assert json_dict["release_date"] == "2025-01-01T12:30:45"

    def test_json_serialization_with_none_values(self):
        """Test that None values are serialized as JSON null."""
        model = GameDataModel(steam_appid="test", price_final=None)

        json_dict = model.model_dump(mode="json")
        assert json_dict["price_final"] is None

        # Should be JSON serializable
        json_str = json.dumps(json_dict)
        assert '"price_final": null' in json_str
