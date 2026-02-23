"""Tests for optional pandas dependency."""

import builtins
from unittest.mock import patch

import pytest

from gameinsights import DependencyNotInstalledError


class TestPandasOptional:
    """Tests for optional pandas dependency."""

    def test_get_user_data_dataframe_raises_dependency_not_installed_without_pandas(
        self, collector_with_mocks
    ):
        """Test that get_user_data with return_as='dataframe' raises DependencyNotInstalledError without pandas."""
        # Patch the builtins.__import__ to raise ImportError for pandas
        original_import = builtins.__import__

        def mock_import(name, *args, **kwargs):
            if name == "pandas":
                raise ImportError("No module named 'pandas'")
            return original_import(name, *args, **kwargs)

        with patch("builtins.__import__", side_effect=mock_import):
            with pytest.raises(DependencyNotInstalledError) as exc_info:
                collector_with_mocks.get_user_data("12345", return_as="dataframe")

            assert exc_info.value.package == "pandas"
            assert exc_info.value.install_extra == "dataframe"

    def test_get_user_data_list_works_without_pandas(self, collector_with_mocks):
        """Test that get_user_data with return_as='list' works without pandas."""
        # Patch the builtins.__import__ to raise ImportError for pandas
        original_import = builtins.__import__

        def mock_import(name, *args, **kwargs):
            if name == "pandas":
                raise ImportError("No module named 'pandas'")
            return original_import(name, *args, **kwargs)

        with patch("builtins.__import__", side_effect=mock_import):
            result = collector_with_mocks.get_user_data("12345", return_as="list")

            assert isinstance(result, list)

    def test_get_games_active_player_data_raises_dependency_not_installed_without_pandas(
        self, collector_with_mocks
    ):
        """Test that get_games_active_player_data raises DependencyNotInstalledError without pandas."""
        original_import = builtins.__import__

        def mock_import(name, *args, **kwargs):
            if name == "pandas":
                raise ImportError("No module named 'pandas'")
            return original_import(name, *args, **kwargs)

        with patch("builtins.__import__", side_effect=mock_import):
            with pytest.raises(DependencyNotInstalledError) as exc_info:
                collector_with_mocks.get_games_active_player_data("12345")

            assert exc_info.value.package == "pandas"

    def test_get_games_active_player_data_empty_raises_dependency_not_installed_without_pandas(
        self, collector_with_mocks
    ):
        """Test that get_games_active_player_data with empty list raises DependencyNotInstalledError without pandas."""
        original_import = builtins.__import__

        def mock_import(name, *args, **kwargs):
            if name == "pandas":
                raise ImportError("No module named 'pandas'")
            return original_import(name, *args, **kwargs)

        with patch("builtins.__import__", side_effect=mock_import):
            with pytest.raises(DependencyNotInstalledError) as exc_info:
                collector_with_mocks.get_games_active_player_data([])

            assert exc_info.value.package == "pandas"

    def test_get_game_review_raises_dependency_not_installed_without_pandas(
        self, collector_with_mocks
    ):
        """Test that get_game_review raises DependencyNotInstalledError without pandas."""
        original_import = builtins.__import__

        def mock_import(name, *args, **kwargs):
            if name == "pandas":
                raise ImportError("No module named 'pandas'")
            return original_import(name, *args, **kwargs)

        with patch("builtins.__import__", side_effect=mock_import):
            with pytest.raises(DependencyNotInstalledError) as exc_info:
                collector_with_mocks.get_game_review("12345")

            assert exc_info.value.package == "pandas"

    def test_get_games_data_never_imports_pandas(self, collector_with_mocks):
        """Test that get_games_data never imports pandas (returns list)."""
        # Track if pandas was imported
        pandas_imported = False

        original_import = builtins.__import__

        def mock_import(name, *args, **kwargs):
            nonlocal pandas_imported
            if name == "pandas":
                pandas_imported = True
                raise AssertionError("pandas should not be imported")
            return original_import(name, *args, **kwargs)

        with patch("builtins.__import__", side_effect=mock_import):
            result = collector_with_mocks.get_games_data("12345")

            assert isinstance(result, list)
            assert not pandas_imported
