"""Tests for optional pandas dependency."""
import builtins
from unittest.mock import patch

import pytest


class TestPandasOptional:
    """Tests for optional pandas dependency."""

    def test_get_user_data_dataframe_raises_import_error_without_pandas(
        self, collector_with_mocks
    ):
        """Test that get_user_data with return_as='dataframe' raises clear error without pandas."""
        # Patch the builtins.__import__ to raise ImportError for pandas
        original_import = builtins.__import__

        def mock_import(name, *args, **kwargs):
            if name == "pandas":
                raise ImportError("No module named 'pandas'")
            return original_import(name, *args, **kwargs)

        with patch("builtins.__import__", side_effect=mock_import):
            with pytest.raises(ImportError) as exc_info:
                collector_with_mocks.get_user_data("12345", return_as="dataframe")

            assert "pandas is required for DataFrame operations" in str(exc_info.value)
            assert "pip install gameinsights[dataframe]" in str(exc_info.value)

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

    def test_get_games_active_player_data_raises_import_error_without_pandas(
        self, collector_with_mocks
    ):
        """Test that get_games_active_player_data raises clear error without pandas."""
        original_import = builtins.__import__

        def mock_import(name, *args, **kwargs):
            if name == "pandas":
                raise ImportError("No module named 'pandas'")
            return original_import(name, *args, **kwargs)

        with patch("builtins.__import__", side_effect=mock_import):
            with pytest.raises(ImportError) as exc_info:
                collector_with_mocks.get_games_active_player_data("12345")

            assert "pandas is required for DataFrame operations" in str(exc_info.value)

    def test_get_games_active_player_data_empty_raises_import_error_without_pandas(
        self, collector_with_mocks
    ):
        """Test that get_games_active_player_data with empty list raises clear error without pandas."""
        original_import = builtins.__import__

        def mock_import(name, *args, **kwargs):
            if name == "pandas":
                raise ImportError("No module named 'pandas'")
            return original_import(name, *args, **kwargs)

        with patch("builtins.__import__", side_effect=mock_import):
            with pytest.raises(ImportError) as exc_info:
                collector_with_mocks.get_games_active_player_data([])

            assert "pandas is required for DataFrame operations" in str(exc_info.value)

    def test_get_game_review_raises_import_error_without_pandas(
        self, collector_with_mocks
    ):
        """Test that get_game_review raises clear error without pandas."""
        original_import = builtins.__import__

        def mock_import(name, *args, **kwargs):
            if name == "pandas":
                raise ImportError("No module named 'pandas'")
            return original_import(name, *args, **kwargs)

        with patch("builtins.__import__", side_effect=mock_import):
            with pytest.raises(ImportError) as exc_info:
                collector_with_mocks.get_game_review("12345")

            assert "pandas is required for DataFrame operations" in str(exc_info.value)

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
