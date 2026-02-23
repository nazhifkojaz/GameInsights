"""Tests for custom exception hierarchy."""

import pytest

from gameinsights import (
    Collector,
    DependencyNotInstalledError,
    GameInsightsError,
    GameNotFoundError,
    InvalidRequestError,
    SourceUnavailableError,
)


class TestExceptionHierarchy:
    """Test exception class definitions and attributes."""

    def test_game_not_found_error_attributes(self):
        """Test GameNotFoundError stores appid and has message."""
        exc = GameNotFoundError(appid="12345")
        assert exc.appid == "12345"
        assert "12345" in str(exc)
        assert "not found" in str(exc).lower()

    def test_game_not_found_error_custom_message(self):
        """Test GameNotFoundError accepts custom message."""
        custom_msg = "Custom error message"
        exc = GameNotFoundError(appid="12345", message=custom_msg)
        assert str(exc) == custom_msg
        assert exc.appid == "12345"

    def test_source_unavailable_error_attributes(self):
        """Test SourceUnavailableError stores source and reason."""
        exc = SourceUnavailableError(source="SteamStore", reason="Timeout")
        assert exc.source == "SteamStore"
        assert exc.reason == "Timeout"
        assert "SteamStore" in str(exc)
        assert "Timeout" in str(exc)

    def test_invalid_request_error_message(self):
        """Test InvalidRequestError stores message."""
        msg = "Invalid input"
        exc = InvalidRequestError(msg)
        assert str(exc) == msg

    def test_dependency_not_installed_error_attributes(self):
        """Test DependencyNotInstalledError stores package info."""
        exc = DependencyNotInstalledError(package="pandas", install_extra="dataframe")
        assert exc.package == "pandas"
        assert exc.install_extra == "dataframe"
        assert "pandas" in str(exc)
        assert "dataframe" in str(exc)

    def test_exception_inheritance(self):
        """Test all exceptions inherit from GameInsightsError."""
        assert issubclass(GameNotFoundError, GameInsightsError)
        assert issubclass(SourceUnavailableError, GameInsightsError)
        assert issubclass(InvalidRequestError, GameInsightsError)
        assert issubclass(DependencyNotInstalledError, GameInsightsError)


class TestCollectorErrorClassification:
    """Test _classify_source_error method."""

    def test_classify_steamstore_not_available(self):
        """Test SteamStore 'not available' message is classified as GameNotFoundError."""
        exc = Collector._classify_source_error(
            "SteamStore",
            "Failed to fetch data for appid 12345, or appid is not available in the specified region (us) or language (english).",
        )
        assert isinstance(exc, GameNotFoundError)
        assert exc.appid == "12345"

    def test_classify_not_found_with_appid(self):
        """Test classification of 'not found' errors with appid extraction."""
        exc = Collector._classify_source_error("Gamalytic", "Game with appid 12345 is not found.")
        assert isinstance(exc, GameNotFoundError)
        assert exc.appid == "12345"

    def test_classify_not_found_steamid(self):
        """Test classification of 'not found' errors with steamid."""
        exc = Collector._classify_source_error("SteamUser", "steamid 76561198000000000 not found.")
        assert isinstance(exc, GameNotFoundError)
        assert exc.appid == "76561198000000000"

    def test_classify_network_error_599(self):
        """Test classification of synthetic 599 errors."""
        exc = Collector._classify_source_error(
            "SteamStore", "Failed to connect. Status code: 599."
        )
        assert isinstance(exc, SourceUnavailableError)
        assert exc.source == "SteamStore"

    def test_classify_connection_error(self):
        """Test classification of connection errors."""
        exc = Collector._classify_source_error("Gamalytic", "Connection error occurred")
        assert isinstance(exc, SourceUnavailableError)

    def test_classify_timeout_error(self):
        """Test classification of timeout errors."""
        exc = Collector._classify_source_error("SteamCharts", "Request timeout")
        assert isinstance(exc, SourceUnavailableError)

    def test_classify_http_error_status(self):
        """Test classification of HTTP error status codes."""
        exc = Collector._classify_source_error("ProtonDB", "Failed with status code: 503")
        assert isinstance(exc, SourceUnavailableError)

    def test_classify_parse_error(self):
        """Test classification of parse errors."""
        exc = Collector._classify_source_error(
            "SteamCharts", "Failed to parse data, game name is not found."
        )
        assert isinstance(exc, SourceUnavailableError)
        assert exc.source == "SteamCharts"

    def test_classify_unknown_error(self):
        """Test classification of unknown errors falls back to base."""
        exc = Collector._classify_source_error("SomeSource", "Unexpected error occurred")
        assert isinstance(exc, GameInsightsError)
        assert not isinstance(exc, GameNotFoundError)
        assert not isinstance(exc, SourceUnavailableError)

    def test_classify_case_insensitive(self):
        """Test that classification is case-insensitive."""
        exc1 = Collector._classify_source_error("SteamStore", "Game with APPID 12345 NOT FOUND.")
        assert isinstance(exc1, GameNotFoundError)


class TestRaiseForFetchFailure:
    """Test _raise_for_fetch_failure method."""

    def test_primary_source_not_found_raises_game_not_found(self):
        """Test primary source 'not found' raises GameNotFoundError."""
        collector = Collector()
        with pytest.raises(GameNotFoundError) as exc_info:
            collector._raise_for_fetch_failure(
                source_name="SteamStore",
                error_message="Game with appid 12345 is not found.",
                is_primary=True,
            )
        assert exc_info.value.appid == "12345"

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


class TestDependencyNotInstalledError:
    """Test DependencyNotInstalledError wrapping."""

    def test_require_pandas_raises_dependency_not_installed(self, collector_with_mocks):
        """Test _require_pandas raises DependencyNotInstalledError."""
        import builtins
        from unittest.mock import patch

        original_import = builtins.__import__

        def mock_import(name, *args, **kwargs):
            if name == "pandas":
                raise ImportError("No module named 'pandas'")
            return original_import(name, *args, **kwargs)

        with patch("builtins.__import__", side_effect=mock_import):
            with pytest.raises(DependencyNotInstalledError) as exc_info:
                Collector._require_pandas()
            assert exc_info.value.package == "pandas"
            assert exc_info.value.install_extra == "dataframe"
