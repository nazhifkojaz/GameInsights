"""Tests for Collector error handling and partial failure scenarios."""

import pytest

# Import helper functions from conftest
from tests.conftest import assert_fetch_result, assert_list_not_tuple


class TestCollectorErrorHandling:
    """Tests for error handling and partial failure scenarios."""

    def test_partial_source_failure_continues_collection(self, collector_with_one_failed_source):
        """Test that collector continues when one source fails.

        Verifies that:
        1. Game data is still returned even when one source fails
        2. Data from successful sources is included
        3. Data from the failed source is excluded
        """
        from gameinsights.model import GameDataModel

        # _fetch_raw_data should still return a GameDataModel
        game_data = collector_with_one_failed_source._fetch_raw_data(steam_appid="12345")

        assert isinstance(game_data, GameDataModel)
        assert game_data.steam_appid == "12345"

        # Fields from successful sources should be present
        assert game_data.name is not None  # From SteamStore
        assert game_data.protondb_tier is not None  # From ProtonDB
        # Note: Gamalytic source succeeds but test fixture doesn't include developers
        # The developers field would be populated by SteamStore in real usage

        # Fields from failed SteamCharts source should be None/default
        # ccu is from SteamCharts, so it should be None when SteamCharts fails
        assert game_data.ccu is None

    def test_get_games_data_with_partial_failures_and_include_failures(
        self, collector_with_one_failed_source
    ):
        """Test get_games_data with include_failures=True when some sources fail.

        Verifies that:
        1. Data is still returned when sources partially fail
        2. FetchResult correctly reports success even with partial source failures
        3. The error is captured in the FetchResult when available
        """
        games_data, results = collector_with_one_failed_source.get_games_data(
            steam_appids=["12345"], include_failures=True
        )

        assert len(games_data) == 1
        assert len(results) == 1
        # Result should be successful because primary source (SteamStore) succeeded
        assert_fetch_result(results[0], "12345", success=True)

    def test_raise_on_error_with_primary_source_failure(
        self, mock_request_response, monkeypatch
    ):
        """Test that raise_on_error=True raises GameNotFoundError when primary source fails."""
        from gameinsights import Collector, GameNotFoundError
        from gameinsights.sources import HowLongToBeat, SteamStore

        # Mock SteamStore to return a not found error
        mock_request_response(
            target_class=SteamStore,
            json_data={
                "success": False,
                "error": (
                    "Failed to fetch data for appid 99999, or appid is not available in the specified region (us) or language (english)."
                ),
            },
        )

        # Mock HowLongToBeat to succeed (needed for collector initialization)
        mock_request_response(
            target_class=HowLongToBeat,
            text_data="<div>mock data</div>",
        )

        # Mock the HowLongToBeat token method
        def mock_get_token(*args, **kwargs):
            return "mock_token"

        monkeypatch.setattr(HowLongToBeat, "_get_search_token", mock_get_token)

        collector = Collector()

        with pytest.raises(GameNotFoundError) as exc_info:
            collector.get_games_data("99999", raise_on_error=True)

        assert exc_info.value.identifier == "99999"

    def test_raise_on_error_false_with_primary_source_failure(
        self, mock_request_response, monkeypatch
    ):
        """Test that raise_on_error=False (default) returns partial data when primary source fails.

        When the primary source (SteamStore) fails but raise_on_error=False, the collector
        returns data with default/None values for fields from the failed source. This is the
        "silent partial data" behavior - errors are absorbed rather than raising exceptions.
        """
        from gameinsights import Collector
        from gameinsights.sources import HowLongToBeat, SteamStore

        # Mock SteamStore to return a not found error
        mock_request_response(
            target_class=SteamStore,
            json_data={
                "success": False,
                "error": (
                    "Failed to fetch data for appid 99999, or appid is not available in the specified region (us) or language (english)."
                ),
            },
        )

        # Mock HowLongToBeat to succeed
        mock_request_response(
            target_class=HowLongToBeat,
            text_data="<div>mock data</div>",
        )

        # Mock the HowLongToBeat token method
        def mock_get_token(*args, **kwargs):
            return "mock_token"

        monkeypatch.setattr(HowLongToBeat, "_get_search_token", mock_get_token)

        collector = Collector()

        # With raise_on_error=False, returns data with default values for missing fields
        result = collector.get_games_data("99999", raise_on_error=False)
        assert_list_not_tuple(result, expected_len=1)
        # Name should be None since SteamStore failed
        assert result[0]["steam_appid"] == "99999"
        assert result[0]["name"] is None


class TestCollectorFailureReporting:
    """Tests for include_failures parameter and FetchResult reporting."""

    def test_get_games_data_with_failures_returns_tuple(self, collector_with_mocks):
        """Test that include_failures=True returns tuple with FetchResult list."""
        games_data, results = collector_with_mocks.get_games_data(
            steam_appids=["12345"], include_failures=True
        )

        assert isinstance(games_data, list)
        assert isinstance(results, list)
        assert len(results) == 1
        assert_fetch_result(results[0], "12345")

    def test_get_games_data_backward_compatible(self, collector_with_mocks):
        """Test that default behavior (include_failures=False) returns list only."""
        games_data = collector_with_mocks.get_games_data(steam_appids=["12345"])
        assert_list_not_tuple(games_data, expected_len=1)

    def test_get_games_data_empty_input_with_failures(self, collector_with_mocks):
        """Test that empty input returns empty results with include_failures=True."""
        games_data, results = collector_with_mocks.get_games_data(
            steam_appids=[], include_failures=True
        )

        assert games_data == []
        assert results == []

    def test_get_games_active_player_data_with_failures(self, collector_with_mocks):
        """Test that include_failures=True returns tuple with FetchResult list."""
        data, results = collector_with_mocks.get_games_active_player_data(
            steam_appids=["12345"], include_failures=True
        )

        assert isinstance(data, list)
        assert isinstance(results, list)
        assert len(results) == 1
        assert_fetch_result(results[0], "12345")
