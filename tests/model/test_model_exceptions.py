"""Tests for custom exception hierarchy."""

import pytest

from gameinsights import (
    DependencyNotInstalledError,
    GameInsightsError,
    GameNotFoundError,
    InvalidRequestError,
    SourceUnavailableError,
)


class TestExceptionHierarchy:
    """Test exception class definitions and attributes."""

    def test_game_not_found_error_attributes(self):
        """Test GameNotFoundError stores identifier and has message."""
        exc = GameNotFoundError(identifier="12345")
        assert exc.identifier == "12345"
        # Test backward compatibility alias
        assert exc.appid == "12345"
        assert "12345" in str(exc)
        assert "not found" in str(exc).lower()

    def test_game_not_found_error_custom_message(self):
        """Test GameNotFoundError accepts custom message."""
        custom_msg = "Custom error message"
        exc = GameNotFoundError(identifier="12345", message=custom_msg)
        assert str(exc) == custom_msg
        assert exc.identifier == "12345"
        # Test backward compatibility alias
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

    def test_exception_chaining(self):
        """Test that DependencyNotInstalledError can preserve the original ImportError."""
        original_error = ImportError("No module named 'pandas'")
        try:
            raise DependencyNotInstalledError(
                package="pandas", install_extra="dataframe"
            ) from original_error
        except DependencyNotInstalledError as e:
            # The __cause__ should be the original ImportError
            assert e.__cause__ is original_error
            assert isinstance(e.__cause__, ImportError)


class TestDependencyNotInstalledError:
    """Test DependencyNotInstalledError wrapping behavior."""

    def test_require_pandas_raises_dependency_not_installed(self, without_pandas):
        """Test _require_pandas raises DependencyNotInstalledError."""
        from gameinsights import Collector

        with pytest.raises(DependencyNotInstalledError) as exc_info:
            Collector._require_pandas()
        assert exc_info.value.package == "pandas"
        assert exc_info.value.install_extra == "dataframe"
