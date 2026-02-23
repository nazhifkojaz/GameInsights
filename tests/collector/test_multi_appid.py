"""Tests for Collector with multiple appids and mixed success/failure scenarios."""

from unittest.mock import patch

import pytest

from gameinsights import Collector, GameNotFoundError


class TestMultiAppidScenarios:
    """Tests for handling multiple appids with mixed success/failure."""

    def test_get_games_data_multiple_success(self, collector_with_mocks):
        """Test get_games_data with multiple successful appids."""
        result = collector_with_mocks.get_games_data(["12345", "12345"])

        assert len(result) == 2
        assert all(isinstance(item, dict) for item in result)

    def test_get_games_data_mixed_success_failure_with_raise_on_error(
        self, mock_request_response, monkeypatch, request, collector_with_mocks
    ):
        """Test get_games_data with mixed success/failure and raise_on_error=True.

        When raise_on_error=True and multiple appids are provided where some fail,
        the first failure should raise an exception (short-circuit behavior).
        """
        from gameinsights.sources import SteamStore

        # First appid succeeds, second fails
        call_count = [0]

        def mock_get(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] == 1:
                # First call - success
                return {
                    "success": True,
                    "data": {"steam_appid": "12345", "name": "Success Game"},
                }
            else:
                # Second call - failure
                return {
                    "success": False,
                    "error": (
                        "Failed to fetch data for appid 99999, or appid is not available in the specified region (us) or language (english)."
                    ),
                }

        # Use collector_with_mocks but override SteamStore.fetch for this test
        with patch.object(SteamStore, "fetch", side_effect=mock_get):
            # Should raise on the first failure
            with pytest.raises(GameNotFoundError):
                collector_with_mocks.get_games_data(["12345", "99999"], raise_on_error=True)

    def test_get_games_data_with_include_failures_multiple_appids(self, collector_with_mocks):
        """Test get_games_data with include_failures=True for multiple appids."""
        games_data, results = collector_with_mocks.get_games_data(
            ["12345", "12345"], include_failures=True
        )

        assert len(games_data) == 2
        assert len(results) == 2
        # All should succeed with mocked collector
        assert all(r.success for r in results)

    def test_get_games_data_duplicate_appids(self, collector_with_mocks):
        """Test that duplicate appids are processed independently."""
        result = collector_with_mocks.get_games_data(["12345", "12345"])

        assert len(result) == 2
        assert result[0]["steam_appid"] == "12345"
        assert result[1]["steam_appid"] == "12345"

    def test_get_games_data_empty_list_with_raise_on_error(self, monkeypatch):
        """Test get_games_data with empty list and raise_on_error=True."""
        from gameinsights import InvalidRequestError
        from gameinsights.sources import HowLongToBeat

        monkeypatch.setattr(HowLongToBeat, "_get_search_token", lambda *args: "token")

        collector = Collector()

        with pytest.raises(InvalidRequestError):
            collector.get_games_data([], raise_on_error=True)

    def test_get_games_data_empty_list_without_raise_on_error(self, monkeypatch):
        """Test get_games_data with empty list and raise_on_error=False."""
        from gameinsights.sources import HowLongToBeat

        monkeypatch.setattr(HowLongToBeat, "_get_search_token", lambda *args: "token")

        collector = Collector()

        result = collector.get_games_data([], raise_on_error=False)

        assert result == []
