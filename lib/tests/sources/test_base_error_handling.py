"""Tests for BaseSource error handling and utility methods."""

from unittest.mock import Mock, patch

from requests.exceptions import ConnectionError as RequestsConnectionError
from requests.exceptions import Timeout as RequestsTimeout

from gameinsights.sources import SteamStore


class TestFetchAndParseJson:
    """Tests for _fetch_and_parse_json error handling."""

    def test_fetch_and_parse_json_with_non_200_status(self):
        """Test that non-200 status codes return None."""
        source = SteamStore(session=None, region="us")

        # Mock response with 404 status
        mock_response = Mock()
        mock_response.status_code = 404

        result = source._fetch_and_parse_json(mock_response, verbose=False)

        assert result is None

    def test_fetch_and_parse_json_with_200_status(self):
        """Test that 200 status with valid dict returns the data."""
        source = SteamStore(session=None, region="us")

        expected_data = {"key": "value", "number": 123}
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = expected_data

        result = source._fetch_and_parse_json(mock_response, verbose=False)

        assert result == expected_data

    def test_fetch_and_parse_json_with_non_dict_response(self):
        """Test that non-dict JSON responses return None."""
        source = SteamStore(session=None, region="us")

        # Mock response returning a list instead of dict
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = ["item1", "item2"]

        result = source._fetch_and_parse_json(mock_response, verbose=False)

        assert result is None


class TestApplyLabelFilter:
    """Tests for _apply_label_filter method."""

    def test_apply_label_filter_with_none_returns_all(self):
        """Test that selected_labels=None returns all data unchanged."""
        source = SteamStore(session=None, region="us")
        data = {"steam_appid": "12345", "name": "Test Game", "price": "10.0"}

        result = source._apply_label_filter(data, None)

        assert result == data

    def test_apply_label_filter_with_valid_subset(self):
        """Test filtering with a subset of valid labels."""
        source = SteamStore(session=None, region="us")
        data = {"steam_appid": "12345", "name": "Test Game", "price": "10.0"}

        result = source._apply_label_filter(data, ["steam_appid"])

        assert result == {"steam_appid": "12345"}

    def test_apply_label_filter_with_invalid_labels(self):
        """Test that invalid labels are ignored."""
        source = SteamStore(session=None, region="us")
        data = {"steam_appid": "12345", "name": "Test Game"}

        result = source._apply_label_filter(data, ["steam_appid", "invalid_label"])

        # Should only include valid labels that exist in data
        assert result == {"steam_appid": "12345"}

    def test_apply_label_filter_empty_selected_labels(self):
        """Test with empty selected_labels list returns data unchanged."""
        source = SteamStore(session=None, region="us")
        data = {"steam_appid": "12345", "name": "Test Game"}

        # Empty list = no filtering
        result = source._apply_label_filter(data, [])

        assert result == data


class TestBaseSourceErrorPaths:
    """Tests for BaseSource error handling in fetch method."""

    def test_fetch_with_connection_error_returns_error_result(self):
        """Test that ConnectionError after retries returns error result via fetch."""
        source = SteamStore(session=None, region="us")

        # Mock session.get to raise requests.exceptions.ConnectionError
        with patch.object(
            source.session, "get", side_effect=RequestsConnectionError("Connection refused")
        ):
            result = source.fetch("12345", verbose=False)

        # fetch should handle the error and return an error result dict
        assert result["success"] is False
        assert "error" in result

    def test_fetch_with_timeout_returns_error_result(self):
        """Test that Timeout after retries returns error result via fetch."""
        source = SteamStore(session=None, region="us")

        # Mock session.get to raise requests.exceptions.Timeout
        with patch.object(source.session, "get", side_effect=RequestsTimeout("Request timed out")):
            result = source.fetch("12345", verbose=False)

        # fetch should handle the error and return an error result dict
        assert result["success"] is False
        assert "error" in result
