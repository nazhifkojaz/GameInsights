"""Tests for Collector error classification and raise_on_error functionality."""

import pytest

from gameinsights import (
    Collector,
    GameInsightsError,
    GameNotFoundError,
    InvalidRequestError,
    SourceUnavailableError,
)
from gameinsights.sources import HowLongToBeat


class TestCollectorErrorClassification:
    """Test _classify_source_error method."""

    @pytest.mark.parametrize(
        "source, message, expected_exception, expected_attrs",
        [
            (
                "SteamStore",
                "Failed to fetch data for appid 12345, or appid is not available in the specified region (us) or language (english).",
                GameNotFoundError,
                {"identifier": "12345"},
            ),
            (
                "Gamalytic",
                "Game with appid 12345 is not found.",
                GameNotFoundError,
                {"identifier": "12345"},
            ),
            (
                "SteamUser",
                "steamid 76561198000000000 not found.",
                GameNotFoundError,
                {"identifier": "76561198000000000"},
            ),
            (
                "SteamStore",
                "Failed to connect. Status code: 599.",
                SourceUnavailableError,
                {"source": "SteamStore"},
            ),
            (
                "Gamalytic",
                "Connection error occurred",
                SourceUnavailableError,
                {},
            ),
            (
                "SteamCharts",
                "Request timeout",
                SourceUnavailableError,
                {},
            ),
            (
                "ProtonDB",
                "Failed with status code: 503",
                SourceUnavailableError,
                {},
            ),
            (
                "SteamCharts",
                "Failed to parse data, game name is not found.",
                SourceUnavailableError,
                {"source": "SteamCharts"},
            ),
            (
                "SomeSource",
                "Unexpected error occurred",
                GameInsightsError,
                {},
            ),
            (
                "SteamStore",
                "Game with APPID 12345 NOT FOUND.",
                GameNotFoundError,
                {"identifier": "12345"},
            ),
        ],
        ids=[
            "steamstore_not_available",
            "gamalytic_not_found_appid",
            "steamuser_not_found_steamid",
            "network_error_599",
            "connection_error",
            "timeout_error",
            "http_error_status",
            "parse_error",
            "unknown_error",
            "case_insensitive",
        ],
    )
    def test_classify_source_error(self, source, message, expected_exception, expected_attrs):
        """Test _classify_source_error classifies errors correctly."""
        exc = Collector._classify_source_error(source, message)
        assert isinstance(exc, expected_exception)
        for attr, value in expected_attrs.items():
            assert getattr(exc, attr) == value


class TestRaiseForFetchFailure:
    """Test _raise_for_fetch_failure method."""

    @pytest.fixture(autouse=True)
    def _mock_hltb_token(self, monkeypatch):
        monkeypatch.setattr(HowLongToBeat, "_get_search_token", lambda *a, **kw: "mock_token")

    def test_primary_source_not_found_raises_game_not_found(self):
        """Test primary source 'not found' raises GameNotFoundError."""
        collector = Collector()
        with pytest.raises(GameNotFoundError) as exc_info:
            collector._raise_for_fetch_failure(
                source_name="SteamStore",
                error_message="Game with appid 12345 is not found.",
                is_primary=True,
            )
        assert exc_info.value.identifier == "12345"

    def test_supplementary_source_not_found_raises_source_unavailable(self):
        """Test supplementary source 'not found' raises SourceUnavailableError."""
        collector = Collector()
        with pytest.raises(SourceUnavailableError) as exc_info:
            collector._raise_for_fetch_failure(
                source_name="ProtonDB",
                error_message="Game 12345 not found on ProtonDB.",
                is_primary=False,
            )
        assert exc_info.value.source == "ProtonDB"

    def test_primary_source_network_error_raises_source_unavailable(self):
        """Test primary source network error raises SourceUnavailableError."""
        collector = Collector()
        with pytest.raises(SourceUnavailableError):
            collector._raise_for_fetch_failure(
                source_name="SteamStore",
                error_message="Connection timeout",
                is_primary=True,
            )


class TestRaiseOnErrorParameter:
    """Test raise_on_error parameter in public methods."""

    @pytest.fixture(autouse=True)
    def _mock_hltb_token(self, monkeypatch):
        monkeypatch.setattr(HowLongToBeat, "_get_search_token", lambda *a, **kw: "mock_token")

    def test_get_games_data_empty_input_with_raise_on_error(self):
        """Test get_games_data with empty input and raise_on_error=True."""
        collector = Collector()
        with pytest.raises(InvalidRequestError):
            collector.get_games_data([], raise_on_error=True)

    def test_get_games_data_empty_input_without_raise_on_error(self):
        """Test get_games_data with empty input and raise_on_error=False (default)."""
        collector = Collector()
        result = collector.get_games_data([], raise_on_error=False)
        assert result == []

    def test_get_game_review_empty_appid_raises_invalid_request(self):
        """Test get_game_review with empty appid raises InvalidRequestError."""
        collector = Collector()
        with pytest.raises(InvalidRequestError) as exc_info:
            collector.get_game_review("")
        assert "non-empty" in str(exc_info.value).lower()
